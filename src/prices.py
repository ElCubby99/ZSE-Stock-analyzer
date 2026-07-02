"""EOD cijene -> prices_eod (po KLASI: ADRS vs ADRS2). KORAK 2B, dio "cijene".

STANJE IZVORA (2026-07-02, vidi docs/adrs_cros_sources.md):
  - zse.hr / www.zse.hr    -> egress 403 (i preko WebFetcha) — ZSE-ov vlastiti
    EOD (tečajnica) nedostupan iz ovog okruženja dok se allowlist ne popravi.
  - rest.zse.hr            -> dosegljiv, ali traži ZSE_API_KEY (401 bez njega).
  - mojedionice.com        -> egress 403 (nije u allowlistu).
  - eho.zse.hr             -> nema podatke o cijenama (samo objave).

Zato modul nudi:
  1. import-csv — deterministički uvoz EOD zapisa (ručni export/dostava),
     format: class_ticker,trade_date,close_eur[,volume]  (ISO datum).
     Ticker se razrješava preko share_classes (klasa!) pa companies (bez klasa).
  2. zse-rest — skeleton za ZSE REST API čim ZSE_API_KEY postoji u okruženju;
     endpoint/format se konfigurira env varom ZSE_REST_URL jer služeni format
     bez ključa nije provjerljiv. NE pogađamo brojke ni format.

CLI:
  python -m src.prices import-csv data/prices_eod.csv --source "zse.hr tečajnica (ručno)"
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

from .db import get_conn


def _resolve(cur, ticker: str) -> tuple[int, int | None]:
    """ticker (klasa ili firma) -> (company_id, share_class_id|None)."""
    cur.execute("SELECT company_id, id FROM share_classes WHERE ticker = %s", (ticker,))
    r = cur.fetchone()
    if r:
        return r[0], r[1]
    cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
    r = cur.fetchone()
    if not r:
        raise ValueError(f"nepoznat ticker (ni klasa ni firma): {ticker}")
    return r[0], None


def import_csv(path: str, source: str) -> int:
    n = 0
    with get_conn() as conn, open(path, newline="", encoding="utf-8") as f:
        cur = conn.cursor()
        for row in csv.DictReader(f):
            company_id, class_id = _resolve(cur, row["class_ticker"].strip())
            cur.execute(
                """
                INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                                        close_eur, volume, source)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (company_id, trade_date, COALESCE(share_class_id, 0))
                DO UPDATE SET close_eur = EXCLUDED.close_eur,
                              volume    = EXCLUDED.volume,
                              source    = EXCLUDED.source
                """,
                (company_id, class_id, row["trade_date"].strip(),
                 float(row["close_eur"]), float(row["volume"]) if row.get("volume") else None,
                 source),
            )
            n += 1
    return n


def fetch_zse_rest(tickers: list[str]) -> int:
    key = os.getenv("ZSE_API_KEY")
    if not key:
        raise SystemExit(
            "ZSE_API_KEY nije postavljen — rest.zse.hr vraća 401 bez ključa.\n"
            "Postavi ZSE_API_KEY (i ZSE_REST_URL predložak) pa pokušaj ponovno."
        )
    raise SystemExit(
        "zse-rest dohvat još nije umrežen: format odgovora rest.zse.hr nije "
        "provjerljiv bez ključa pa ga ne pogađamo. Uz postavljen ZSE_API_KEY "
        "javi format (ili daj primjer odgovora) i ovdje se dovrši parser."
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="EOD cijene -> prices_eod")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("import-csv", help="uvoz iz CSV-a (class_ticker,trade_date,close_eur[,volume])")
    pc.add_argument("csv_path")
    pc.add_argument("--source", required=True, help="opis izvora zapisa (audit trail)")

    pr = sub.add_parser("zse-rest", help="dohvat s rest.zse.hr (traži ZSE_API_KEY)")
    pr.add_argument("tickers", nargs="+")

    a = p.parse_args(argv)
    if a.cmd == "import-csv":
        n = import_csv(a.csv_path, a.source)
        print(f"Upisano/ažurirano {n} EOD zapisa iz {a.csv_path}")
    else:
        fetch_zse_rest(a.tickers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
