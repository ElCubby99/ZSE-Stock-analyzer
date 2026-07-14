"""M19-A: praćenje troška API poziva + mjesečni budžet alarm.

Svaki API poziv (ekstrakcija, klasifikacija, segmenti) loguje se u api_usage
s procjenom troška u EUR iz config/api_pricing.json (cijene po modelu — NE
hardkodirano; batch i cache množitelji uključeni).

Politika budžeta: kad kumulativ tekućeg mjeseca prijeđe prag
(config monthly_budget_eur, override env API_BUDGET_EUR) ->
  - alarm u dnevnom digestu,
  - NE-HITNE ekstrakcije (Tier >= 3 onboarding) se preskaču do kraja mjeseca,
  - HITNE (nova izvješća iz watchera, Tier 1) prolaze normalno.

Logging NIKAD ne smije srušiti sam API poziv — sve je omotano u try/except.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

_PRICING: Optional[dict] = None
_PRICING_PATH = os.path.join(os.path.dirname(__file__), "..", "config",
                             "api_pricing.json")


def pricing() -> dict:
    global _PRICING
    if _PRICING is None:
        with open(_PRICING_PATH, encoding="utf-8") as f:
            _PRICING = json.load(f)
    return _PRICING


def _model_prices(model: str) -> Optional[dict]:
    """Match po prefiksu — dated ID (claude-haiku-4-5-20251001) -> bazni unos."""
    models = pricing()["models"]
    if model in models:
        return models[model]
    for key in sorted(models, key=len, reverse=True):
        if model.startswith(key):
            return models[key]
    return None


def estimate_cost_eur(model: str, input_tokens: int = 0, output_tokens: int = 0,
                      cache_creation_input_tokens: int = 0,
                      cache_read_input_tokens: int = 0,
                      batch: bool = False) -> Optional[float]:
    """Procjena troška u EUR; None ako model nije u configu (loguj s 0 + flag)."""
    p = pricing()
    mp = _model_prices(model)
    if mp is None:
        return None
    in_usd = mp["input_usd_per_mtok"] / 1e6
    out_usd = mp["output_usd_per_mtok"] / 1e6
    usd = (input_tokens * in_usd
           + output_tokens * out_usd
           + cache_creation_input_tokens * in_usd * p["cache_write_multiplier"]
           + cache_read_input_tokens * in_usd * p["cache_read_multiplier"])
    if batch:
        usd *= p["batch_multiplier"]
    return usd * p["usd_eur"]


def record(operation: str, model: str, usage: Any = None, *,
           ticker: str | None = None, batch: bool = False,
           conn=None) -> None:
    """Upiši jedan API poziv. `usage` je response.usage objekt (ili dict).
    Otvara vlastitu konekciju ako conn nije dan. Nikad ne baca — greška
    logiranja ne smije srušiti ekstrakciju."""
    try:
        def g(k):
            if usage is None:
                return 0
            if isinstance(usage, dict):
                return int(usage.get(k) or 0)
            return int(getattr(usage, k, 0) or 0)

        it, ot = g("input_tokens"), g("output_tokens")
        cc, cr = g("cache_creation_input_tokens"), g("cache_read_input_tokens")
        cost = estimate_cost_eur(model, it, ot, cc, cr, batch)
        if cost is None:
            cost = 0.0
            operation = f"{operation}|model_nije_u_cjeniku"
        row = (ticker, operation, model, it, ot, cc, cr, batch, round(cost, 6))
        sql = ("INSERT INTO api_usage (ticker, operation, model, input_tokens, "
               "output_tokens, cache_creation_input_tokens, "
               "cache_read_input_tokens, batch, est_cost_eur) "
               "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)")
        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(sql, row)
        else:
            from .db import get_conn
            with get_conn() as c, c.cursor() as cur:
                cur.execute(sql, row)
                c.commit()
    except Exception as e:  # noqa: BLE001 — logging ne smije rušiti poziv
        print(f"[api_usage] upozorenje: logiranje nije uspjelo ({e})")


# ---------- agregacije ----------

def month_total_eur(conn) -> float:
    with conn.cursor() as cur:
        cur.execute("""SELECT COALESCE(SUM(est_cost_eur),0) FROM api_usage
                       WHERE date_trunc('month', ts) = date_trunc('month', now())""")
        return float(cur.fetchone()[0])


def today_total_eur(conn) -> float:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(est_cost_eur),0) FROM api_usage "
                    "WHERE ts::date = CURRENT_DATE")
        return float(cur.fetchone()[0])


def by_firm(conn, limit: int = 20) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute("""SELECT COALESCE(ticker,'—'), SUM(est_cost_eur), COUNT(*)
                       FROM api_usage GROUP BY 1 ORDER BY 2 DESC LIMIT %s""", (limit,))
        return cur.fetchall()


def by_day(conn, days: int = 31) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute("""SELECT ts::date, SUM(est_cost_eur), COUNT(*) FROM api_usage
                       WHERE ts > now() - make_interval(days => %s)
                       GROUP BY 1 ORDER BY 1 DESC""", (days,))
        return cur.fetchall()


def by_operation(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute("""SELECT operation, SUM(est_cost_eur), COUNT(*)
                       FROM api_usage GROUP BY 1 ORDER BY 2 DESC""")
        return cur.fetchall()


# ---------- budžet ----------

def monthly_budget_eur() -> float:
    env = os.getenv("API_BUDGET_EUR")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return float(pricing().get("monthly_budget_eur", 50.0))


def budget_state(conn) -> dict:
    month = month_total_eur(conn)
    budget = monthly_budget_eur()
    return {"today_eur": today_total_eur(conn), "month_eur": month,
            "budget_eur": budget, "exceeded": month > budget}


def allow_extraction(conn, *, urgent: bool) -> bool:
    """Budžet gate: hitne (Tier 1 / watcher nova izvješća) UVIJEK prolaze;
    ne-hitne (Tier >= 3 backfill/onboarding) se pauziraju kad je mjesec preko
    praga."""
    if urgent:
        return True
    try:
        return not budget_state(conn)["exceeded"]
    except Exception:  # noqa: BLE001 — gate ne smije blokirati zbog greške
        return True


def digest_line(conn) -> str:
    s = budget_state(conn)
    line = (f"API danas: €{s['today_eur']:.2f} | mjesec: €{s['month_eur']:.2f} "
            f"/ €{s['budget_eur']:.2f} budžet")
    if s["exceeded"]:
        line += ("\n**ALERT: mjesečni API budžet PREKORAČEN — ne-hitne ekstrakcije "
                 "(Tier 3) pauzirane do kraja mjeseca; hitne (nova izvješća, "
                 "Tier 1) prolaze.**")
    return line


def main(argv=None) -> int:
    """CLI: python -m src.api_usage — pregled troška (dan/firma/operacija/budžet)."""
    from .db import get_conn
    with get_conn() as conn:
        s = budget_state(conn)
        print(digest_line(conn))
        print("\nPo danu (31 d):")
        for d, eur, n in by_day(conn):
            print(f"  {d}  €{float(eur):8.4f}  ({n} poziva)")
        print("\nPo firmi (top 20):")
        for t, eur, n in by_firm(conn):
            print(f"  {t:8} €{float(eur):8.4f}  ({n} poziva)")
        print("\nPo operaciji:")
        for op, eur, n in by_operation(conn):
            print(f"  {op:28} €{float(eur):8.4f}  ({n} poziva)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
