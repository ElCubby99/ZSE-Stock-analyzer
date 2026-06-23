"""Integracijski test: loader + validator protiv lokalne baze.

Sve se radi unutar jedne transakcije koja se na kraju ROLLBACK-a, pa baza
ostaje čista. Zahtijeva postavljenu shemu (db/setup_db.sh) i KOEI seed.
"""
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.loader import load_extraction  # noqa: E402
from src.validator import validate_filing  # noqa: E402


def _consistent_extraction(year, *, conf=0.95, scale=1000):
    """Interno konzistentna konsolidirana godišnja ekstrakcija (value_raw u '000)."""
    items = {
        "income": {
            "revenue": 1_200_000, "operating_expenses": 1_050_000,
            "depreciation_amortization": 60_000, "ebit": 150_000,
            "net_financial_result": 10_000, "pretax_income": 160_000,
            "income_tax": 28_000, "net_income": 132_000,
            "net_income_parent": 125_000, "net_income_minority": 7_000,
        },
        "balance": {
            "total_assets": 1_800_000, "total_equity": 900_000,
            "equity_parent": 850_000, "minority_interests": 50_000,
            "debt_short": 80_000, "debt_long": 220_000,
            "cash_and_equivalents": 150_000,
        },
        "cashflow": {"operating_cf": 180_000, "capex": 90_000},
        "shares": {"shares_outstanding": 2_570_000, "treasury_shares": 50_000},
    }
    out = []
    for stmt, d in items.items():
        for item, val in d.items():
            out.append({"statement": stmt, "item": item, "value_raw": val,
                        "source_page": "str. 1", "confidence": conf})
    return {
        "meta": {"company_ticker": "KOEI", "fiscal_year": year,
                 "period_type": "annual", "basis": "consolidated",
                 "cumulative": False, "audited": True, "currency": "EUR",
                 "reporting_scale": scale},
        "items": out, "flags": [],
    }


def _run(conn, extraction):
    fid = load_extraction(conn, extraction, source_url="test://x")
    return fid, validate_filing(conn, fid)


def main():
    conn = psycopg2.connect(config.dsn())
    failures = []

    def check(name, cond, extra=""):
        print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  ({extra})" if extra else ""))
        if not cond:
            failures.append(name)

    try:
        # --- 1. Čista, konzistentna ekstrakcija => validated ---
        fid, res = _run(conn, _consistent_extraction(2024))
        check("clean_filing_validated", res["status"] == "validated", res["status"])
        rmap = {r["rule"]: r["status"] for r in res["results"]}
        check("rule1_pass", rmap["1_balance_closes"] == "PASS")
        check("rule2_pass", rmap["2_equity_consistent"] == "PASS")
        check("rule3_pass", rmap["3_profit_consistent"] == "PASS")
        check("rule4_ebitda_derived_pass", rmap["4_ebitda_sanity"] == "PASS")
        check("rule7_confidence_pass", rmap["7_confidence"] == "PASS")

        # derivirane stavke upisane (is_reported=FALSE)
        with conn.cursor() as cur:
            cur.execute("SELECT item, value_eur, is_reported FROM financials "
                        "WHERE filing_id=%s AND item IN ('ebitda','net_debt','total_debt','free_cash_flow')",
                        (fid,))
            der = {i: (float(v), r) for i, v, r in cur.fetchall()}
        check("ebitda_derived_value", der.get("ebitda", (0,))[0] == 210_000_000, der.get("ebitda"))
        check("net_debt_derived_value", der.get("net_debt", (0,))[0] == 150_000_000, der.get("net_debt"))
        check("fcf_derived_value", der.get("free_cash_flow", (0,))[0] == 90_000_000)
        check("derived_not_reported", all(not r for _, r in der.values()))
        check("value_eur_scaled", der.get("total_debt", (0,))[0] == 300_000_000)

        # broj dionica NIJE skaliran monetarnom skalom
        with conn.cursor() as cur:
            cur.execute("SELECT value_eur FROM financials WHERE filing_id=%s AND item='shares_outstanding'", (fid,))
            shares = float(cur.fetchone()[0])
        check("shares_not_scaled", shares == 2_570_000, shares)

        # --- 2. Niska confidence => FAIL pravilo 7 => needs_review ---
        conn.rollback()
        bad = _consistent_extraction(2024, conf=0.50)
        fid2, res2 = _run(conn, bad)
        check("low_conf_needs_review", res2["status"] == "needs_review", res2["status"])
        r7 = next(r for r in res2["results"] if r["rule"] == "7_confidence")
        check("rule7_fail", r7["status"] == "FAIL")

        # --- 3. Nekonzistentan kapital => FAIL pravilo 2 ---
        conn.rollback()
        broken = _consistent_extraction(2024)
        for it in broken["items"]:
            if it["item"] == "minority_interests":
                it["value_raw"] = 999_999  # razbij equity_parent+minority=total_equity
        fid3, res3 = _run(conn, broken)
        r2 = next(r for r in res3["results"] if r["rule"] == "2_equity_consistent")
        check("rule2_fail_on_broken_equity", r2["status"] == "FAIL")
        check("broken_needs_review", res3["status"] == "needs_review")

        # --- 4. YoY: dvije godine, druga skoči >60% => WARN ---
        conn.rollback()
        load_extraction(conn, _consistent_extraction(2023), source_url="test://2023")
        big = _consistent_extraction(2024)
        for it in big["items"]:
            if it["item"] == "revenue":
                it["value_raw"] = 3_000_000  # +150% YoY
        fid4 = load_extraction(conn, big, source_url="test://2024")
        res4 = validate_filing(conn, fid4)
        r6 = next(r for r in res4["results"] if r["rule"] == "6_yoy_sanity")
        check("rule6_warn_on_big_yoy", r6["status"] == "WARN", r6["detail"])

    finally:
        conn.rollback()  # ništa se ne perzistira
        conn.close()

    print(f"\n{'ALL PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
