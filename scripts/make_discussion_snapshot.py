#!/usr/bin/env python3
"""NALOG M30 faza 1: kompaktan data_snapshot za rundu rasprave iz commitanih
exporta (frontend/public/data/<T>.json — produkcijski podaci). Snapshot je
ULAZ agenata i sprema se u discussions.data_snapshot (transparentnost:
čitatelj vidi točno što su agenti dobili)."""
import json
import sys


def snapshot(ticker: str) -> dict:
    d = json.load(open(f"frontend/public/data/{ticker}.json", encoding="utf-8"))
    rec = (d.get("valuation") or {}).get("reconciliation") or {}
    m = d.get("metrics") or {}
    prim = next((c for c in d.get("share_classes", []) if c.get("is_primary")),
                (d.get("share_classes") or [{}])[0])
    ps = next((c for c in (d.get("price_summary") or {}).get("classes", [])
               if c.get("class_ticker") == prim.get("ticker")), {})
    pc = next((r for r in m.get("per_class", [])
               if r.get("class_ticker") == prim.get("ticker")), {})
    cal = d.get("dividend_calendar") or {}
    hist = cal.get("history") or {}
    dsust = cal.get("d_sust") or {}
    own = d.get("ownership") or {}
    t10 = own.get("top10") or {}
    cz = (rec.get("class_zones") or {}).get(prim.get("ticker"))
    zone = ([cz["zone_low"], cz["zone_high"]] if cz
            else [rec.get("zone_low"), rec.get("zone_high")])
    f3 = d.get("financials_3y") or {}
    rows = {r.get("item"): r for r in (f3.get("rows") or [])}
    years = f3.get("years") or []

    def series(item):
        r = rows.get(item) or {}
        vals = r.get("values") or {}
        return {str(k): vals[k] for k in sorted(vals)}

    return {
        "ticker": d.get("ticker"), "name": d.get("name"),
        "sector": d.get("sector"), "as_of": (d.get("price_summary") or {}).get("as_of"),
        "price": (ps.get("last") or {}).get("close_eur"),
        "price_date": (ps.get("last") or {}).get("date"),
        "high_52w": ps.get("high_52w_eur"), "low_52w": ps.get("low_52w_eur"),
        "avg_turnover_20d_eur": ps.get("avg_turnover_20d_eur"),
        "traded_days_1y": ps.get("traded_days_1y"),
        "zone_low": zone[0], "zone_high": zone[1],
        "zone_note": rec.get("zone_note"), "archetype": rec.get("archetype"),
        "anchor_methods": rec.get("anchor_methods"),
        "qualified_methods": rec.get("qualified_methods"),
        "red_rules": rec.get("red_rules"), "low_float_note": rec.get("low_float_note"),
        "pe": pc.get("pe"), "pb": pc.get("pb"), "div_yield": pc.get("div_yield"),
        "eps": m.get("eps"), "bvps": m.get("bvps"), "roe": m.get("roe"),
        "dps": m.get("dps"), "dps_label": m.get("dps_label"),
        "market_cap_eur": m.get("market_cap_eur"),
        "d_sust_ps": dsust.get("d_sust_ps"), "payout_used": dsust.get("payout_used"),
        "d_sust_flags": dsust.get("flags"),
        "div_history": (hist.get("per_year") or [])[:6],
        "div_continuity": hist.get("continuity"),
        "top10_date": t10.get("snapshot_date"),
        "top10": [{"name": r.get("name"), "pct": r.get("pct")}
                  for r in (t10.get("rows") or [])[:5]],
        "free_float_from_top10_pct": t10.get("free_float_from_top10_pct"),
        "fin": {
            "revenue": series("revenue"), "net_income": series("net_income"),
            "ebitda_margin": series("ebitda_margin"),
        },
        "fin_years": years,
        "sources": {
            "stock": f"https://www.burzovnilist.com/dionica/{ticker.lower()}",
            "financials": f"https://www.burzovnilist.com/dionica/{ticker.lower()}/financije",
            "dividends": "https://www.burzovnilist.com/dividende",
            "methodology": "https://www.burzovnilist.com/metodologija",
        },
    }


if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(json.dumps(snapshot(t), ensure_ascii=False))
