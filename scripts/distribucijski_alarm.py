#!/usr/bin/env python3
"""v3 FAZA P.2: distribucijski alarm za likvidna imena.

Top-20 firmi po godišnjem prometu; isključuju se (s razlogom) imena sa
zanemarivim free floatom (raskorak nije informativan) i zone "u
rekalibraciji". Ako > 40% preostalih ima |raskorak vs sredina zone| > 30%
-> alarm: upisuje se u overview.json (calibration_alert: banner na
/metodologija) i skript izlazi s kodom 2 (workflow tada otvara GitHub
issue s labelom calibration-review). Ispod praga: activni=false, izlaz 0.
"""
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OVERVIEW = ROOT / "frontend" / "public" / "data" / "overview.json"
GAP_PRAG = 0.30
UDIO_PRAG = 0.40


def main() -> int:
    o = json.loads(OVERVIEW.read_text(encoding="utf-8"))
    rows = {r["ticker"]: r for r in o["stocks"]}
    with get_conn() as c, c.cursor() as cur:
        cur.execute(
            """SELECT c.ticker FROM prices_eod p
               JOIN companies c ON c.id = p.company_id
               WHERE p.trade_date > (SELECT MAX(trade_date) FROM prices_eod) - 365
               GROUP BY c.ticker
               ORDER BY SUM(p.turnover_eur) DESC NULLS LAST LIMIT 20""")
        top20 = [r[0] for r in cur.fetchall()]
    big, elig, detalji = 0, 0, []
    for t in top20:
        r = rows.get(t) or next((rows[k] for k in rows if k.startswith(t)), None)
        if not r or r.get("low_float") or not r.get("zone_low") or not r.get("price"):
            continue
        mid = (r["zone_low"] + r["zone_high"]) / 2
        gap = r["price"] / mid - 1
        elig += 1
        if abs(gap) > GAP_PRAG:
            big += 1
            detalji.append(f"{t} {gap:+.0%}")
    udio = big / elig if elig else 0.0
    alert = udio > UDIO_PRAG
    o["calibration_alert"] = {
        "active": alert, "big": big, "eligible": elig,
        "share_pct": round(udio * 100, 0),
        "names": detalji,
        "note": ("dio fer-zona je u provjeri — distribucija raskoraka "
                 "likvidnih imena premašuje interni prag; zone provjeravamo, "
                 "ne prilagođavamo ih tržištu" if alert else None),
    }
    OVERVIEW.write_text(json.dumps(o, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"[alarm] |gap|>{GAP_PRAG:.0%}: {big}/{elig} = {udio:.0%} "
          f"(prag {UDIO_PRAG:.0%}) -> {'ALARM' if alert else 'ok'}"
          + (f"; imena: {', '.join(detalji)}" if detalji else ""))
    return 2 if alert else 0


if __name__ == "__main__":
    sys.exit(main())
