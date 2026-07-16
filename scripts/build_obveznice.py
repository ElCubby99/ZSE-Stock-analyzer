#!/usr/bin/env python3
"""M-BOND: frontend/public/data/obveznice.json — tablica svih uvrštenih
obveznica + deterministički izračuni (tekući prinos, YTM, obračunata
kamata, duracija; formule na /metodologija). YTM se NE prikazuje bez
potpunih ulaza (status 'u obradi' za izračune traži kupon+dospijeće+cijenu;
izdavatelj bez determinističkog imena ostaje 'u obradi' za master data).
Settlement za izračune = datum zadnje cijene (dokumentirano)."""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.bond_math import (  # noqa: E402
    accrued_interest, coupon_schedule, current_yield, durations, ytm,
)
from src.db import get_conn  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "data" / "obveznice.json"


def main() -> int:
    rows = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(trade_date) FROM bond_prices_eod")
        market_last = cur.fetchone()[0]
        cur.execute(
            """SELECT b.symbol, b.isin, b.issuer, b.series_name, b.btype,
                      b.coupon_pct::float, b.maturity_date, b.price_currency,
                      b.coupon_freq, b.freq_assumed, b.day_count,
                      b.day_count_assumed, b.status,
                      p.clean_price_pct::float, p.trade_date
               FROM bonds b
               LEFT JOIN LATERAL (
                 SELECT clean_price_pct, trade_date FROM bond_prices_eod
                 WHERE symbol = b.symbol ORDER BY trade_date DESC LIMIT 1
               ) p ON true
               ORDER BY b.btype, b.maturity_date""")
        for (sym, isin, issuer, srs, btype, cpn, mat, ccy, freq, freq_ass,
             dc, dc_ass, status, px, px_date) in cur.fetchall():
            cur.execute(
                """SELECT trade_date::text, clean_price_pct::float
                   FROM bond_prices_eod WHERE symbol=%s ORDER BY trade_date""",
                (sym,))
            series = [{"date": d, "price_pct": v} for d, v in cur.fetchall()]

            y = cy = acc = dur = None
            schedule = []
            can_calc = (cpn is not None and mat and px and px_date
                        and mat > px_date)
            if can_calc:
                settle = px_date
                y = ytm(px, cpn, freq or 1, mat, settle)
                cy = current_yield(px, cpn)
                acc = accrued_interest(cpn, freq or 1, mat, settle)
                dd = durations(px, cpn, freq or 1, mat, settle)
                dur = {"macaulay": dd[0], "modified": dd[1]} if dd else None
            if cpn is not None and mat and mat > dt.date.today():
                schedule = [
                    {"date": d.isoformat(),
                     "amount_pct": (cpn / (freq or 1)) + (100.0 if d == mat else 0.0)}
                    for d in coupon_schedule(mat, freq or 1, dt.date.today())]

            rows.append({
                "symbol": sym, "isin": isin,
                "issuer": issuer,           # None -> "u obradi" u UI
                "series_name": srs, "btype": btype,
                "coupon_pct": cpn,
                "maturity_date": mat.isoformat() if mat else None,
                "currency": ccy,
                "coupon_freq": freq, "freq_assumed": bool(freq_ass),
                "day_count": dc, "day_count_assumed": bool(dc_ass),
                "status": status,
                "price_pct": px,
                "price_date": px_date.isoformat() if px_date else None,
                # ILIKV. po istoj logici kao dionice: cijena starija od
                # zadnjeg tržišnog dana = indikativna
                "stale": bool(px_date and market_last and px_date < market_last),
                "ytm_pct": y * 100 if y is not None else None,
                "current_yield_pct": cy * 100 if cy is not None else None,
                "accrued_pct": acc,
                "duration": dur,
                "years_to_maturity": ((mat - dt.date.today()).days / 365.25
                                      if mat else None),
                "schedule": schedule,
                "series": series,
            })
    out = {
        "as_of": market_last.isoformat() if market_last else None,
        "rows": rows,
        "note": ("Cijene su čiste (bez obračunate kamate), u % nominale, iz "
                 "službene ZSE tečajnice. Izračuni prinosa su deterministički "
                 "(metodologija, sekcija Obveznice); frekvencija kupona i "
                 "konvencija dana nose 'pretpostavka' oznaku dok ih prospekt "
                 "ne potvrdi. Nije investicijski savjet."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with_ytm = sum(1 for r in rows if r["ytm_pct"] is not None)
    print(f"[obveznice] {len(rows)} obveznica, {with_ytm} s YTM -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
