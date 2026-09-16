#!/usr/bin/env python3
"""NALOG M30 faza 1: kompaktan data_snapshot za rundu rasprave iz commitanih
exporta (frontend/public/data/<T>.json — produkcijski podaci). Snapshot je
ULAZ agenata i sprema se u discussions.data_snapshot (transparentnost:
čitatelj vidi točno što su agenti dobili).

M81: snapshot uz naše agregate nosi i blok `annual_report` — činjenice iz
STVARNOG godišnjeg izvješća (konsolidiranost, ovisni subjekti, najveće
promjene stavki u RDG-u). Bez toga je 16.09.2026. cijela SNBA runda
raspravljala o "nerazloženih 23,5 mil. €" koje u izvješću imaju ime i
uzrok. Kad izvješće nije strojno čitljivo (PDF), blok to IZRIČITO kaže —
nepročitano se nikad ne prikazuje kao provjereno.
"""
import json
import sys

sys.path.insert(0, ".")   # rad i kao `python scripts/...` i kao `python -m scripts...`


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
        "annual_report": annual_report_block(ticker),
        "sources": {
            "stock": f"https://www.burzovnilist.com/dionica/{ticker.lower()}",
            "financials": f"https://www.burzovnilist.com/dionica/{ticker.lower()}/financije",
            "dividends": "https://www.burzovnilist.com/dividende",
            "methodology": "https://www.burzovnilist.com/metodologija",
        },
    }


def annual_report_block(ticker: str) -> dict:
    """M81: činjenice iz zadnja dva godišnja izvješća s EHO-a.

    Vraća uvijek — i kad ne uspije: status 'nije_strojno_citljivo' s
    naznakama iz teksta jasno kaže agentu da izvješće MORA pročitati čovjek
    prije nego se iz njega išta tvrdi. Nikad ne izmišlja i nikad ne šuti."""
    try:
        from src.db import get_conn
        from src.report_facts import (annual_sources, consolidation_changed,
                                      facts, fetch, kind,
                                      text_excerpts, text_hints)
    except Exception as e:  # noqa: BLE001
        return {"status": "nedostupno", "reason": f"{type(e).__name__}: {e}"}
    try:
        with get_conn() as conn, conn.cursor() as cur:
            srcs = annual_sources(cur, ticker)
    except Exception as e:  # noqa: BLE001
        return {"status": "nedostupno", "reason": f"{type(e).__name__}: {e}"}
    if not srcs:
        return {"status": "nema_izvjesca", "note": "u bazi nema godišnjeg izvješća s URL-om"}

    years, unread = [], []
    for fy, url in srcs:
        blob = fetch(url)
        if not blob:
            unread.append({"fiscal_year": fy, "source_url": url, "reason": "dohvat nije uspio"})
            continue
        try:
            f = facts(blob, source_url=url, fiscal_year=fy)
        except Exception:  # noqa: BLE001
            fmt = {"pdf": "PDF", "esef": "ESEF/iXBRL paket",
                   "zip": "zip bez GFI obrasca"}.get(kind(blob), "neprepoznat format")
            unread.append({"fiscal_year": fy, "source_url": url,
                           "reason": f"{fmt} — nije GFI obrazac",
                           "tekst_spominje": text_hints(blob),
                           "izvodi": text_excerpts(blob)})
            continue
        years.append({
            "fiscal_year": fy, "source_url": url,
            "consolidated": f["consolidated"], "audited": f["audited"],
            "auditor": f["auditor"], "employees": f["employees"],
            "subsidiaries": f["subsidiaries"],
            "total_assets": f["total_assets"],
            "biggest_moves": [{"label": r["label"][:70], "prev": r["prev"],
                               "curr": r["curr"], "delta": r["delta"]}
                              for r in f["biggest_moves"][:6]],
        })
    block: dict = {"status": "procitano" if years else "nije_strojno_citljivo",
                   "years": years}
    if unread:
        block["unread"] = unread
        block["upozorenje"] = ("Dio godišnjih izvješća nije strojno pročitan — "
                               "tvrdnje iz njih treba provjeriti u izvorniku.")
    if len(years) >= 2 and consolidation_changed(years[1], years[0]):
        block["opseg_promijenjen"] = (
            f"{years[1]['fiscal_year']} "
            f"{'konsolidirano' if years[1]['consolidated'] else 'nekonsolidirano'} -> "
            f"{years[0]['fiscal_year']} "
            f"{'konsolidirano' if years[0]['consolidated'] else 'nekonsolidirano'}: "
            "postotne usporedbe tih godina mjere RAZLIČITE opsege")
    return block


if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(json.dumps(snapshot(t), ensure_ascii=False))
