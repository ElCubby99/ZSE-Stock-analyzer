"""Točka 3 (validator): 7 determinističkih provjera nad učitanim filingom.

Politika statusa:
  - FAIL ili WARN na bilo kojem pravilu => filing.status = 'needs_review'
  - inače                                => filing.status = 'validated'
  - SKIP (nema dovoljno podataka za pravilo) ne blokira, ali se bilježi.

Pravila 1–4 i 7 su tvrde provjere (FAIL). Pravila 5–6 su "flag za pregled"
(WARN) — ne znače nužno grešku, ali traže ljudsko oko => needs_review.

API: validate_filing(conn, filing_id) -> {"status", "results": [...]}
"""
from __future__ import annotations

from typing import Any

CONF_THRESHOLD = 0.85
TOL = 0.005          # ±0.5% za bilančne identitete
YOY_LIMIT = 0.60     # ±60% YoY => flag


def rel_close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b), 1.0)


def _filing_meta(conn, filing_id: int) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT company_id, fiscal_year, period_type, basis "
            "FROM filings WHERE id = %s",
            (filing_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Filing {filing_id} ne postoji.")
        return {"company_id": row[0], "fiscal_year": row[1],
                "period_type": row[2], "basis": row[3]}


def _items_for_filing(conn, filing_id: int):
    """Vrati (values{item:value_eur}, conf{item:confidence-reported-only})."""
    values: dict[str, float] = {}
    conf: dict[str, float] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item, value_eur, confidence, is_reported "
            "FROM financials WHERE filing_id = %s",
            (filing_id,),
        )
        for item, value_eur, confidence, is_reported in cur.fetchall():
            if value_eur is not None:
                values[item] = float(value_eur)
            if is_reported and confidence is not None:
                conf[item] = float(confidence)
    return values, conf


