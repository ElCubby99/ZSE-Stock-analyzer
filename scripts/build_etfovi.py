#!/usr/bin/env python3
"""M63: frontend/public/data/etfovi.json — svi ETF-ovi uvršteni na ZSE.

Činjenični prikaz (fer-vrijednost analiza se NE radi — ETF replicira
indeks): ime fonda, indeks koji prati (kurirano iz EHO objava izdavatelja,
izvor uz svaki zapis), zadnja cijena/promet, likvidnost (dani trgovanja u
zadnjih godinu dana), serija cijena, te podaci indeksa koji fond prati kad
ih imamo (ZSE indeksi, index_eod); za strane indekse serije nemamo — stoji
samo naziv (ništa se ne izmišlja)."""
import json
import pathlib
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.indices import INDICES  # noqa: E402

ISIN_SLUG = {isin: slug for _n, (isin, slug, _d) in INDICES.items()}

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "data" / "etfovi.json"
WORKDAYS_1Y = 250  # ista aproksimacija kao likvidnost na stranici dionice


def main() -> int:
    rows = []
    yr_ago = (date.today() - timedelta(days=365)).isoformat()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(trade_date) FROM etf_prices_eod")
        market_last = cur.fetchone()[0]
        cur.execute(
            """SELECT e.symbol, e.isin, e.name, e.issuer, e.index_name,
                      e.index_isin, e.category, e.price_currency, e.status,
                      e.source
               FROM etfs e ORDER BY e.symbol""")
        for (sym, isin, name, issuer, idx_name, idx_isin, cat, ccy, status,
             src) in cur.fetchall():
            cur.execute(
                """SELECT trade_date::text, close_eur::float, volume::float,
                          turnover_eur::float
                   FROM etf_prices_eod WHERE symbol=%s ORDER BY trade_date""",
                (sym,))
            hist = cur.fetchall()
            series = [{"date": d, "close_eur": c} for d, c, _v, _t in hist]
            last = hist[-1] if hist else None
            prev = hist[-2] if len(hist) > 1 else None
            traded_1y = sum(1 for d, _c, _v, _t in hist if d >= yr_ago)

            # podaci indeksa koji fond prati — samo gdje IMAMO izvor serije
            index_data = None
            if idx_isin:
                cur.execute(
                    """SELECT trade_date::text, close_value::float
                       FROM index_eod WHERE index_isin=%s
                       ORDER BY trade_date DESC LIMIT 2""", (idx_isin,))
                iv = cur.fetchall()
                if iv:
                    index_data = {
                        "isin": idx_isin,
                        "slug": ISIN_SLUG.get(idx_isin),
                        "last_value": iv[0][1], "last_date": iv[0][0],
                        "change_pct": (round((iv[0][1] / iv[1][1] - 1) * 100, 2)
                                       if len(iv) > 1 and iv[1][1] else None),
                    }

            rows.append({
                "symbol": sym, "isin": isin,
                "name": name,               # None -> "u obradi" u UI
                "issuer": issuer,
                "index_name": idx_name,
                "index_data": index_data,   # None = nemamo izvor serije indeksa
                "category": cat,
                "currency": ccy,
                "status": status,
                "source": src,
                "last_close_eur": last[1] if last else None,
                "last_date": last[0] if last else None,
                "change_pct": (round((last[1] / prev[1] - 1) * 100, 2)
                               if last and prev and prev[1] else None),
                "last_volume": last[2] if last else None,
                "last_turnover_eur": last[3] if last else None,
                # ILIKV. istom logikom kao dionice/obveznice
                "stale": bool(last and market_last
                              and last[0] < market_last.isoformat()),
                "traded_days_1y": traded_1y,
                "workdays_1y": WORKDAYS_1Y,
                "series": series,
            })
    out = {
        "as_of": market_last.isoformat() if market_last else None,
        "rows": rows,
        "note": ("Cijene i promet iz službene ZSE tečajnice; imena fondova i "
                 "indeksi koje prate iz službenih objava izdavatelja na EHO "
                 "portalu (KIID / odluke o uvrštenju). ETF replicira indeks — "
                 "procjena fer vrijednosti se za ETF-ove ne izrađuje. Za "
                 "strane indekse ne prikazujemo vrijednosti (nemamo izvor "
                 "serije). Nije investicijski savjet."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[etfovi] {len(rows)} ETF-ova -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
