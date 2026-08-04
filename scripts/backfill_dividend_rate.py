#!/usr/bin/env python3
"""M59: backfill dividendnih RATA za cijeli univerzum.

Stari dedup ključ (klasa, ex-datum, iznos) tiho je gutao 2. ratu kad je
dividenda isplaćivana u više jednakih rata s istim ex-datumom (HPB 2024:
2 x 11,95 €; HPB 2026: EHO blok nosio samo zbroj — kurirana podjela u
src.dividends.CURATED_SPLITS). Novi ključ uključuje i datum isplate, pa
ponovni scrape povijesti ubacuje nedostajuće rate i osvježava godišnji dps
(zbroj po fiskalnoj godini). Idempotentno — drugi prolaz ne mijenja ništa.

CLI:
  python scripts/backfill_dividend_rate.py [--from 2023-01-01] [tickeri...]
  (bez tickera: sve firme iz baze; ispisuje PROMIJENJENI TICKERI: za
   revalorizaciju istim mehanizmom kao repair_h1_interim)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import get_conn  # noqa: E402
from src.dividends import (scrape_dividends, store_dividends,  # noqa: E402
                           upsert_dps_financials)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tickers", nargs="*")
    p.add_argument("--from", dest="date_from", default="2023-01-01")
    a = p.parse_args(argv)
    changed = []
    with get_conn() as conn, conn.cursor() as cur:
        if a.tickers:
            tickers = [t.upper() for t in a.tickers]
        else:
            cur.execute("SELECT ticker FROM companies ORDER BY ticker")
            tickers = [r[0] for r in cur.fetchall()]
        for t in tickers:
            try:
                divs = scrape_dividends(t, a.date_from, verbose=False)
            except Exception as e:  # noqa: BLE001 — jedan ticker ne ruši backfill
                print(f"[div-rate] {t}: scrape pao ({type(e).__name__}: {e})")
                continue
            if not divs:
                continue
            n = store_dividends(conn, t, divs)
            if n:
                upsert_dps_financials(conn, t, verbose=False)
                changed.append(t)
                print(f"[div-rate] {t}: +{n} novih redaka (rate/isplate), dps osvježen")
            conn.commit()
    print("PROMIJENJENI TICKERI:", ",".join(changed) if changed else "-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