def _prior_year_values(conn, meta: dict[str, Any]):
    """Vrijednosti prethodne godine (isti period_type/basis) iz current viewa."""
    values: dict[str, float] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT item, value_eur FROM v_financials_current
            WHERE company_id = %s AND fiscal_year = %s
              AND period_type = %s AND basis = %s
            """,
            (meta["company_id"], meta["fiscal_year"] - 1,
             meta["period_type"], meta["basis"]),
        )
        for item, value_eur in cur.fetchall():
            if value_eur is not None:
                values[item] = float(value_eur)
    return values


def _r(rule: str, status: str, detail: str) -> dict[str, str]:
    return {"rule": rule, "status": status, "detail": detail}


def validate_filing(conn, filing_id: int) -> dict[str, Any]:
    meta = _filing_meta(conn, filing_id)
    v, conf = _items_for_filing(conn, filing_id)
    prior = _prior_year_values(conn, meta)
    results: list[dict[str, str]] = []

    # 1. Bilanca se zatvara.
    if "total_assets" in v and "total_equity" in v and "total_liabilities" in v:
        rhs = v["total_equity"] + v["total_liabilities"]
        ok = rel_close(v["total_assets"], rhs)
        results.append(_r("1_balance_closes", "PASS" if ok else "FAIL",
                          f"total_assets={v['total_assets']:.0f} vs equity+liab={rhs:.0f}"))
    elif "total_assets" in v and "total_equity" in v:
        ok = v["total_equity"] <= v["total_assets"] * (1 + TOL)
        results.append(_r("1_balance_closes", "PASS" if ok else "FAIL",
                          f"fallback: total_equity({v['total_equity']:.0f}) <= total_assets({v['total_assets']:.0f})"))
    else:
        results.append(_r("1_balance_closes", "SKIP", "nedostaje total_assets/total_equity"))

    # 2. Kapital konzistentan.
    if all(k in v for k in ("equity_parent", "minority_interests", "total_equity")):
        lhs = v["equity_parent"] + v["minority_interests"]
        ok = rel_close(lhs, v["total_equity"])
        results.append(_r("2_equity_consistent", "PASS" if ok else "FAIL",
                          f"parent+minority={lhs:.0f} vs total_equity={v['total_equity']:.0f}"))
    else:
        results.append(_r("2_equity_consistent", "SKIP",
                          "nedostaje equity_parent/minority_interests/total_equity"))

    # 3. Dobit konzistentna.
    if all(k in v for k in ("net_income_parent", "net_income_minority", "net_income")):
        lhs = v["net_income_parent"] + v["net_income_minority"]
        ok = rel_close(lhs, v["net_income"])
        results.append(_r("3_profit_consistent", "PASS" if ok else "FAIL",
                          f"parent+minority={lhs:.0f} vs net_income={v['net_income']:.0f}"))
    else:
        results.append(_r("3_profit_consistent", "SKIP",
                          "nedostaje net_income_parent/minority/net_income"))

    # 4. EBITDA sanity.
    if "ebit" in v and "depreciation_amortization" in v and "ebitda" in v:
        expected = v["ebit"] + v["depreciation_amortization"]
        ok = rel_close(v["ebitda"], expected)
        results.append(_r("4_ebitda_sanity", "PASS" if ok else "FAIL",
                          f"ebitda={v['ebitda']:.0f} vs ebit+d&a={expected:.0f}"))
    else:
        results.append(_r("4_ebitda_sanity", "SKIP", "nedostaje ebit/d&a/ebitda"))

    # 5. Scale sanity (WARN): revenue red veličine vs prošla godina.
    if "revenue" in v and "revenue" in prior and prior["revenue"] != 0:
        ratio = v["revenue"] / prior["revenue"]
        if ratio > 100 or ratio < 0.01:
            results.append(_r("5_scale_sanity", "WARN",
                              f"revenue {v['revenue']:.0f} je {ratio:.1f}x prošle ({prior['revenue']:.0f}) — provjeri reporting_scale"))
        else:
            results.append(_r("5_scale_sanity", "PASS", f"revenue ratio vs prošla={ratio:.2f}"))
    else:
        results.append(_r("5_scale_sanity", "SKIP", "nema prošlogodišnjeg revenue za usporedbu"))

    # 6. YoY sanity (WARN): SAMO jezgrene stavke >±60% YoY (M6.2 suženje —
    # novčani tokovi i sporedne stavke legitimno jako variraju pa ne blokiraju;
    # isti "jezgreni" duh kao promotion gate u onboardingu).
    YOY_CORE_ITEMS = {"revenue", "net_income_parent", "equity_parent",
                      "total_assets", "total_operating_income"}
    big_moves = []
    for item, cur_val in v.items():
        if item not in YOY_CORE_ITEMS:
            continue
        if item in prior and prior[item] != 0:
            change = (cur_val - prior[item]) / abs(prior[item])
            if abs(change) > YOY_LIMIT:
                big_moves.append(f"{item} {change*100:+.0f}%")
    if not prior:
        results.append(_r("6_yoy_sanity", "SKIP", "nema prethodne godine"))
    elif big_moves:
        results.append(_r("6_yoy_sanity", "WARN", "velike YoY promjene: " + ", ".join(big_moves)))
    else:
        results.append(_r("6_yoy_sanity", "PASS", "jezgrene stavke unutar ±60% YoY"))

    # 7. Confidence prag: bilo koja reported stavka < 0.85.
    low = {k: c for k, c in conf.items() if c < CONF_THRESHOLD}
    if not conf:
        results.append(_r("7_confidence", "SKIP", "nema reported confidence vrijednosti"))
    elif low:
        results.append(_r("7_confidence", "FAIL",
                          "ispod praga: " + ", ".join(f"{k}={c:.2f}" for k, c in low.items())))
    else:
        results.append(_r("7_confidence", "PASS", f"sve reported stavke >= {CONF_THRESHOLD}"))

    blocking = [r for r in results if r["status"] in ("FAIL", "WARN")]
    status = "needs_review" if blocking else "validated"

    with conn.cursor() as cur:
        cur.execute("UPDATE filings SET status = %s WHERE id = %s", (status, filing_id))

    return {"status": status, "results": results}
