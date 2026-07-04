"""JSON za stranicu dionice (M4): sve iz baze + postojećeg valuacijskog motora.

Frontend samo ČITA ovaj JSON — ovdje se NE mijenja eligibility ni valuation
logika; poziva se postojeći value_company s kalibriranim Params. Svaka brojka
nosi izvor gdje postoji (source_page + source_url filinga, izvor cijene,
sources blok pretpostavki). Što fali u bazi -> null + oznaka, ne izmišlja se.

MAR: izlaz su metode/rasponi/pretpostavke — bez preporuka.

CLI:
  python -m src.stock_json ADRS            # ispiši JSON na stdout
  python -m src.stock_json ADRS CROS --out data/exports
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

from .db import get_conn
from .params_calibrated import build_params
from .valuation_methods import REGISTRY, build_ctx, value_company

# stavke fundamenata za prikaz (redoslijed = redoslijed u tablici na stranici)
FUNDAMENTAL_ITEMS = [
    ("revenue", "Poslovni prihodi"),
    ("ebitda", "EBITDA"),
    ("ebit", "EBIT"),
    ("net_income", "Neto dobit (ukupno)"),
    ("net_income_parent", "Neto dobit matici"),
    ("net_income_minority", "Manjinski interesi (dobit)"),
    ("total_assets", "Ukupna imovina"),
    ("total_equity", "Ukupni kapital"),
    ("equity_parent", "Kapital matici"),
    ("net_debt", "Neto dug"),
    ("cash_and_equivalents", "Novac i ekvivalenti"),
    ("operating_cf", "Operativni novčani tok"),
    ("capex", "Capex"),
    ("dps", "Dividenda po dionici"),
]

METHOD_LABELS = {m.key: m.label for m in REGISTRY}


def _f(x):
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return x


def _fundamentals(cur, company_id: int) -> list[dict]:
    rows = []
    for item, label in FUNDAMENTAL_ITEMS:
        cur.execute(
            """SELECT fin.value_eur, fin.confidence, fin.source_page,
                      fin.fiscal_year, f.source_url, f.audited, f.doc_type
               FROM financials fin JOIN filings f ON f.id = fin.filing_id
               WHERE f.company_id = %s AND fin.item = %s
                 AND f.period_type = 'annual' AND f.basis = 'consolidated'
               ORDER BY f.fiscal_year DESC LIMIT 1""",
            (company_id, item),
        )
        r = cur.fetchone()
        rows.append({
            "item": item, "label": label,
            "value_eur": _f(r[0]) if r else None,
            "confidence": _f(r[1]) if r else None,
            "source_page": r[2] if r else None,
            "fiscal_year": r[3] if r else None,
            "source_url": r[4] if r else None,
            "audited": r[5] if r else None,
            "missing": r is None or r[0] is None,
        })
    return rows


def _val(fund: list[dict], item: str):
    for row in fund:
        if row["item"] == item:
            return row["value_eur"]
    return None


def _share_classes(cur, company_id: int) -> list[dict]:
    cur.execute(
        """SELECT sc.id, sc.ticker, sc.class_type, sc.isin, sc.shares_issued,
                  COALESCE(sc.treasury_shares, 0), sc.is_primary_line, sc.dividend_note
           FROM share_classes sc WHERE sc.company_id = %s
           ORDER BY sc.is_primary_line DESC, sc.ticker""",
        (company_id,),
    )
    out = []
    for cid, tk, ctype, isin, issued, treas, prim, note in cur.fetchall():
        cur.execute(
            """SELECT close_eur, trade_date, volume, source FROM prices_eod
               WHERE share_class_id = %s AND close_eur IS NOT NULL
               ORDER BY trade_date DESC LIMIT 1""", (cid,))
        p = cur.fetchone()
        out.append({
            "ticker": tk, "class_type": ctype, "isin": isin,
            "shares_issued": _f(issued), "treasury_shares": _f(treas),
            "shares_ex_treasury": _f(issued) - _f(treas) if issued is not None else None,
            "is_primary": bool(prim), "note": note,
            "last_price": ({"close_eur": _f(p[0]), "trade_date": str(p[1]),
                            "volume": _f(p[2]), "source": p[3]} if p else None),
        })
    return out


def _price_history(cur, company_id: int) -> list[dict]:
    cur.execute(
        """SELECT COALESCE(sc.ticker, c.ticker), p.trade_date, p.close_eur, p.volume, p.source
           FROM prices_eod p JOIN companies c ON c.id = p.company_id
           LEFT JOIN share_classes sc ON sc.id = p.share_class_id
           WHERE p.company_id = %s ORDER BY p.trade_date, 1""", (company_id,))
    return [{"class_ticker": r[0], "trade_date": str(r[1]), "close_eur": _f(r[2]),
             "volume": _f(r[3]), "source": r[4]} for r in cur.fetchall()]


def _per_class_ratios(classes: list[dict], eps, bvps, dps) -> list[dict]:
    """P/E, P/B, div. prinos po klasi iz zadnjeg closea. Izvedeno iz baze — bez novih brojki."""
    out = []
    for c in classes:
        px = c["last_price"]["close_eur"] if c["last_price"] else None
        out.append({
            "class_ticker": c["ticker"],
            "price": px,
            "pe": (px / eps) if (px and eps and eps > 0) else None,
            "pb": (px / bvps) if (px and bvps and bvps > 0) else None,
            "div_yield": (dps / px) if (px and dps) else None,
            "basis": "izvedeno: zadnji close / per-share iz FY financija",
        })
    return out


def build_stock_json(conn, ticker: str) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT id, name, sector, is_group, isin FROM companies WHERE ticker = %s",
                (ticker,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"nepoznat ticker: {ticker}")
    company_id, name, sector, is_group, comp_isin = row

    fund = _fundamentals(cur, company_id)
    classes = _share_classes(cur, company_id)

    # valuacija: postojeći motor, kalibrirani Params (read-only za frontend)
    params = build_params(ticker)
    ctx = build_ctx(conn, ticker, params=params)
    result = value_company(ctx)

    ran = []
    for key, r in result["ran"].items():
        vr = r["range"]
        ran.append({
            "key": key, "label": r["label"],
            "low": _f(vr.low), "base": _f(vr.base), "high": _f(vr.high),
            "confidence": _f(vr.confidence),
            "no_value": not vr.base,
            "assumptions": json.loads(json.dumps(vr.assumptions, default=_f)),
        })
    skipped = [{"key": k, "label": METHOD_LABELS.get(k, k), "reason": v}
               for k, v in result["skipped"].items()]
    rec = result["reconciliation"]
    reconciliation = (None if rec.get("status") == "no_value" else {
        "zone_low": _f(rec.get("zone_low")), "zone_high": _f(rec.get("zone_high")),
        "dispersion": _f(rec.get("dispersion")), "divergent": rec.get("divergent"),
        "method_bases": {k: _f(v) for k, v in (rec.get("method_bases") or {}).items()},
    })

    shares = _f(ctx.shares_ex_treasury)
    ni_parent = _val(fund, "net_income_parent")
    eq_parent = _val(fund, "equity_parent") or _val(fund, "total_equity")
    dps = _val(fund, "dps")
    eps = (ni_parent / shares) if (ni_parent and shares) else None
    bvps = (eq_parent / shares) if (eq_parent and shares) else None
    roe = (ni_parent / eq_parent) if (ni_parent and eq_parent) else None

    # sotp breakdown (ako je metoda pokrenuta) — komponente + placeholder zastave
    sotp = next((m for m in ran if m["key"] == "sotp_nav"), None)
    sotp_breakdown = None
    if sotp:
        a = sotp["assumptions"]
        sotp_breakdown = {
            "parts": a.get("parts") or [],
            "net_cash": a.get("net_cash"),
            "net_cash_note": a.get("net_cash_note"),
            "nav_gross_eur": a.get("nav_gross_eur"),
            "nav_total_eur": a.get("nav_total_eur"),
            "holding_discount_range": a.get("holding_discount_range"),
            "holding_discount_reason": a.get("holding_discount_reason"),
            "market_check": a.get("market_check"),
            "missing": a.get("missing"),
        }

    # pretpostavke s izvorima (read-only na stranici) + eksplicitne oznake nesigurnosti
    assumption_flags = [
        {"key": "beta", "label": "β = 1,0", "status": "pretpostavka",
         "why": "nema povijesne serije cijena za procjenu bete"},
    ]
    if sotp_breakdown is not None:  # samo gdje se SOTP primjenjuje
        assumption_flags += [
            {"key": "holding_discount", "label": "holding diskont 15–25%",
             "status": "pretpostavka",
             "why": "povijesni diskont neizvediv iz baze (premalo dana cijena)"},
            {"key": "sotp_multiples", "label": "SOTP multiple neuvrštenih (7,5 / 8,0 / 7,0×)",
             "status": "pretpostavka", "why": "default multiple, nisu tržišno kalibrirane"},
        ]
    if not params.peers_calibrated:
        assumption_flags.append(
            {"key": "peer_multiples", "label": "peer multipli (P/E 12, P/B 1,5)",
             "status": "pretpostavka",
             "why": "nema usporedivog osiguratelja na ZSE (docs/peers.md)"})

    latest_fy = max((r["fiscal_year"] for r in fund if r["fiscal_year"]), default=None)
    audited = any(r["audited"] for r in fund if r["audited"] is not None)

    return {
        "ticker": ticker, "name": name, "sector": sector, "is_group": is_group,
        "isin": comp_isin, "fiscal_year": latest_fy, "audited": audited,
        "share_classes": classes,
        "metrics": {
            "eps": eps, "bvps": bvps, "roe": roe, "dps": dps,
            "shares_ex_treasury": shares,
            "market_cap_eur": _f(ctx.own_market_cap),
            "ebitda_eur": _val(fund, "ebitda"),
            "per_class": _per_class_ratios(classes, eps, bvps, dps),
            "basis_note": ("per-share: FY konsolidirane financije / dionice bez "
                           "trezorskih; trž.kap = Σ zadnji close klase × dionice klase"),
        },
        "fundamentals": fund,
        "prices": _price_history(cur, company_id),
        "valuation": {
            "params": {
                "r": _f(params.cost_of_equity), "g": _f(params.perpetual_growth),
                "holding_discount_low": _f(params.holding_discount_low),
                "holding_discount_high": _f(params.holding_discount_high),
                "peer_pe": _f(params.peer_pe), "peer_pb": _f(params.peer_pb),
                "rates_calibrated": params.rates_calibrated,
                "peers_calibrated": params.peers_calibrated,
                "sources": params.sources,
            },
            "assumption_flags": assumption_flags,
            "ran": ran, "skipped": skipped, "reconciliation": reconciliation,
            "sotp": sotp_breakdown,
        },
        "mar_note": ("Informativni prikaz metoda, raspona i pretpostavki iz javno "
                     "objavljenih izvješća; nije investicijski savjet ni preporuka."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="JSON za stranicu dionice")
    p.add_argument("tickers", nargs="+")
    p.add_argument("--out", default=None, help="direktorij za <ticker>.json (default: stdout)")
    a = p.parse_args(argv)
    with get_conn() as conn:
        for t in a.tickers:
            data = build_stock_json(conn, t)
            if a.out:
                import os
                os.makedirs(a.out, exist_ok=True)
                # UPPERCASE ime: frontend statično čita /data/<TICKER>.json
                path = f"{a.out}/{t.upper()}.json"
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"zapisano {path}")
            else:
                json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
                print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
