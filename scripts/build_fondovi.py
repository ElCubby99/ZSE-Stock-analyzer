#!/usr/bin/env python3
"""M-FOND: frontend/public/data/fondovi.json — vrijednosti jedinica OMF-ova
s prinosima (YTD/1g/3g/5g IZ POVIJESTI jedinica; bez podataka -> null i
poštena napomena) + Mirex + SINERGIJA s našim podacima o dioničarima:
u kojim se ZSE top-10 popisima pojavljuju OMF-ovi (iz shareholders tablice,
matching pravila u src/pension_funds.py). BEZ rangiranja fondova —
redoslijed je abecedni po obitelji pa kategoriji."""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.pension_funds import CATEGORIES, FUNDS, ensure_tables, match_omf  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "data" / "fondovi.json"


def _return(series, years):
    """Prinos prema vrijednosti ~years unatrag (ili None)."""
    if len(series) < 2:
        return None
    last_d, last_v = series[-1]
    target = last_d - dt.timedelta(days=int(365.25 * years))
    prev = None
    for d, v in series:
        if d <= target:
            prev = v
        else:
            break
    return (last_v / prev - 1) if prev else None


def _ytd(series):
    if len(series) < 2:
        return None
    last_d, last_v = series[-1]
    prev = None
    for d, v in series:
        if d < dt.date(last_d.year, 1, 1):
            prev = v
        else:
            break
    return (last_v / prev - 1) if prev else None


def main() -> int:
    units, mirex, synergy = [], [], []
    with get_conn() as conn, conn.cursor() as cur:
        ensure_tables(conn)
        for fund in sorted(FUNDS):
            for cat in CATEGORIES:
                cur.execute(
                    """SELECT value_date, unit_value::float FROM fund_units
                       WHERE fund=%s AND category=%s ORDER BY value_date""",
                    (fund, cat))
                series = cur.fetchall()
                if not series and cat == "C" and fund != "AZ":
                    pass  # kategorija C postoji za sve — red ostaje s null
                last = series[-1] if series else None
                units.append({
                    "fund": fund, "category": cat,
                    "unit_value": last[1] if last else None,
                    "value_date": last[0].isoformat() if last else None,
                    "ytd": _ytd(series), "y1": _return(series, 1),
                    "y3": _return(series, 3), "y5": _return(series, 5),
                })
        for cat in CATEGORIES:
            cur.execute("""SELECT value_date, value::float FROM mirex
                           WHERE category=%s ORDER BY value_date""", (cat,))
            s = cur.fetchall()
            mirex.append({"category": cat,
                          "value": s[-1][1] if s else None,
                          "value_date": s[-1][0].isoformat() if s else None,
                          "ytd": _ytd(s)})

        # sinergija: zadnji snapshot top-10 po firmi -> OMF-ovi u njemu
        cur.execute(
            """SELECT c.ticker, c.name, s.holder_name, s.pct::float,
                      s.snapshot_date::text
               FROM shareholders s JOIN companies c ON c.id = s.company_id
               WHERE s.snapshot_date = (
                 SELECT max(s2.snapshot_date) FROM shareholders s2
                 WHERE s2.company_id = s.company_id)
               ORDER BY c.ticker, s.rank""")
        for ticker, name, holder, pct, snap in cur.fetchall():
            m = match_omf(holder)
            if not m:
                continue
            synergy.append({
                "ticker": ticker, "company_name": name,
                "fund": m[0], "category": m[1],
                "pct": pct, "holder_name": holder, "as_of": snap,
            })

    has_units = any(u["unit_value"] is not None for u in units)
    out = {
        "units": units, "mirex": mirex, "synergy": synergy,
        "units_available": has_units,
        "note": ("Izvor jedinica i Mirexa: HANFA javne objave, MJESEČNI ritam. "
                 + ("" if has_units else
                    "Prvi uvoz HANFA podataka još nije obavljen — prinosi će se "
                    "pojaviti nakon prvog mjesečnog uvoza. ")
                 + "Bez rangiranja fondova — redoslijed je abecedni; "
                   "činjenični prikaz, nije investicijski savjet."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[fondovi] jedinice: {'DA' if has_units else 'čeka prvi HANFA uvoz'}, "
          f"sinergija: {len(synergy)} OMF pozicija u top-10 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
