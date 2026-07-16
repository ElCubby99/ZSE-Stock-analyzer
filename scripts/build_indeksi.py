#!/usr/bin/env python3
"""M-IDX: frontend/public/data/indeksi.json — kartice, serije za graf,
sastavnice s težinama (zse.hr IndexComposition; NE izmišljaju se) i
"temperatura tržišta" (koliko CROBEX sastavnica je iznad/u/ispod naše
fer-zone — činjenični prikaz naše metrike, bez preporuka)."""
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.indices import INDICES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "data" / "indeksi.json"
OVERVIEW = ROOT / "frontend" / "public" / "data" / "overview.json"


def pct_change(series, days_back):
    """Promjena zadnje vrijednosti prema vrijednosti ~days_back dana ranije."""
    if len(series) < 2:
        return None
    last_d, last_v = series[-1]
    import datetime as dt
    target = dt.date.fromisoformat(last_d) - dt.timedelta(days=days_back)
    prev = None
    for d, v in series:
        if dt.date.fromisoformat(d) <= target:
            prev = v
        else:
            break
    if not prev:
        return None
    return last_v / prev - 1


def ytd_change(series):
    if len(series) < 2:
        return None
    last_d, last_v = series[-1]
    year = last_d[:4]
    prev = None
    for d, v in series:
        if d < f"{year}-01-01":
            prev = v
        else:
            break
    return (last_v / prev - 1) if prev else None


def main() -> int:
    zones = {}
    try:
        ov = json.loads(OVERVIEW.read_text(encoding="utf-8"))
        for s in ov.get("stocks", []):
            zones[s["ticker"]] = s
    except FileNotFoundError:
        pass

    out = {"indices": [], "temperature": None}
    with get_conn() as conn, conn.cursor() as cur:
        # klasa -> firma (stranice dionica su po FIRMI: /dionica/<company>)
        cur.execute("""SELECT COALESCE(sc.ticker, c.ticker), c.ticker
                       FROM companies c LEFT JOIN share_classes sc ON sc.company_id=c.id""")
        cls2co = {a: b for a, b in cur.fetchall()}
        for name, (isin, slug, desc) in INDICES.items():
            cur.execute(
                """SELECT trade_date::text, close_value::float FROM index_eod
                   WHERE index_isin=%s ORDER BY trade_date""", (isin,))
            series = [(d, v) for d, v in cur.fetchall()]
            if not series:
                continue
            cur.execute(
                """SELECT ticker, name, weight_pct::float, as_of::text
                   FROM index_constituents WHERE index_isin=%s
                   ORDER BY weight_pct DESC NULLS LAST, ticker""", (isin,))
            cons = [{"ticker": t, "name": n, "weight_pct": w, "as_of": a,
                     "company": cls2co.get(t)}
                    for t, n, w, a in cur.fetchall()]
            last_d, last_v = series[-1]
            prev_v = series[-2][1] if len(series) > 1 else None
            out["indices"].append({
                "name": name, "slug": slug, "isin": isin, "description": desc,
                "value": last_v, "date": last_d,
                "change_pct": (last_v / prev_v - 1) if prev_v else None,
                "ytd_pct": ytd_change(series),
                "y1_pct": pct_change(series, 365),
                # serija za graf (puna dubina, ~500 točaka — istog reda
                # veličine kao povijest cijene na stranici dionice)
                "series": [{"date": d, "value": v} for d, v in series],
                "constituents": cons,
                "source": "ZSE službene vrijednosti indeksa (zse.hr); sastavnice i težine: ZSE IndexComposition",
            })

        # temperatura tržišta: CROBEX sastavnice vs naše fer-zone
        crobex_isin = INDICES["CROBEX"][0]
        cur.execute("SELECT ticker FROM index_constituents WHERE index_isin=%s",
                    (crobex_isin,))
        members = [r[0] for r in cur.fetchall()]
    above = below = inside = np = 0
    for t in members:
        s = zones.get(t)
        if not s or s.get("zone_low") is None or not s.get("price"):
            np += 1
            continue
        if s["price"] > s["zone_high"]:
            above += 1
        elif s["price"] < s["zone_low"]:
            below += 1
        else:
            inside += 1
    total = len(members)
    if total:
        out["temperature"] = {
            "index": "CROBEX", "total": total,
            "above": above, "inside": inside, "below": below, "np": np,
            "note": ("položaj tržišnih cijena sastavnica CROBEX-a naspram naših "
                     "fer-zona (javna metodologija) — činjenični prikaz, ne "
                     "preporuka; zaključak je čitateljev"),
        }
    out["indices"].sort(key=lambda x: (x["name"] != "CROBEX", x["name"]))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[indeksi] {len(out['indices'])} indeksa, temperatura: "
          f"{out['temperature']} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
