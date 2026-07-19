"""M41: lokalni regen exporta (per-stock JSON + financije + overview + indeksi).

Zrcali jezgru daily.stage_regen bez blog/dividende/shareholders koraka.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from src.db import get_conn
from src.sotp_order import ordered_tickers
from src.stock_json import build_stock_json


def main() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
            tickers = [r[0] for r in cur.fetchall()]
        tickers = ordered_tickers(conn, tickers)
        os.makedirs("frontend/public/data", exist_ok=True)
        ok, fail = 0, []
        for t in tickers:
            try:
                data = build_stock_json(conn, t)
                with open(f"frontend/public/data/{t}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                ok += 1
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                fail.append(f"{t}: {type(e).__name__}: {e}")
        print(f"stock JSON: {ok} ok, {len(fail)} fail")
        for f in fail:
            print("  FAIL", f)
    for mod in ("scripts.build_financije", "scripts.build_overview",
                "scripts.build_indeksi"):
        r = subprocess.run([sys.executable, "-m", mod], capture_output=True, text=True)
        print(f"{mod}: {'ok' if r.returncode == 0 else 'FAIL'}")
        if r.returncode != 0:
            print((r.stderr or r.stdout)[-500:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
