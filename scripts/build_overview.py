#!/usr/bin/env python3
"""Gradi frontend/public/data/overview.json iz statičnih <TICKER>.json exporta.

Po KLASI dionice: cijena, promjena, promet, fer-zona (per-share iz
valuation.reconciliation; null za market_only), P/E, P/B, prinos, likvidnost.
Indeksi: zadnja 2 dana iz tablice index_eod (ako je baza dostupna); inače [].
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "frontend" / "public" / "data"

def _tickers() -> list[str]:
    """M15: dinamički — svi <TICKER>.json exporti u data direktoriju."""
    skip = {"overview"}
    return sorted(p.stem for p in DATA_DIR.glob("*.json")
                  if p.stem not in skip and p.stem == p.stem.upper())


TICKERS = _tickers()

INDICES = [
    ("CROBEX", "HRZB00ICBEX6"),
]


def load_indices() -> list[dict]:
    """CROBEX iz baze (index_eod, zadnja 2 dana). Baza nedostupna -> []."""
    try:
        sys.path.insert(0, str(ROOT))
        import psycopg2  # type: ignore

        from src.config import dsn

        out = []
        with psycopg2.connect(dsn()) as conn, conn.cursor() as cur:
            for name, isin in INDICES:
                cur.execute(
                    "SELECT trade_date, close_value FROM index_eod "
                    "WHERE index_isin = %s ORDER BY trade_date DESC LIMIT 2",
                    (isin,),
                )
                rows = cur.fetchall()
                if not rows:
                    continue
                value = float(rows[0][1])
                change_pct = None
                if len(rows) == 2 and rows[1][1]:
                    prev = float(rows[1][1])
                    if prev:
                        change_pct = value / prev - 1.0
                out.append({
                    "name": name,
                    "date": rows[0][0].isoformat(),
                    "value": value,
                    "change_pct": change_pct,
                })
        return out
    except Exception as exc:  # noqa: BLE001 — baza je opcionalna
        print(f"[overview] indeksi preskočeni (baza nedostupna): {exc}")
        return []


def build_stocks() -> list[dict]:
    stocks: list[dict] = []
    for company in TICKERS:
        path = DATA_DIR / f"{company}.json"
        d = json.loads(path.read_text(encoding="utf-8"))

        market_only = d.get("data_status") == "market_only"
        rec = (d.get("valuation") or {}).get("reconciliation") or {}
        zone_low = None if market_only else rec.get("zone_low")
        zone_high = None if market_only else rec.get("zone_high")

        liq_flags = {
            c.get("class_ticker"): c.get("flag")
            for c in (d.get("liquidity") or {}).get("classes", [])
        }
        metrics = {
            c.get("class_ticker"): c
            for c in (d.get("metrics") or {}).get("per_class", [])
        }

        for cls in (d.get("price_summary") or {}).get("classes", []):
            ct = cls.get("class_ticker")
            last = cls.get("last") or {}
            m = metrics.get(ct) or {}
            stocks.append({
                "ticker": ct,
                "company": company,
                "name": d.get("name"),
                "sector": d.get("sector"),
                "price": last.get("close_eur"),
                "date": last.get("date"),
                "change_pct": cls.get("change_pct"),
                "turnover": cls.get("avg_turnover_20d_eur"),
                "zone_low": zone_low,
                "zone_high": zone_high,
                "pe": m.get("pe"),
                "pb": m.get("pb"),
                "div_yield": m.get("div_yield"),
                "illiquid": liq_flags.get(ct) not in (None, "ok"),
            })
    return stocks


def main() -> None:
    stocks = build_stocks()
    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "indices": load_indices(),
        "stocks": stocks, "qa": systemic_qa(stocks),
    }
    out = DATA_DIR / "overview.json"
    out.write_text(
        json.dumps(overview, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"[overview] {out}: {len(stocks)} klasa, "
          f"{len(overview['indices'])} indeksa")


def systemic_qa(stocks):
    """M11 QA: ako model za >70% klasa (s zonom i cijenom) kaže da je cijena
    IZNAD fer-zone -> upozorenje o mogućoj SUSTAVNOJ pristranosti naniže."""
    rated = [s for s in stocks if s.get("zone_high") and s.get("price")]
    if not rated:
        return None
    above = [s for s in rated if s["price"] > s["zone_high"]]
    share = len(above) / len(rated)
    if share > 0.70:
        msg = (f"UPOZORENJE (sustavna pristranost?): {len(above)}/{len(rated)} "
               f"({share:.0%}) klasa ima cijenu IZNAD fer-zone — provjeri "
               "pretpostavke modela (rast, terminal g, arhetipovi), ne tržište")
        print(msg)
        return {"share_above_zone": round(share, 3), "warning": msg}
    return {"share_above_zone": round(share, 3), "warning": None}


if __name__ == "__main__":
    main()
