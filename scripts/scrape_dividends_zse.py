"""M16-A: dividendni kalendar sa zse.hr stranice papira — za SVE klase.

Stranica papira nosi strukturirani blok 'Dividenda': iznos (isplata u novcu),
datum isplate, datum stjecanja prava (record) i 'trgovanje bez dividende'
(ex-datum). Upis u dividends s izvorom (URL stranice papira); fiscal_year
ostaje NULL (stranica ga ne navodi — ništa se ne izmišlja). Idempotentno
preko UNIQUE (class_ticker, ex_date, amount_eur).

Pokretanje:  python -m scripts.scrape_dividends_zse
"""
from __future__ import annotations

import datetime
import os
import re
import sys

sys.path.insert(0, ".")

import requests  # noqa: E402

from src.db import get_conn  # noqa: E402


def _verify():
    return os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or True


def _dt(s: str):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s)
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def parse_dividend(isin: str) -> dict | None:
    url = f"https://zse.hr/hr/papir/310?isin={isin}"
    r = requests.get("https://zse.hr/hr/papir/310", params={"isin": isin},
                     timeout=40, verify=_verify())
    r.raise_for_status()
    txt = re.sub(r"<[^>]+>", "\n", r.text)
    lines = [x.strip() for x in txt.split("\n") if x.strip()]
    try:
        i = lines.index("Dividenda")
    except ValueError:
        return None
    blk = lines[i:i + 10]
    out = {"url": url, "amount": None, "payment": None, "record": None, "ex": None}
    for j, ln in enumerate(blk):
        if ln == "Isplata u novcu" and j + 1 < len(blk):
            m = re.match(r"([\d.,]+)\s*EUR", blk[j + 1])
            if m:
                out["amount"] = float(m.group(1).replace(".", "").replace(",", "."))
        elif ln == "Datum isplate" and j + 1 < len(blk):
            out["payment"] = _dt(blk[j + 1])
        elif ln == "Datum stjecanja prava" and j + 1 < len(blk):
            out["record"] = _dt(blk[j + 1])
        elif ln == "Trgovanje bez dividende" and j + 1 < len(blk):
            out["ex"] = _dt(blk[j + 1])
    return out if out["amount"] else None


def main() -> int:
    added = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT sc.id, sc.company_id, sc.ticker, sc.isin
                       FROM share_classes sc WHERE sc.isin IS NOT NULL
                       ORDER BY sc.ticker""")
        for scid, cid, tick, isin in cur.fetchall():
            try:
                d = parse_dividend(isin)
            except Exception as e:  # noqa: BLE001
                print(f"[div] {tick}: dohvat pao ({e})")
                continue
            if not d:
                continue
            cur.execute(
                """INSERT INTO dividends (company_id, share_class_id, class_ticker,
                       fiscal_year, amount_eur, div_type, ex_date, record_date,
                       payment_date, source_url)
                   VALUES (%s,%s,%s,NULL,%s,'cash',%s,%s,%s,%s)
                   ON CONFLICT (class_ticker, ex_date, amount_eur) DO NOTHING""",
                (cid, scid, tick, d["amount"], d["ex"], d["record"], d["payment"],
                 d["url"] + " (zse.hr stranica papira, blok 'Dividenda')"))
            if cur.rowcount:
                added += 1
                print(f"[div] {tick}: {d['amount']} EUR, isplata {d['payment']}, "
                      f"ex {d['ex']}")
        conn.commit()
    print(f"[div] novih zapisa: {added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
