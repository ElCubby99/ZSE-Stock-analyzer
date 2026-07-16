#!/usr/bin/env python3
"""FAZA D (Metodologija v3): forenzika fer-zona — izvještaj PRIJE ijedne
promjene izračuna. NIŠTA u ovom skriptu ne mijenja bazu ni valuacije;
samo čita, računa dijagnostike i piše docs/forenzika_v3_faza_d.md.

Sadržaj po nalogu:
  A) top 15 po prometu (+ imena iz naloga koja nisu u top 15: CROS, INA):
     svi ulazi (ROE i iz koje godine, g i izvor, r i PUNI raspis rf/β/ERP/
     CRP/nelikvidnost), vrijednost svake metode, sidro i zašto, tržišna
     cijena, raskorak.
  B) reverse-r: r koji izjednačava projekciju s tržišnom cijenom, po svakoj
     r-ovisnoj metodi (bisekcija; comps/SOTP ne ovise o r pa nemaju reverse-r).
  C) konvergencija metoda vs sidro: parovi metoda koji konvergiraju (±20%)
     dok sidro od njihove sredine divergira >30%.
  D) TTM pokrivenost: firme s kvartalima u bazi (M18) koje vrednujemo iz
     zadnjeg GODIŠNJEG.
  E) ERP/CRP audit (double counting check) — činjenice iz koda i izvora.
"""
import copy
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn                      # noqa: E402
from src.params_calibrated import (              # noqa: E402
    ERP, ERP_SRC, RF, RF_SRC, build_params)
from src.beta_discipline import (                # noqa: E402
    LIQ_MIN_RATIO, LIQ_MIN_TURNOVER, resolve_beta)
from src.valuation_methods import (              # noqa: E402
    build_ctx, compute_dcf, compute_ddm, compute_justified_pb_roe,
    compute_residual_income, value_company)

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "docs" / "forenzika_v3_faza_d.md"
OUT_JSON = ROOT / "docs" / "forenzika_v3_faza_d.json"

EXTRA = ["CROS", "INA"]        # iz naloga, nisu u top 15 po prometu
R_METHODS = {                  # metode kojima vrijednost ovisi o r
    "dcf_fcf": compute_dcf,
    "ddm_gordon": compute_ddm,
    "justified_pb_roe": compute_justified_pb_roe,
    "residual_income": compute_residual_income,
}


def top_by_turnover(conn, n=15):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.ticker, SUM(p.turnover_eur)::bigint
            FROM prices_eod p JOIN companies c ON c.id = p.company_id
            WHERE p.trade_date > (SELECT MAX(trade_date) FROM prices_eod) - 365
            GROUP BY c.ticker ORDER BY 2 DESC NULLS LAST LIMIT %s""", (n,))
        return [(t, int(v or 0)) for t, v in cur.fetchall()]


def input_provenance(conn, ticker):
    """Iz koje godine dolaze net_income_parent / equity / revenue koje
    valuacija koristi (data() čita zadnje GODIŠNJE konsolidirano) + koji
    interim filingi POSTOJE (TTM potencijal)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, sector FROM companies WHERE ticker=%s", (ticker,))
        cid, sector = cur.fetchone()
        prov = {}
        for item in ("net_income_parent", "total_equity", "equity_parent",
                     "revenue", "total_operating_income", "ebitda",
                     "operating_cf", "capex", "dps"):
            cur.execute("""
                SELECT f.fiscal_year, fin.value_eur FROM financials fin
                JOIN filings f ON f.id = fin.filing_id
                WHERE f.company_id=%s AND fin.item=%s
                  AND f.period_type='annual' AND f.basis='consolidated'
                  AND fin.value_eur IS NOT NULL
                ORDER BY f.fiscal_year DESC LIMIT 1""", (cid, item))
            r = cur.fetchone()
            if r:
                prov[item] = {"fy": r[0], "value_eur": float(r[1])}
        cur.execute("""
            SELECT f.period_type, MAX(f.fiscal_year) FROM filings f
            WHERE f.company_id=%s AND f.period_type <> 'annual'
            GROUP BY f.period_type ORDER BY 2 DESC""", (cid,))
        prov["_interim_filings"] = [{"period": p, "fy": y} for p, y in cur.fetchall()]
        cur.execute("""
            SELECT MAX(f.fiscal_year) FROM filings f
            WHERE f.company_id=%s AND f.period_type='annual'
              AND f.basis='consolidated'""", (cid,))
        prov["_last_annual_fy"] = cur.fetchone()[0]
        # zadnja dividenda iz dividends (dps fallback u build_ctx)
        cur.execute("""
            SELECT d.amount_eur, d.div_type,
                   COALESCE(d.ex_date, d.payment_date)::text
            FROM dividends d JOIN share_classes sc ON sc.id=d.share_class_id
            WHERE d.company_id=%s AND d.div_type NOT ILIKE '%%rijedlog%%'
              AND d.amount_eur IS NOT NULL
            ORDER BY sc.is_primary_line DESC NULLS LAST,
                     COALESCE(d.ex_date, d.payment_date) DESC LIMIT 1""", (cid,))
        r = cur.fetchone()
        if r:
            prov["_last_dividend"] = {"amount": float(r[0]), "type": r[1], "date": r[2]}
        return sector, prov


