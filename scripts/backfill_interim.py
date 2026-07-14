"""M18 KORAK 2a: backfill interim (kvartalnih) izvješća iz TFI XLSX — 0 kredita.

Za sve žive firme: EHO financialReports 2024Q2–danas, XLSX, konsolidirano ima
prednost. Periodi se normaliziraju (1Q->q1, 2Q->h1, 3Q->9m, 4Q->q4) i upisuju
kao KUMULATIV (IFRS interim je YTD; cumulative=TRUE). Postojeći 'annual'
filinzi se NE diraju (valuacija ih koristi); q4 nosi kumulativ FY + proširenu
taksonomiju (M18 stavke). Svaki filing kroz validate gate; nerevidirano.

Pokretanje:  python -m scripts.backfill_interim [--tickers ...]
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys

sys.path.insert(0, ".")

import requests  # noqa: E402

from scripts.parse_tfi_universe import parse_tfi  # noqa: E402
from src.db import get_conn  # noqa: E402
from src.eho import feed  # noqa: E402
from src.loader import load_extraction  # noqa: E402
from src.validator import validate_filing  # noqa: E402

PERIOD_MAP = {"1Q": "q1", "2Q": "h1", "1H": "h1", "3Q": "9m", "4Q": "q4"}
SCRATCH = "/tmp/tfi_interim"


def _verify():
    return os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*", default=None)
    a = ap.parse_args(argv)
    os.makedirs(SCRATCH, exist_ok=True)
    today = datetime.date.today().isoformat()
    ok = review = skip = fail = 0
    with get_conn() as conn, conn.cursor() as cur:
        if a.tickers:
            firms = a.tickers
        else:
            cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
            firms = [r[0] for r in cur.fetchall()]
        for tick in firms:
            try:
                d = feed("financialReports", ticker=tick,
                         date_from="2024-04-01", date_to=today)
                items = d.get("items") or []
            except Exception as e:  # noqa: BLE001
                print(f"[interim] {tick}: feed pao ({e})"); fail += 1; continue
            # najbolji dokument po (year, period): XLSX, konsolidirani prednost
            best: dict = {}
            for it in items:
                if it.get("documentType") != "XLSX" or it.get("period") not in PERIOD_MAP:
                    continue
                key = (it["year"], it["period"])
                if key not in best or (it["consolidated"] and not best[key]["consolidated"]):
                    best[key] = it
            for (year, per), it in sorted(best.items()):
                pt = PERIOD_MAP[per]
                try:
                    path = f"{SCRATCH}/{tick}_{year}_{per}.xlsx"
                    r = requests.get(it["documentLink"], timeout=120, verify=_verify())
                    r.raise_for_status()
                    open(path, "wb").write(r.content)
                    parsed = parse_tfi(path)
                    if not parsed or not parsed["items"]:
                        print(f"[interim] {tick} {year}{per}: nije TFI-POD -> preskačem")
                        skip += 1
                        continue
                    solo = "" if it["consolidated"] else " | SOLO obrazac"
                    extraction = {
                        "meta": {"company_ticker": tick, "fiscal_year": year,
                                 "period_type": pt, "basis": "consolidated",
                                 "audited": False, "cumulative": True,
                                 "currency": "EUR", "reporting_scale": 1},
                        "items": [
                            {"item": k, "value_raw": v,
                             "confidence": 0.9 if k != "ebit" else 0.85,
                             "source_page": (f"TFI {per} {year} XLSX (kumulativ), "
                                             f"{parsed['src'][k]}{solo} — strojno "
                                             f"parsirano, nerevidirano")}
                            for k, v in parsed["items"].items()],
                    }
                    fid = load_extraction(conn, extraction,
                                          source_url=it["documentLink"],
                                          doc_type="financial_report",
                                          published_at=it.get("publishDate"))
                    conn.commit()
                    res = validate_filing(conn, fid)
                    if res["status"] == "validated":
                        ok += 1
                    else:
                        review += 1
                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    print(f"[interim] {tick} {year}{per}: GREŠKA {str(e)[:80]}")
                    fail += 1
            print(f"[interim] {tick}: {len(best)} perioda obrađeno")
    print(f"\nGOTOVO: validated={ok}, needs_review={review}, skip={skip}, fail={fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
