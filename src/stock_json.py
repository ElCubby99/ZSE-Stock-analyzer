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

# --- v2 sekcije: konfiguracija ---
FINANCIAL_SECTORS = {"bank", "insurance"}   # leverage guard (kao u valuation_methods)
LIQ_MIN_TURNOVER_EUR = 5000.0               # dnevni promet ispod -> low
LIQ_STALE_DAYS = 5                          # dana bez trgovine -> low
LIQ_VERY_LOW_SHARES = 3                     # komada -> very_low
LIQ_VERY_STALE_DAYS = 20                    # dana -> very_low

THREE_Y_ROWS = [
    ("revenue", "Poslovni prihodi"),
    ("ebitda", "EBITDA"),
    ("ebit", "EBIT"),
    ("net_income_parent", "Neto dobit matici"),
    ("eps", "EPS (dobit matici / dionica)"),
    ("operating_cf", "Operativni novčani tok"),
]

SEGMENT_LABELS = {
    "tourism": "Turizam", "insurance": "Osiguranje",
    "aquaculture": "Zdrava hrana (marikultura)", "energy": "Energetika",
}

# --- M5: bankovni prikazi (banka nema revenue/EBITDA u industrijskom smislu) ---
BANK_THREE_Y_ROWS = [
    ("total_operating_income", "Ukupni operativni prihod"),
    ("net_interest_income", "Neto kamatni prihod"),
    ("net_fee_income", "Neto prihod od naknada"),
    ("operating_expenses", "Operativni troškovi"),
    ("loan_loss_provisions", "Rezervacije (trošak rizika)"),
    ("net_income_parent", "Neto dobit matici"),
    ("eps", "EPS (dobit matici / dionica)"),
]

BANK_FUNDAMENTAL_ITEMS = [
    ("total_operating_income", "Ukupni operativni prihod"),
    ("net_interest_income", "Neto kamatni prihod"),
    ("net_fee_income", "Neto prihod od naknada i provizija"),
    ("operating_expenses", "Operativni troškovi"),
    ("loan_loss_provisions", "Rezervacije (trošak rizika)"),
    ("net_income", "Neto dobit (ukupno)"),
    ("net_income_parent", "Neto dobit matici"),
    ("total_assets", "Ukupna imovina"),
    ("equity_parent", "Kapital matici"),
    ("loans_to_customers", "Krediti klijentima"),
    ("deposits_from_customers", "Depoziti klijenata"),
    ("cet1_ratio", "CET1 stopa (Grupa)"),
    ("total_capital_ratio", "Ukupna stopa kapitala (Grupa)"),
    ("npl_ratio", "NPL omjer"),
    ("npl_coverage", "NPL pokrivenost"),
    ("dps", "Dividenda po dionici"),
]

BANK_RATIO_ITEMS = {"cet1_ratio", "total_capital_ratio", "npl_ratio",
                    "npl_coverage", "cost_of_risk"}


