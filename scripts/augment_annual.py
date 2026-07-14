"""M18 KORAK 2b: kirurški AUGMENT FY-baze PROŠIRENOM taksonomijom za 1Y-filere
BEZ 4Q objave (npr. KOEI/DLKV/PLAG) — 0 kredita.

VAŽNO: NE dira kurirane godišnje ('annual') filinge (valuacija se oslanja na
njih; auto-parse 1Y XLSX-a bira drugu liniju prihoda i zna promašiti NT).
Umjesto toga upisuje SAMO nove taksonomijske stavke iz 1Y XLSX-a u zaseban
'q4' filing (FY-ekvivalent kumulativ), koji indikatori čitaju TEK kad 'annual'
tu stavku NEMA. Jezgra (revenue/ebit/ocf/...) ostaje netaknuta i zasjenjuje q4.

Firme koje objavljuju 4Q na EHO već su pokrivene backfillom (q4 sadrži nove
stavke) — ovaj skript je samo za 1Y-filere bez 4Q.

Preskače stavke s vrijednošću 0/None za tokovne (P&L/CF) — 0 je indikator
neuspjelog parsiranja (npr. NT list koji parser ne pročita), ne stvarna nula.

Pokretanje:  python -m scripts.augment_annual --tickers KOEI DLKV PLAG
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys

sys.path.insert(0, ".")

import requests  # noqa: E402

from scripts.parse_tfi_universe import parse_tfi, _verify  # noqa: E402
from src.canonical import STATEMENT_OF  # noqa: E402
from src.db import get_conn  # noqa: E402
from src.eho import feed  # noqa: E402
from src.loader import load_extraction  # noqa: E402
from src.validator import validate_filing  # noqa: E402

# Samo M18-nove stavke (jezgru ne diramo — dolazi iz kuriranog 'annual').
NEW_ITEMS = {
    "material_costs", "interest_expense", "current_assets", "current_liabilities",
    "short_term_fin_assets", "retained_earnings", "inventories",
    "trade_receivables", "trade_payables", "investing_cf", "financing_cf",
    "employees",
}
# Tokovne stavke: vrijednost 0 = neuspjelo parsiranje -> preskoči.
FLOW_ITEMS = {"material_costs", "interest_expense", "investing_cf", "financing_cf"}


def _best_1y(items, year):
    cands = [x for x in items if x.get("documentType") == "XLSX"
             and x.get("period") in ("1Y", "4Q") and x.get("year") == year]
    if not cands:
        return None
    cands.sort(key=lambda x: (bool(x.get("consolidated")), x.get("period") == "4Q"),
               reverse=True)
    return cands[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*", required=True)
    ap.add_argument("--years", nargs="*", type=int, default=[2024, 2025])
    a = ap.parse_args(argv)
    os.makedirs("/tmp/tfi_augment", exist_ok=True)
    today = datetime.date.today().isoformat()
    ok = skip = fail = 0
    with get_conn() as conn, conn.cursor() as cur:
        for tick in a.tickers:
            try:
                d = feed("financialReports", ticker=tick,
                         date_from="2024-01-01", date_to=today)
                items = d.get("items") or []
            except Exception as e:  # noqa: BLE001
                print(f"[augment] {tick}: feed pao ({e})"); fail += 1; continue
            for year in a.years:
                rep = _best_1y(items, year)
                if not rep:
                    continue
                try:
                    path = f"/tmp/tfi_augment/{tick}_{year}.xlsx"
                    r = requests.get(rep["documentLink"].replace("\\/", "/"),
                                     timeout=120, verify=_verify())
                    r.raise_for_status()
                    with open(path, "wb") as fh:
                        fh.write(r.content)
                    parsed = parse_tfi(path)
                    if not parsed or not parsed["items"]:
                        print(f"[augment] {tick} FY{year}: nije TFI-POD -> preskačem")
                        skip += 1
                        continue
                    keep = {}
                    for k, v in parsed["items"].items():
                        if k not in NEW_ITEMS or v is None:
                            continue
                        if k in FLOW_ITEMS and abs(v) < 1:  # 0 = parse-fail
                            continue
                        keep[k] = v
                    if not keep:
                        print(f"[augment] {tick} FY{year}: nema uparivih novih stavaka")
                        skip += 1
                        continue
                    solo = "" if rep.get("consolidated") else " | SOLO obrazac"
                    extraction = {
                        "meta": {"company_ticker": tick, "fiscal_year": year,
                                 "period_type": "q4", "basis": "consolidated",
                                 "audited": False, "cumulative": True,
                                 "currency": "EUR", "reporting_scale": 1},
                        "items": [
                            {"item": k, "value_raw": v, "confidence": 0.85,
                             "source_page": (f"TFI 1Y {year} XLSX (kumulativ, samo "
                                             f"proširene stavke), {parsed['src'][k]}{solo}"
                                             " — strojno parsirano, nerevidirano")}
                            for k, v in keep.items()],
                    }
                    fid = load_extraction(conn, extraction,
                                          source_url=rep["documentLink"].replace("\\/", "/"),
                                          doc_type="financial_report",
                                          published_at=rep.get("publishDate"))
                    conn.commit()
                    validate_filing(conn, fid)
                    conn.commit()
                    print(f"[augment] {tick} FY{year}: +{len(keep)} stavaka "
                          f"({', '.join(sorted(keep))})")
                    ok += 1
                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    print(f"[augment] {tick} FY{year}: GREŠKA {str(e)[:80]}")
                    fail += 1
    print(f"\nGOTOVO: augmentirano={ok}, skip={skip}, fail={fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
