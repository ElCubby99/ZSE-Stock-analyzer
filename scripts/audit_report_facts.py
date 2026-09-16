#!/usr/bin/env python3
"""M81: revizija rundi naspram STVARNIH izvješća.

Za svaku firmu koja ima raspravu (data/discussions/*.json) dohvaća zadnja
dva godišnja izvješća s EHO-a i provjerava dvije stvari koje su 16.09.2026.
promakle u SNBA rundi:

  1) je li se opseg izvještavanja promijenio (nekonsolidirano -> konsolidirano
     ili obrnuto) — tada postotne usporedbe dviju godina mjere RAZLIČITE
     opsege i ne smiju se iznositi bez upozorenja;
  2) ima li u računu dobiti stavku s velikim skokom koja u našim agregatima
     ostaje nevidljiva (tipično "Ostali prihodi iz redovnog poslovanja").

Ispisuje nalaz po firmi; izlazni kod 1 ako je bilo koja runda potencijalno
zahvaćena, da se može vezati na CI.

    python -m scripts.audit_report_facts [--ticker SNBA] [--json out.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import sys
import urllib.request

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.report_facts import (  # noqa: E402
    annual_sources, consolidation_changed, facts, fetch, pdf_scan)

BIG_MOVE_SHARE = 0.25   # stavka koja pomakne >25 % dobiti prethodne godine


def discussion_tickers() -> list[str]:
    return sorted({pathlib.Path(p).stem for p in glob.glob("data/discussions/*.json")})






def audit_one(cur, ticker: str) -> dict:
    out = {"ticker": ticker, "flags": [], "years": []}
    srcs = annual_sources(cur, ticker)
    if len(srcs) < 1:
        out["flags"].append("nema godišnjeg izvješća s URL-om u bazi")
        return out
    parsed = []
    for fy, url in srcs:
        blob = fetch(url)
        if not blob:
            out["flags"].append(f"NEPROVJERENO {fy}: izvješće se nije dalo dohvatiti")
            continue
        try:
            f = facts(blob, source_url=url, fiscal_year=fy)
        except Exception as e:  # noqa: BLE001
            # NIKAD ne prelaziti u 'uredno' na neuspjelom čitanju — to je
            # lažna sigurnost. PDF se barem pretraži na ključne naznake.
            hints = pdf_scan(blob) if blob[:4] == b"%PDF" else []
            kind = "PDF" if blob[:4] == b"%PDF" else type(e).__name__
            msg = (f"NEPROVJERENO {fy}: izvješće nije strojno čitljivo ({kind})"
                   + (f"; tekst spominje: {', '.join(hints)}" if hints else ""))
            out["flags"].append(msg)
            continue
        parsed.append(f)
        out["years"].append({
            "fiscal_year": fy, "consolidated": f["consolidated"],
            "employees": f["employees"],
            "subsidiaries": [s["name"] for s in f["subsidiaries"]],
        })
    if len(parsed) >= 2 and consolidation_changed(parsed[1], parsed[0]):
        out["flags"].append(
            f"OPSEG: {parsed[1]['fiscal_year']} {parsed[1]['consolidated_mark']} -> "
            f"{parsed[0]['fiscal_year']} {parsed[0]['consolidated_mark']} — "
            "usporedba godina mjeri različite opsege")
    if parsed:
        cur_f = parsed[0]
        profit = next((r for r in cur_f["watch"]
                       if r["label"].lower().startswith("dobit ili gubitak tekuće")), None)
        base = abs(profit["prev"]) if profit and profit["prev"] else None
        for r in cur_f["watch"]:
            low = r["label"].lower()
            if not low.startswith("ostali prihodi") and not low.startswith("ostali rashodi"):
                continue
            if base and abs(r["delta"]) > base * BIG_MOVE_SHARE:
                out["flags"].append(
                    f"STAVKA: '{r['label'][:48]}' {r['prev']:,.0f} -> {r['curr']:,.0f} "
                    f"(Δ {r['delta']:+,.0f}) — veće od {int(BIG_MOVE_SHARE*100)} % "
                    f"prošlogodišnje dobiti")
        if cur_f["subsidiaries"]:
            out["subsidiaries"] = [s["name"] for s in cur_f["subsidiaries"]]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", default=None, help="samo jedna firma")
    ap.add_argument("--json", default=None, help="spremi nalaz u datoteku")
    a = ap.parse_args(argv)

    tickers = [a.ticker.upper()] if a.ticker else discussion_tickers()
    results, flagged = [], 0
    with get_conn() as conn, conn.cursor() as cur:
        for t in tickers:
            print(f"[revizija] {t} …")
            r = audit_one(cur, t)
            results.append(r)
            for f in r["flags"]:
                print(f"    ⚑ {f}")
                flagged += 1
            if not r["flags"]:
                yrs = ", ".join(str(y["fiscal_year"]) for y in r["years"])
                print(f"    uredno — pročitana izvješća: {yrs} "
                      "(opseg nepromijenjen, bez velikih 'ostalih' stavki)")
    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[revizija] firmi: {len(results)}, upozorenja: {flagged}")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