def _bank_kpi(cur, company_id: int, fiscal_year: int | None) -> dict | None:
    """M5 DIO D: bankovni KPI blok — izvučeno gdje je objavljeno, ostalo IZRAČUN
    iz izvučenih stavki (formula u basis). Bez podatka -> value null + missing."""
    if not fiscal_year:
        return None
    g = lambda item, fy=fiscal_year: _vfc(cur, company_id, fy, item)
    prev = fiscal_year - 1

    ni = g("net_income_parent")
    eq = g("equity_parent") or g("total_equity")
    ta, ta_prev = g("total_assets"), g("total_assets", prev)
    nii, toi = g("net_interest_income"), g("total_operating_income")
    opex, llp = g("operating_expenses"), g("loan_loss_provisions")
    loans, deps = g("loans_to_customers"), g("deposits_from_customers")
    loans_p, deps_p = g("loans_to_customers", prev), g("deposits_from_customers", prev)

    avg_ta = ((ta + ta_prev) / 2) if (ta and ta_prev) else ta
    kpis = [
        {"key": "roe", "label": "ROE", "unit": "pct",
         "value": (ni / eq) if (ni is not None and eq) else None,
         "basis": "izračun: neto dobit matici / kapital matici (kraj godine)"},
        {"key": "roa", "label": "ROA", "unit": "pct",
         "value": (ni / ta) if (ni is not None and ta) else None,
         "basis": "izračun: neto dobit matici / ukupna imovina"},
        {"key": "nim", "label": "NIM", "unit": "pct",
         "value": (nii / avg_ta) if (nii is not None and avg_ta) else None,
         "basis": ("izračun: NII / prosječna imovina (FY0, FY-1)" if ta_prev
                   else "izračun: NII / imovina na kraj godine (nema FY-1)")},
        {"key": "cir", "label": "Cost-to-income", "unit": "pct",
         "value": (abs(opex) / toi) if (opex is not None and toi) else None,
         "basis": "izračun: |operativni troškovi| / ukupni operativni prihod"},
        {"key": "cost_of_risk", "label": "Trošak rizika", "unit": "pct",
         "value": (g("cost_of_risk") if g("cost_of_risk") is not None else
                   ((-llp / loans) if (llp is not None and loans) else None)),
         "basis": ("izvučeno" if g("cost_of_risk") is not None else
                   "izračun: −rezervacije / krediti (kraj godine); negativno = neto otpuštanje")},
        {"key": "npl_ratio", "label": "NPL omjer", "unit": "pct",
         "value": g("npl_ratio"), "basis": "izvučeno (regulatory)"},
        {"key": "npl_coverage", "label": "NPL pokrivenost", "unit": "pct",
         "value": g("npl_coverage"), "basis": "izvučeno (regulatory)"},
        {"key": "cet1_ratio", "label": "CET1 stopa", "unit": "pct",
         "value": g("cet1_ratio"),
         "basis": "izvučeno (bilj. o regulatornom kapitalu)"},
        {"key": "total_capital_ratio", "label": "Ukupna stopa kapitala", "unit": "pct",
         "value": g("total_capital_ratio"),
         "basis": "izvučeno (bilj. o regulatornom kapitalu)"},
        {"key": "ldr", "label": "Krediti / depoziti (LDR)", "unit": "pct",
         "value": (loans / deps) if (loans and deps) else None,
         "basis": "izračun: krediti klijentima / depoziti klijenata"},
        {"key": "loans_yoy", "label": "Rast kredita YoY", "unit": "pct",
         "value": (loans / loans_p - 1) if (loans and loans_p) else None,
         "basis": "izračun iz FY0 vs FY-1"},
        {"key": "deposits_yoy", "label": "Rast depozita YoY", "unit": "pct",
         "value": (deps / deps_p - 1) if (deps and deps_p) else None,
         "basis": "izračun iz FY0 vs FY-1"},
    ]
    for k in kpis:
        k["missing"] = k["value"] is None
    return {
        "fiscal_year": fiscal_year,
        "kpis": kpis,
        "note": ("bankovni KPI: 'izvučeno' = objavljena brojka s izvorom u "
                 "fundamentima; 'izračun' = formula nad izvučenim stavkama; "
                 "bez podatka -> 'nema u bazi', ne nula. OGRADA za YoY: FY-1 "
                 "može dolaziti iz GFI obrasca a FY0 iz revidiranog godišnjeg "
                 "izvješća — definicije bilančnih linija mogu odstupati"),
    }


def _vfc(cur, company_id: int, fiscal_year: int, item: str):
    """Jedna stavka iz v_financials_current (annual/consolidated)."""
    cur.execute(
        """SELECT value_eur, confidence FROM v_financials_current
           WHERE company_id=%s AND fiscal_year=%s AND item=%s
             AND period_type='annual' AND basis='consolidated'""",
        (company_id, fiscal_year, item),
    )
    r = cur.fetchone()
    return _f(r[0]) if r else None


