#!/usr/bin/env python3
"""M35: povijesna GODIŠNJA izvješća (FY2022-2024) za firme s kratkom serijom.

Deterministički, 0 API kredita: EHO financialReports feed -> TFI-POD XLSX
(1Y ako postoji, inače 4Q kumulativ = FY) -> parse_tfi -> load + validate.
Preferira konsolidirani obrazac; solo (nekonsolidirani) se uzima SAMO kad
konsolidirani ne postoji (izdavatelj bez grupe — ista konvencija kao u
parse_tfi_universe: basis='consolidated' + 'SOLO obrazac' u izvoru).

4Q fallback se upisuje kao period_type='annual' (4Q kumulativ JE fiskalna
godina za P&L i završna bilanca), a source_page se ISPRAVI da kaže 4Q —
svaka brojka nosi istinit izvor.

Banke/osiguranja: TFI im je nadzorni obrazac -> parse_tfi vraća prazno ->
preskaču se s razlogom (FINREP godišnji parser je zaseban posao).

Pokretanje: python -m scripts.backfill_history_m35 [--tickers T1 T2] [--dry]
"""
from __future__ import annotations

import argparse
import sys
import time

sys.path.insert(0, ".")

from scripts.parse_tfi_universe import ingest_tfi_xlsx  # noqa: E402
from src.db import get_conn  # noqa: E402
from src.eho import feed  # noqa: E402
from src.validator import validate_filing  # noqa: E402

YEARS = (2022, 2023, 2024)


def _short_series(conn, only=None):
    """{ticker: [godine koje FALE]} za live firme s <3 'annual' godina."""
    with conn.cursor() as cur:
        cur.execute("""
          SELECT c.ticker, c.sector,
                 ARRAY_AGG(DISTINCT f.fiscal_year ORDER BY f.fiscal_year)
                   FILTER (WHERE f.fiscal_year IS NOT NULL)
          FROM companies c
          LEFT JOIN filings f ON f.company_id=c.id AND f.period_type='annual'
               AND f.basis='consolidated'
          LEFT JOIN financials fin ON fin.filing_id=f.id AND fin.item='revenue'
               AND fin.value_eur IS NOT NULL
          WHERE c.is_live GROUP BY c.ticker, c.sector
          HAVING COUNT(DISTINCT f.fiscal_year) < 4 ORDER BY c.ticker""")
        out = {}
        for t, sector, have in cur.fetchall():
            if only and t not in only:
                continue
            have = set(have or [])
            out[t] = {"sector": sector,
                      "missing": [y for y in YEARS if y not in have]}
        return out


def _pick_doc(items, year):
    """Najbolji dokument za FY: 1Y XLSX > 4Q XLSX; konsolidiran > solo.
    -> (url, period_label, consolidated) | None"""
    cands = []
    for x in items:
        if x.get("year") != year or x.get("documentType") != "XLSX":
            continue
        per = str(x.get("period"))
        if per not in ("1Y", "4Q"):
            continue
        cons = bool(x.get("consolidated"))
        # niži tuple = bolji: 1Y prije 4Q, konsolidiran prije solo, noviji prvi
        cands.append(((0 if per == "1Y" else 1, 0 if cons else 1,
                       x.get("publishDate") or ""), x, per, cons))
    if not cands:
        return None
    cands.sort(key=lambda c: (c[0][0], c[0][1], c[0][2]))
    _, x, per, cons = cands[0]
    url = (x.get("documentLink") or "").replace("\\/", "/").replace("//fileadmin", "/fileadmin")
    return url, per, cons


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", nargs="*", default=None)
    p.add_argument("--dry", action="store_true", help="samo popis, bez upisa")
    a = p.parse_args(argv)

    done, skipped, failed = [], [], []
    with get_conn() as conn:
        plan = _short_series(conn, set(a.tickers) if a.tickers else None)
        print(f"[m35] {len(plan)} firmi s kratkom serijom")
        for t, info in plan.items():
            if info["sector"] in ("bank", "insurance"):
                skipped.append((t, "banka/osiguranje — TFI je nadzorni obrazac, "
                                   "traži FINREP godišnji parser (zaseban posao)"))
                continue
            try:
                d = feed("financialReports", ticker=t, date_from="2021-01-01",
                         date_to="2026-07-16")
                items = d.get("items") or []
            except Exception as e:  # noqa: BLE001
                failed.append((t, "*", f"feed: {type(e).__name__}: {e}"))
                continue
            for y in info["missing"]:
                pick = _pick_doc(items, y)
                if not pick:
                    skipped.append((t, f"FY{y}: nema 1Y/4Q XLSX na EHO feedu "
                                       "(samo PDF/ZIP ili ništa) — ostaje za "
                                       "ručnu PDF ekstrakciju"))
                    continue
                url, per, cons = pick
                if a.dry:
                    done.append((t, y, per, cons, "DRY"))
                    continue
                try:
                    # FY2022 i ranije: TFI obrasci su u HRK (euro od 1.1.2023.)
                    fid, parsed = ingest_tfi_xlsx(
                        conn, t, url, y, "annual",
                        consolidated=cons, cumulative=True,
                        currency="HRK" if y <= 2022 else "EUR")
                    if fid is None:
                        skipped.append((t, f"FY{y}: XLSX nije TFI-POD obrazac "
                                           "(nadzorni/drugi layout)"))
                        conn.rollback()
                        continue
                    if per == "4Q":
                        # istinit izvor: dokument je 4Q kumulativ (= FY), ne 1Y
                        with conn.cursor() as cur:
                            cur.execute(
                                """UPDATE financials
                                   SET source_page = REPLACE(source_page,
                                       'TFI 1Y', 'TFI 4Q (kumulativ = FY)')
                                   WHERE filing_id=%s""", (fid,))
                    status = validate_filing(conn, fid)
                    conn.commit()
                    done.append((t, y, per, "K" if cons else "SOLO", status))
                    print(f"  [ok] {t} FY{y} <- {per} XLSX "
                          f"({'kons.' if cons else 'solo'}) -> {status}")
                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    failed.append((t, y, f"{type(e).__name__}: {str(e)[:90]}"))
                time.sleep(0.4)   # pristojan tempo prema EHO-u

    print(f"\n[m35] upisano {len(done)}; preskočeno {len(skipped)}; "
          f"greške {len(failed)}")
    for row in skipped:
        print("  [skip]", *row)
    for row in failed:
        print("  [FAIL]", *row)
    return 0


if __name__ == "__main__":
    sys.exit(main(None))
