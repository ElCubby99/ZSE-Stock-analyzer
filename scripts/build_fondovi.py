#!/usr/bin/env python3
"""M-FOND: frontend/public/data/fondovi.json — vrijednosti jedinica OMF-ova
s prinosima (YTD/1g/3g/5g/10g IZ POVIJESTI jedinica; bez podataka -> null i
poštena napomena) + Mirex (isti set prinosa) + SINERGIJA s našim podacima o
dioničarima: u kojim se ZSE top-10 popisima pojavljuju OMF-ovi (iz
shareholders tablice, matching pravila u src/pension_funds.py). BEZ
rangiranja fondova — redoslijed je abecedni po obitelji pa kategoriji.

M-FOND2: + fondovi_series.json za graf usporedbe — po seriji (12 OMF + 3
Mirex) mjesečne točke CIJELE povijesti (zadnja vrijednost u mjesecu) i
dnevne točke zadnjih ~400 dana; frontend bira granulaciju po rasponu.
Ništa se ne interpolira — samo stvarne objavljene vrijednosti."""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.pension_funds import CATEGORIES, FUNDS, ensure_tables, match_omf  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "data" / "fondovi.json"
OUT_SERIES = ROOT / "frontend" / "public" / "data" / "fondovi_series.json"

# M-FOND3: slug za zasebnu stranicu fonda (obitelj-kategorija), npr. "az-a",
# "erste-plavi-b", "pbz-co-c", "raiffeisen-a". Isti slug čita frontend ruta.
_SLUG = {"AZ": "az", "Erste Plavi": "erste-plavi", "PBZ CO": "pbz-co",
         "Raiffeisen": "raiffeisen"}


def fund_slug(fund: str, cat: str) -> str:
    return f"{_SLUG.get(fund, fund.lower().replace(' ', '-'))}-{cat.lower()}"


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


def _returns(series):
    """Standardni set prinosa iz povijesti (None gdje serija ne seže)."""
    return {
        "ytd": _ytd(series), "y1": _return(series, 1),
        "y3": _return(series, 3), "y5": _return(series, 5),
        "y10": _return(series, 10),
    }


def _monthly(series):
    """Zadnja vrijednost u svakom mjesecu (za dugačke raspone grafa)."""
    out = []
    for d, v in series:
        key = (d.year, d.month)
        if out and out[-1][0] == key:
            out[-1] = (key, d, v)
        else:
            out.append((key, d, v))
    return [[d.isoformat(), round(v, 4)] for _, d, v in out]


def _daily_tail(series, days=400):
    """Dnevne točke zadnjih ~400 dana (za YTD/1g raspon grafa)."""
    if not series:
        return []
    cut = series[-1][0] - dt.timedelta(days=days)
    return [[d.isoformat(), round(v, 4)] for d, v in series if d >= cut]


def main() -> int:
    units, mirex, synergy, chart_series = [], [], [], []
    with get_conn() as conn, conn.cursor() as cur:
        ensure_tables(conn)
        # M-FOND3: zadnja neto imovina (AUM) po fondu/kategoriji
        aum = {}
        try:
            cur.execute(
                """SELECT DISTINCT ON (fund, category) fund, category,
                          net_assets_eur::float, members, value_date::text, source
                   FROM fund_aum ORDER BY fund, category, value_date DESC""")
            for f, c, na, mem, vd, src in cur.fetchall():
                aum[(f, c)] = {"net_assets_eur": na, "members": mem,
                               "value_date": vd, "source": src}
        except Exception:  # noqa: BLE001 — tablica možda još prazna
            conn.rollback()
        # M-FOND4: tržišna kapitalizacija po firmi (Σ klasa: zadnji EOD ×
        # dionice bez trezorskih) — za tržišnu vrijednost OMF udjela i % NAV-a
        mcap = {}
        try:
            cur.execute(
                """SELECT c.ticker,
                          SUM(p.close_eur * (sc.shares_issued
                              - COALESCE(sc.treasury_shares, 0))) AS mcap
                   FROM share_classes sc
                   JOIN companies c ON c.id = sc.company_id
                   JOIN LATERAL (
                       SELECT close_eur FROM prices_eod pe
                       WHERE pe.share_class_id = sc.id AND pe.close_eur IS NOT NULL
                       ORDER BY pe.trade_date DESC LIMIT 1) p ON TRUE
                   WHERE sc.shares_issued IS NOT NULL
                   GROUP BY c.ticker""")
            for tk, mc in cur.fetchall():
                mcap[tk] = float(mc) if mc is not None else None
        except Exception:  # noqa: BLE001
            conn.rollback()
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
                    "slug": fund_slug(fund, cat),
                    "unit_value": last[1] if last else None,
                    "value_date": last[0].isoformat() if last else None,
                    "aum": aum.get((fund, cat)),
                    **_returns(series),
                })
                if series:
                    chart_series.append({
                        "id": f"{fund}-{cat}", "fund": fund, "category": cat,
                        "kind": "omf", "m": _monthly(series),
                        "d": _daily_tail(series),
                    })
        for cat in CATEGORIES:
            cur.execute("""SELECT value_date, value::float FROM mirex
                           WHERE category=%s ORDER BY value_date""", (cat,))
            s = cur.fetchall()
            mirex.append({"category": cat,
                          "value": s[-1][1] if s else None,
                          "value_date": s[-1][0].isoformat() if s else None,
                          **_returns(s)})
            if s:
                chart_series.append({
                    "id": f"MIREX-{cat}", "fund": "Mirex", "category": cat,
                    "kind": "mirex", "m": _monthly(s), "d": _daily_tail(s),
                })

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
            # M-FOND4: tržišna vrijednost udjela (pct × tržišna kap.) i udio
            # tog ulaganja u neto imovini (NAV) fonda — NAV% samo kad je AUM
            # poznat (HANFA neto imovina); inače null uz jasnu ogradu na webu
            mc = mcap.get(ticker)
            stake_value = (pct / 100.0 * mc) if (pct is not None and mc) else None
            fa = aum.get((m[0], m[1])) or {}
            na = fa.get("net_assets_eur")
            nav_pct = (stake_value / na * 100.0) if (stake_value and na) else None
            synergy.append({
                "ticker": ticker, "company_name": name,
                "fund": m[0], "category": m[1],
                "slug": fund_slug(m[0], m[1]),
                "pct": pct, "holder_name": holder, "as_of": snap,
                "stake_value_eur": (round(stake_value, 0)
                                    if stake_value is not None else None),
                "nav_pct": (round(nav_pct, 3) if nav_pct is not None else None),
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
    series_out = {
        "as_of": max((s["m"][-1][0] for s in chart_series), default=None),
        "note": ("Stvarne objavljene vrijednosti (HANFA), bez interpolacije; "
                 "m = zadnja vrijednost u mjesecu, d = dnevne točke ~400 dana."),
        "series": chart_series,
    }
    OUT_SERIES.write_text(json.dumps(series_out, ensure_ascii=False),
                          encoding="utf-8")
    print(f"[fondovi] jedinice: {'DA' if has_units else 'čeka prvi HANFA uvoz'}, "
          f"sinergija: {len(synergy)} OMF pozicija u top-10 -> {OUT}; "
          f"graf: {len(chart_series)} serija -> {OUT_SERIES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