def _financials_3y(cur, company_id: int, shares: float | None,
                   rows_spec=None) -> dict:
    """DIO 1: zadnje 3 fiskalne godine + YoY (FY0 vs FY-1) + CAGR (FY-2 -> FY0)."""
    cur.execute(
        """SELECT DISTINCT fiscal_year FROM v_financials_current
           WHERE company_id=%s AND period_type='annual' AND basis='consolidated'
             AND statement IN ('income','balance','cashflow') AND item <> 'dps'
           ORDER BY fiscal_year DESC LIMIT 3""", (company_id,))
    years = sorted(r[0] for r in cur.fetchall())
    rows = []
    for item, label in (rows_spec or THREE_Y_ROWS):
        vals = {}
        for y in years:
            if item == "eps":
                ni = _vfc(cur, company_id, y, "net_income_parent")
                # EPS uz KANONSKI (današnji) broj dionica — napomena u note sekcije
                vals[str(y)] = (ni / shares) if (ni is not None and shares) else None
            else:
                vals[str(y)] = _vfc(cur, company_id, y, item)
        v = [vals.get(str(y)) for y in years]
        yoy = ((v[-1] / v[-2] - 1) if len(v) >= 2 and v[-1] is not None
               and v[-2] not in (None, 0) else None)
        cagr = None
        if len(v) >= 3 and v[0] is not None and v[-1] is not None and v[0] > 0 and v[-1] > 0:
            cagr = (v[-1] / v[0]) ** (1 / (len(v) - 1)) - 1
        rows.append({"item": item, "label": label, "values": vals,
                     "yoy_pct": yoy, "cagr_pct": cagr,
                     "unit": "eur_per_share" if item == "eps" else "eur"})
    return {
        "years": years,
        "rows": rows,
        "note": ("konsolidirano, godišnje (v_financials_current); EPS uz kanonski "
                 "današnji broj dionica bez trezorskih; prazno = nema u bazi, "
                 "ne procjenjuje se"),
    }


def _balance(cur, company_id: int, sector: str, fiscal_year: int | None,
             bvps: float | None) -> dict | None:
    """DIO 2: bilanca + leverage guard po sektoru (financije: bez net_debt)."""
    if not fiscal_year:
        return None
    is_fin = sector in FINANCIAL_SECTORS
    out = {
        "fiscal_year": fiscal_year,
        "is_financial": is_fin,
        "total_assets": _vfc(cur, company_id, fiscal_year, "total_assets"),
        "total_equity": _vfc(cur, company_id, fiscal_year, "total_equity"),
        "equity_parent": _vfc(cur, company_id, fiscal_year, "equity_parent"),
        "bvps": bvps,
    }
    if is_fin:
        out["leverage"] = None
        out["leverage_note"] = ("n/p — kod osiguratelja/banaka depoziti, pričuve i "
                                "obveze iz ugovora nisu financijski dug pa net_debt i "
                                "net_debt/EBITDA nemaju smisla (sektorski KPI dolaze zasebno)")
        return out
    nd = _vfc(cur, company_id, fiscal_year, "net_debt")
    ebitda = _vfc(cur, company_id, fiscal_year, "ebitda")
    out["leverage"] = {
        "net_debt": nd,
        "net_debt_to_ebitda": (nd / ebitda) if (nd is not None and ebitda) else None,
        "current_ratio": None,   # kratkoročna imovina/obveze nisu u kanonskim stavkama
        "current_ratio_note": "tekući omjer: kratkoročne stavke nisu u bazi",
        "components_note": "net_debt = debt_short + debt_long − novac (izračun iz ekstrakcije)",
    }
    if sector == "holding":
        out["leverage_note"] = ("holding konsolidira osiguratelja — grupni "
                                "net_debt/EBITDA uzeti s oprezom (miješa financijski "
                                "i operativni dio)")
    return out


