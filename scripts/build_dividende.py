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
import re
import sys
from datetime import date

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

OUT = "frontend/public/data/dividende.json"


def _src_id(url: str | None) -> int:
    m = re.search(r"/view/(\d+)", url or "")
    return int(m.group(1)) if m else 0


def suppress_superseded(rows: list[dict]) -> list[dict]:
    """M76: potisni redundantne retke istog (firma, klasa, FY, iznos):
      - postoji li ne-prijedlog u grupi, prijedlozi se ne prikazuju
        (QTLG: prijedlog #67538 + izglasana #67687 istih datuma);
      - među samim prijedlozima ostaje samo najnovija objava — veći EHO
        view id (CKML: ispravak poziva #67707 zamjenjuje #67692).
    Rate iste dividende (HPB 2×8,77) su ne-prijedlozi i NE diraju se."""
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["company"], r["class_ticker"], r["fiscal_year"],
                           r["amount_eur"]), []).append(r)
    out = []
    for grp in groups.values():
        proposals = [r for r in grp if "rijedlog" in (r["div_type"] or "")]
        others = [r for r in grp if r not in proposals]
        out.extend(others)
        if proposals and not others:
            newest = max(_src_id(r["source_url"]) for r in proposals)
            out.extend(r for r in proposals if _src_id(r["source_url"]) == newest)
    # stabilan poredak kao prije grupiranja (ex_date pa klasa)
    out.sort(key=lambda r: (r["ex_date"] or r["payment_date"] or "9999",
                            r["class_ticker"] or ""))
    return out


def main() -> int:
    today = date.today()
    rows = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT c.ticker, c.name, d.class_ticker, d.fiscal_year,
                      d.amount_eur, d.div_type, d.ex_date, d.record_date,
                      d.payment_date, d.source_url,
                      d.payout_type, d.payout_ratio, d.classified_reason,
                      d.note,
                      (SELECT p.close_eur FROM prices_eod p
                       JOIN share_classes sc ON sc.id = p.share_class_id
                       WHERE sc.ticker = d.class_ticker
                             AND p.close_eur IS NOT NULL
                       ORDER BY p.trade_date DESC LIMIT 1) AS last_close
               FROM dividends d JOIN companies c ON c.id = d.company_id
               ORDER BY COALESCE(d.ex_date, d.payment_date) NULLS LAST,
                        d.class_ticker""")
        for (tick, name, ct, fy, amt, dtyp, ex, rec, pay, src,
             ptype, pratio, preason, note, close) in cur.fetchall():
            # status istom logikom kao profil (jedan izvor istine za oznake)
            if dtyp and "izvedeno" in dtyp:
                status = "paid"  # Z2: povijesni izvedeni zapis (NT) = isplaćen
            elif dtyp and "rijedlog" in (dtyp or ""):
                # M59: prijedlog NIKAD nije "isplaćen" — protekli datum isplate
                # prijedloga ne čini ga isplatom (isti redoslijed kao profil)
                status = "proposed"
            elif pay is not None and pay <= today:
                status = "paid"
            elif (pay is None and ex is None and fy is not None
                  and fy < today.year - 1):
                # M35.1: povijesni zapis BEZ datuma (stara fiskalna godina)
                # ne smije defaultati na "nadolazeća" — dividenda za FY1999
                # nije upcoming ni u kojem svemiru
                status = "paid"
            else:
                status = "upcoming"
            # obuhvat: isplaćene OVE godine + AKTUALNE nadolazeće/prijedlozi
            if status == "paid":
                ref = pay or ex
                if ref is None or ref.year != today.year:
                    continue
            elif status == "proposed":
                # M59: prijedlog s proteklim datumima je ili zamijenjen
                # izglasanom verzijom ili odbačen — ne prikazuje se kao aktualan
                ref = ex or pay
                if ref is not None and ref < today:
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
                # v3 DIV: tip isplate + % dobiti pripadne fiskalne godine
                "payout_type": ptype,
                "payout_ratio": float(pratio) if pratio is not None else None,
                "classified_reason": preason,
                # M59: napomena uz rate (HPB: 2 rate po 8,77 € iste dividende)
                "note": note,
            })
        # Z2: povijest po firmi -> kontinuitet i prosjek za kalendar
        # M59: SUM umjesto MAX — rate i višestruke isplate iste fiskalne
        # godine se ZBRAJAJU (konvencija kao dps u financials); dual-class
        # dupliciranje rješava filter na primarnu liniju klase
        cur.execute(
            """SELECT c.ticker,
                      COALESCE(d.fiscal_year,
                        EXTRACT(YEAR FROM COALESCE(d.ex_date, d.payment_date))::int - 1) fy,
                      SUM(d.amount_eur)
               FROM dividends d JOIN companies c ON c.id=d.company_id
               LEFT JOIN share_classes sc ON sc.id=d.share_class_id
               WHERE d.div_type NOT ILIKE '%%rijedlog%%' AND d.amount_eur IS NOT NULL
                 AND (sc.is_primary_line IS TRUE OR d.share_class_id IS NULL)
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
    rows = suppress_superseded(rows)
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