def reverse_r(ctx, method_key, price, g_floor):
    """Bisekcija: r takav da metoda vrati bazu == tržišna cijena.
    Metode su padajuće u r. None ako cilj nije premostiv u [g+0.6pb, 40%]."""
    compute = R_METHODS[method_key]
    base_params = ctx.params

    def value_at(r):
        p2 = copy.deepcopy(base_params)
        p2.cost_of_equity = r
        p2.wacc = r
        ctx.params = p2
        try:
            return compute(ctx).base or None
        finally:
            ctx.params = base_params

    lo, hi = g_floor + 0.006, 0.40
    v_lo, v_hi = value_at(lo), value_at(hi)
    if v_lo is None or v_hi is None:
        return None
    # cilj izvan raspona vrijednosti -> nema smislenog implied r
    if not (min(v_lo, v_hi) <= price <= max(v_lo, v_hi)):
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        v = value_at(mid)
        if v is None:
            return None
        if (v - price) * (v_lo - price) > 0:
            lo, v_lo = mid, v
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def analyze(conn, ticker):
    sector, prov = input_provenance(conn, ticker)
    params = build_params(ticker)
    ctx = build_ctx(conn, ticker, params=params)
    out = value_company(ctx)
    rec = out["reconciliation"]

    # --- raspis r (rf + β×ERP + nelikvidnost; CRP je UNUTAR ERP-a — audit!)
    with conn.cursor() as cur:
        cur.execute("SELECT sector FROM companies WHERE ticker=%s", (ticker,))
        bd = resolve_beta(conn, ticker, cur.fetchone()[0])
    r_stack = {
        "rf": RF, "beta": bd["beta"], "beta_origin": bd["origin"],
        "erp": ERP, "erp_contains_crp": True,
        "illiq_premium": bd["illiq_premium"],
        "r_total": round(RF + bd["beta"] * ERP + bd["illiq_premium"], 4),
        "liquidity": {k: round(v, 3) if isinstance(v, float) else v
                      for k, v in bd["liquidity"].items()},
        "passes_liq_threshold": (bd["liquidity"]["ratio"] >= LIQ_MIN_RATIO
                                 and bd["liquidity"]["avg_turnover"] >= LIQ_MIN_TURNOVER),
    }

    methods = {}
    for k, r in out["ran"].items():
        vr = r["range"]
        methods[k] = {"label": r["label"], "low": vr.low, "base": vr.base,
                      "high": vr.high, "conf": vr.confidence}

    price, zone_lo, zone_hi = ctx.price, rec.get("zone_low"), rec.get("zone_high")
    gap = None
    if price and zone_lo is not None and zone_hi:
        mid = (zone_lo + zone_hi) / 2
        gap = price / mid - 1 if mid else None

    # ROE koji koristi opravdani P/B
    ni = prov.get("net_income_parent", {})
    eq = prov.get("equity_parent") or prov.get("total_equity") or {}
    roe = (ni.get("value_eur") / eq.get("value_eur")
           if ni.get("value_eur") is not None and eq.get("value_eur") else None)

    # reverse-r po r-ovisnoj metodi s pozitivnom bazom
    rev = {}
    if price:
        for k in R_METHODS:
            if methods.get(k, {}).get("base"):
                g_floor = (params.perpetual_growth
                           if k in ("justified_pb_roe", "residual_income")
                           else params.terminal_growth)
                rev[k] = reverse_r(ctx, k, price, g_floor)

    # konvergencija: parovi metoda ±20%, sidro divergira >30% od njihove
    # sredine. BEZ conf filtera (conf se prijavljuje) — dijagnostika mora
    # vidjeti i potvrde koje danas ne kvalificiraju, to je dio nalaza.
    anchor = (rec.get("anchor_methods") or [None])[0]
    conv = []
    keys = [k for k, m in methods.items() if m["base"] and m["base"] > 0]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a == anchor or b == anchor:
                continue
            va, vb = methods[a]["base"], methods[b]["base"]
            if abs(va / vb - 1) <= 0.20 and anchor and methods.get(anchor, {}).get("base"):
                pair_mid = (va + vb) / 2
                dev = methods[anchor]["base"] / pair_mid - 1
                if abs(dev) > 0.30:
                    conv.append({"pair": [a, b],
                                 "pair_conf": [methods[a]["conf"], methods[b]["conf"]],
                                 "pair_mid": round(pair_mid, 2),
                                 "anchor": anchor,
                                 "anchor_base": round(methods[anchor]["base"], 2),
                                 "anchor_vs_pair_pct": round(dev * 100, 1)})

    # klase naspram iste zone (ADRS/ADRS2 dijagnostika iz naloga)
    classes = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT sc.ticker, sc.class_type, px.close_eur, px.trade_date::text
            FROM share_classes sc
            JOIN companies c ON c.id = sc.company_id
            LEFT JOIN LATERAL (
                SELECT close_eur, trade_date FROM prices_eod p
                WHERE p.share_class_id = sc.id AND p.close_eur IS NOT NULL
                ORDER BY p.trade_date DESC LIMIT 1) px ON TRUE
            WHERE c.ticker=%s ORDER BY sc.is_primary_line DESC NULLS LAST""",
            (ticker,))
        for tk, ct, px, pd in cur.fetchall():
            g2 = None
            if px and zone_lo is not None and zone_hi:
                m2 = (zone_lo + zone_hi) / 2
                g2 = round((float(px) / m2 - 1) * 100, 1) if m2 else None
            classes.append({"class": tk, "type": ct,
                            "price": float(px) if px else None,
                            "date": pd, "gap_vs_mid_pct": g2})
    # koncentracija vlasništva (INA-tip dijagnostika): zbroj top-10 udjela
    own_top10 = None
    with conn.cursor() as cur:
        cur.execute("""
            SELECT SUM(s.pct)::float FROM shareholders s
            JOIN companies c ON c.id = s.company_id
            WHERE c.ticker=%s AND s.snapshot_date = (
                SELECT MAX(s2.snapshot_date) FROM shareholders s2
                WHERE s2.company_id = s.company_id)""", (ticker,))
        r = cur.fetchone()
        own_top10 = round(r[0], 1) if r and r[0] is not None else None

    gh = ctx.growth_hint or {}
    return {
        "classes": classes, "top10_holders_pct": own_top10,
        "ticker": ticker, "sector": sector,
        "archetype": rec.get("archetype"),
        "anchor": anchor, "anchor_note": rec.get("zone_note"),
        "zone_low": zone_lo, "zone_high": zone_hi,
        "price": price, "gap_vs_mid_pct": round(gap * 100, 1) if gap is not None else None,
        "r_stack": r_stack,
        "g": {"g1": gh.get("g1"), "forward": bool(gh.get("forward")),
              "g_perpetual": params.perpetual_growth,
              "g_terminal": params.terminal_growth,
              "source": (gh.get("source") or "nema serije — bez faze rasta")[:220]},
        "roe": {"value": round(roe, 4) if roe is not None else None,
                "ni_fy": ni.get("fy"), "eq_fy": eq.get("fy"),
                "basis": "zadnje GODIŠNJE konsolidirano (ne TTM)"},
        "inputs_provenance": prov,
        "methods": methods,
        "reverse_r": rev,
        "convergence_vs_anchor": conv,
        "qa_flags": rec.get("qa_flags"),
        "red_rules": rec.get("red_rules"),
    }


def main():
    with get_conn() as conn:
        top = top_by_turnover(conn, 15)
        tickers = [t for t, _ in top] + [t for t in EXTRA if t not in {x for x, _ in top}]
        results, errors = [], []
        for t in tickers:
            try:
                results.append(analyze(conn, t))
                print(f"[ok] {t}")
            except Exception as e:  # noqa: BLE001 — forenzika: zabilježi i nastavi
                conn.rollback()
                errors.append({"ticker": t, "error": str(e)[:300]})
                print(f"[ERR] {t}: {e}")

        # D) TTM pokrivenost za CIJELI univerzum
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.ticker,
                       MAX(f.fiscal_year) FILTER (WHERE f.period_type='annual') AS fy_a,
                       MAX(f.fiscal_year) FILTER (WHERE f.period_type<>'annual') AS fy_i,
                       ARRAY_AGG(DISTINCT f.period_type)
                         FILTER (WHERE f.period_type<>'annual') AS interim
                FROM filings f JOIN companies c ON c.id=f.company_id
                WHERE f.basis='consolidated'
                GROUP BY c.ticker HAVING
                  MAX(f.fiscal_year) FILTER (WHERE f.period_type<>'annual') IS NOT NULL
                ORDER BY c.ticker""")
            ttm = [{"ticker": t, "last_annual_fy": fa, "last_interim_fy": fi,
                    "interim_types": sorted(it or [])}
                   for t, fa, fi, it in cur.fetchall()]

    payload = {
        "generated": dt.date.today().isoformat(),
        "top15_by_turnover": top,
        "extra_from_order": EXTRA,
        "results": results, "errors": errors,
        "ttm_coverage": ttm,
        "erp_audit": {
            "rf": RF, "rf_src": RF_SRC, "erp": ERP, "erp_src": ERP_SRC,
            "finding_erp_contains_crp": (
                "ERP=5,7% = zreli 4,23% + CRP za Moody's A3 (~1,47 p.b.) — CRP je "
                "SKRIVEN u ERP-u, nije zasebna komponenta. Nelikvidnosna premija se "
                "dodaje ZASEBNO (samo ispod Z1 praga) pa formalnog double counta "
                "CRP+CRP nema, ali: (a) CRP nije vidljiv u raspisu; (b) rf je HR 10g "
                "(3,61%) koji VEĆ NOSI hrvatski spread naspram Bunda — zemlja se "
                "naplaćuje i u rf i u ERP-u = DOUBLE COUNT rizika zemlje; "
                "(c) A3/A- eurozona 2026. ne opravdava CRP iz starijih tablica."),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1,
                                   default=str), encoding="utf-8")
    print(f"-> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