def _liquidity(cur, classes: list[dict], as_of) -> dict:
    """DIO 3: flag likvidnosti po klasi iz prices_eod (zadnji dan s prometom)."""
    from datetime import date, datetime

    out_classes = []
    for c in classes:
        cur.execute("SELECT id FROM share_classes WHERE ticker=%s", (c["ticker"],))
        r = cur.fetchone()
        sc_id = r[0] if r else None
        last_trade = None
        if sc_id is not None:
            cur.execute(
                """SELECT trade_date, close_eur, volume FROM prices_eod
                   WHERE share_class_id=%s AND volume IS NOT NULL AND volume > 0
                   ORDER BY trade_date DESC LIMIT 1""", (sc_id,))
            r = cur.fetchone()
            if r:
                last_trade = {"date": str(r[0]), "close_eur": _f(r[1]),
                              "volume": _f(r[2]),
                              "turnover_eur": (_f(r[1]) or 0) * (_f(r[2]) or 0)}
        cur.execute(
            """SELECT MIN(trade_date) FROM prices_eod p
               JOIN share_classes sc ON sc.id=p.share_class_id
               WHERE sc.ticker=%s""", (c["ticker"],))
        r = cur.fetchone()
        data_from = str(r[0]) if r and r[0] else None

        if last_trade is None:
            flag = "very_low"
            days = None
            note = (f"u dostupnim podacima (od {data_from or '—'}) nema zabilježene "
                    f"trgovine — zadnji close je indikativan, ne transakcijski")
        else:
            days = (as_of - datetime.strptime(last_trade["date"], "%Y-%m-%d").date()).days
            vol, tov = last_trade["volume"], last_trade["turnover_eur"]
            if vol < LIQ_VERY_LOW_SHARES or days > LIQ_VERY_STALE_DAYS:
                flag = "very_low"
            elif tov < LIQ_MIN_TURNOVER_EUR or days > LIQ_STALE_DAYS:
                flag = "low"
            else:
                flag = "ok"
            note = (f"zadnja trgovina {last_trade['date']}: {vol:.0f} kom / "
                    f"{tov:,.0f} € prometa ({days} d)")
        out_classes.append({"class_ticker": c["ticker"], "last_trade": last_trade,
                            "days_since_trade": days, "flag": flag, "note": note})
    return {
        "as_of": str(as_of),
        "thresholds": {"min_turnover_eur": LIQ_MIN_TURNOVER_EUR,
                       "stale_days": LIQ_STALE_DAYS,
                       "very_low_shares": LIQ_VERY_LOW_SHARES,
                       "very_stale_days": LIQ_VERY_STALE_DAYS},
        "classes": out_classes,
        "note": ("cijena bez prometa je indikativna; flag: low = dnevni promet < "
                 f"{LIQ_MIN_TURNOVER_EUR:.0f} € ili > {LIQ_STALE_DAYS} d bez trgovine; "
                 f"very_low = < {LIQ_VERY_LOW_SHARES} kom ili > {LIQ_VERY_STALE_DAYS} d"),
    }


def _segments(cur, company_id: int, fiscal_year: int | None) -> dict | None:
    """DIO 4: IFRS 8 segmenti (samo objavljeni ključevi; izvedeni interni ključevi
    poput 'tourism_hup' su SOTP ulaz, ne objavljeni segment — ne prikazuju se)."""
    if not fiscal_year:
        return None
    cur.execute(
        """SELECT segment_key, revenue, ebitda, net_result, confidence, source_page
           FROM segment_financials
           WHERE company_id=%s AND fiscal_year=%s AND period_type='annual'
             AND basis='consolidated' AND segment_key = ANY(%s)
           ORDER BY revenue DESC NULLS LAST""",
        (company_id, fiscal_year, list(SEGMENT_LABELS)),
    )
    rows = []
    for key, rev, ebitda, net, conf, src in cur.fetchall():
        rev, ebitda, net = _f(rev), _f(ebitda), _f(net)
        rows.append({"key": key, "label": SEGMENT_LABELS.get(key, key),
                     "revenue": rev, "ebitda": ebitda, "net_result": net,
                     "ebitda_margin": (ebitda / rev) if (ebitda is not None and rev) else None,
                     "confidence": _f(conf), "source_page": src})
    if not rows:
        return None
    rev_sum = sum(r["revenue"] for r in rows if r["revenue"] is not None)
    ebitda_sum = sum(r["ebitda"] for r in rows if r["ebitda"] is not None)
    ebitda_missing = [r["label"] for r in rows if r["ebitda"] is None]
    group_rev = _vfc(cur, company_id, fiscal_year, "revenue")
    group_ebitda = _vfc(cur, company_id, fiscal_year, "ebitda")
    # Usporedivost prihoda: kanonski 'revenue' ne uključuje premije osiguranja,
    # pa je za grupe s osiguranjem Σ segmenata > grupni 'revenue'. Tada je
    # reconciliation prihoda N/P (usporedivi ukupni prihod nije u bazi) —
    # nikako ne prikazivati negativan "ostatak" kao eliminacije.
    rev_comparable = bool(group_rev and rev_sum and rev_sum <= group_rev * 1.02)
    return {
        "fiscal_year": fiscal_year,
        "rows": rows,
        "reconciliation": {
            "revenue_sum": rev_sum or None,
            "group_revenue": group_rev,
            "revenue_comparable": rev_comparable,
            "revenue_residual": (group_rev - rev_sum) if rev_comparable else None,
            "revenue_note": (None if rev_comparable else
                             "n/p — Σ segmenata uključuje premije osiguranja, a grupni "
                             "'revenue' u bazi ne; usporedivi ukupni prihod (bilj. o "
                             "segmentima) nije među kanonskim stavkama"),
            "ebitda_sum": ebitda_sum or None,
            "group_ebitda": group_ebitda,
            "ebitda_missing_segments": ebitda_missing,
            "note": ("ostatak = eliminacije/centar; segmentne brojke uključuju "
                     "unutargrupne odnose (bilj. o segmentima)"
                     + ("; Σ EBITDA nepotpun — bez EBITDA: " + ", ".join(ebitda_missing)
                        if ebitda_missing else "")),
        },
    }


