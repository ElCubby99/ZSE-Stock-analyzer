#!/usr/bin/env python3
"""M22: agregirani dividendni kalendar -> frontend/public/data/dividende.json.

Jedan red po dividendnom događaju (po KLASI — dual-class firme imaju red po
klasi s cijenom te klase). Ulaze: isplaćene OVE godine + sve nadolazeće i
prijedlozi. Status ISTOM logikom kao profil dionice (src/stock_json.py
_dividend_calendar): paid (payment_date <= danas) / proposed (div_type sadrži
'rijedlog') / upcoming. Prinos = iznos / zadnji close TE klase (podatak, ne
rang). Datumi koji ne postoje u objavi ostaju null. Izvor uz svaki red.
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

OUT = "frontend/public/data/dividende.json"


def main() -> int:
    today = date.today()
    rows = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT c.ticker, c.name, d.class_ticker, d.fiscal_year,
                      d.amount_eur, d.div_type, d.ex_date, d.record_date,
                      d.payment_date, d.source_url,
                      (SELECT p.close_eur FROM prices_eod p
                       JOIN share_classes sc ON sc.id = p.share_class_id
                       WHERE sc.ticker = d.class_ticker
                             AND p.close_eur IS NOT NULL
                       ORDER BY p.trade_date DESC LIMIT 1) AS last_close
               FROM dividends d JOIN companies c ON c.id = d.company_id
               ORDER BY COALESCE(d.ex_date, d.payment_date) NULLS LAST,
                        d.class_ticker""")
        for (tick, name, ct, fy, amt, dtyp, ex, rec, pay, src,
             close) in cur.fetchall():
            # status istom logikom kao profil (jedan izvor istine za oznake)
            if dtyp and "izvedeno" in dtyp:
                status = "paid"  # Z2: povijesni izvedeni zapis (NT) = isplaćen
            elif pay is not None and pay <= today:
                status = "paid"
            elif dtyp and "rijedlog" in (dtyp or ""):
                status = "proposed"
            else:
                status = "upcoming"
            # obuhvat: isplaćene OVE godine + sve nadolazeće/prijedlozi
            if status == "paid":
                ref = pay or ex
                if ref is None or ref.year != today.year:
                    continue
            amt_f = float(amt)
            close_f = float(close) if close is not None else None
            rows.append({
                "company": tick, "name": name, "class_ticker": ct,
                "fiscal_year": fy, "amount_eur": amt_f,
                "div_type": dtyp,
                "ex_date": str(ex) if ex else None,
                "record_date": str(rec) if rec else None,
                "payment_date": str(pay) if pay else None,
                "status": status,
                "price_eur": close_f,
                "yield_now": (amt_f / close_f) if close_f else None,
                "source_url": src,
            })
        # Z2: povijest po firmi -> kontinuitet i prosjek za kalendar
        cur.execute(
            """SELECT c.ticker,
                      COALESCE(d.fiscal_year,
                        EXTRACT(YEAR FROM COALESCE(d.ex_date, d.payment_date))::int - 1) fy,
                      MAX(d.amount_eur)
               FROM dividends d JOIN companies c ON c.id=d.company_id
               WHERE d.div_type NOT ILIKE '%%rijedlog%%' AND d.amount_eur IS NOT NULL
               GROUP BY 1, 2""")
        per_firm = {}
        for tick, fy, amt in cur.fetchall():
            if fy is not None:
                per_firm.setdefault(tick, {})[int(fy)] = float(amt)
        history = {}
        for tick, byfy in per_firm.items():
            years = sorted(byfy, reverse=True)
            window = set(range(max(years) - 4, max(years) + 1))
            last5 = years[:5]
            history[tick] = {
                "paid_years_of_5": len([y for y in years if y in window]),
                "coverage_from": min(years),
                "avg_amount_5y": round(sum(byfy[y] for y in last5) / len(last5), 4),
            }
    out = {
        "as_of": str(today),
        "rows": rows,
        "history": history,
        "note": ("Izvor: EHO objave izdavatelja (odluke glavnih skupština / "
                 "obavijesti o dividendi). Prinos = iznos / zadnja cijena te "
                 "klase (informativan podatak, ne preporuka). Prijedlozi NISU "
                 "izglasane isplate. Datumi koji nisu objavljeni ostaju prazni."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    n_up = sum(1 for r in rows if r["status"] != "paid")
    print(f"[dividende] {len(rows)} redova ({n_up} nadolazećih/prijedloga) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