def _ownership(cur, company_id: int, ticker: str) -> dict:
    """DIO 5: obrnuti holdings graf — tko drži OVU firmu + približni free float."""
    cur.execute(
        """SELECT p.name, p.ticker, h.ownership_pct, h.source_page
           FROM holdings h JOIN companies p ON p.id = h.parent_company_id
           WHERE h.held_company_id = %s ORDER BY h.ownership_pct DESC""",
        (company_id,),
    )
    holders = [{"name": n, "ticker": t, "pct": _f(pct), "source": src}
               for n, t, pct, src in cur.fetchall()]
    if holders:
        known = sum(h["pct"] for h in holders)
        ff = max(0.0, 1.0 - known)
        note = ("free float ≈ 100% − poznati većinski udjeli iz vlasničkog grafa; "
                "manji imatelji nisu u bazi")
        liq_link = (f"manjinski free float (~{ff * 100:.1f}%) znači plitku knjigu "
                    "naloga — vidi oznaku likvidnosti uz cijenu"
                    if ff < 0.40 else None)
    else:
        known, ff = None, None
        note = ("u bazi nema zabilježenih većinskih imatelja za ovu firmu — "
                "free float nepoznat (ne procjenjuje se)")
        liq_link = None
    return {"holders": holders, "known_pct": known,
            "free_float_pct_approx": ff, "note": note, "liquidity_link": liq_link}


def _f(x):
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return x


def _fundamentals(cur, company_id: int, items_spec=None) -> list[dict]:
    rows = []
    for item, label in (items_spec or FUNDAMENTAL_ITEMS):
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
        unit = ("pct" if item in BANK_RATIO_ITEMS
                else "eur_per_share" if item == "dps" else "eur")
        rows.append({
            "item": item, "label": label, "unit": unit,
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
    is_bank = sector == "bank"

    fund = _fundamentals(cur, company_id,
                         BANK_FUNDAMENTAL_ITEMS if is_bank else FUNDAMENTAL_ITEMS)
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
    assumption_flags = []
    if not params.beta_calibrated:
        assumption_flags.append(
            {"key": "beta", "label": "β = 1,0", "status": "pretpostavka",
             "why": "beta nije kalibrirana za ovu firmu (serija prekratka/"
                    "nelikvidna) — vidi src/calibrate.py"})
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

    from datetime import date
    today = date.today()

    return {
        "ticker": ticker, "name": name, "sector": sector, "is_group": is_group,
        "isin": comp_isin, "fiscal_year": latest_fy, "audited": audited,
        "generated_at": str(today),
        "financials_3y": _financials_3y(cur, company_id, shares,
                                        BANK_THREE_Y_ROWS if is_bank else THREE_Y_ROWS),
        "balance": _balance(cur, company_id, sector, latest_fy, bvps),
        "liquidity": _liquidity(cur, classes, today),
        "segments": _segments(cur, company_id, latest_fy),
        "ownership": _ownership(cur, company_id, ticker),
        "bank_kpi": _bank_kpi(cur, company_id, latest_fy) if is_bank else None,
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
