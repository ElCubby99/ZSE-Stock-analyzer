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


def _pct_hr(x, dec=1):
    return f"{x * 100:+.{dec}f}%".replace(".", ",")


def _meur_hr(x):
    return f"{x / 1e6:,.1f} M€".replace(",", "X").replace(".", ",").replace("X", ".")


def _direction(first, last, thresh=0.01):
    """Smjer iz brojki: rast/pad/stabilno — bez epiteta."""
    if first is None or last is None or not first:
        return None
    ch = last / first - 1
    if abs(ch) <= thresh:
        return "stabilno"
    return "rast" if ch > 0 else "pad"


def _trend(cur, company_id: int, sector: str) -> dict | None:
    """Trend prihoda i EBITDA-e kroz dostupne godine (do 3) + ČINJENIČNA
    naracija: samo brojke i smjer (rast/pad/stabilno), bez epiteta.
    Banka: prihod = ukupni operativni prihod, EBITDA n/p.
    Godina koje nema u bazi -> preskočena u nizu, navedena u napomeni."""
    is_bank = sector == "bank"
    is_fin = sector in FINANCIAL_SECTORS
    rev_item = "total_operating_income" if is_bank else "revenue"
    rev_label = "Ukupni operativni prihod" if is_bank else "Prihodi"
    cur.execute(
        """SELECT DISTINCT fiscal_year FROM v_financials_current
           WHERE company_id=%s AND period_type='annual' AND basis='consolidated'
             AND statement IN ('income','balance','cashflow') AND item <> 'dps'
           ORDER BY fiscal_year DESC LIMIT 3""", (company_id,))
    years = sorted(r[0] for r in cur.fetchall())
    if not years:
        return None
    series = []
    for y in years:
        rev = _vfc(cur, company_id, y, rev_item)
        ebd = None if is_fin else _vfc(cur, company_id, y, "ebitda")
        series.append({
            "year": y, "revenue": _f(rev), "ebitda": _f(ebd),
            "ebitda_margin": (_f(ebd / rev) if (ebd is not None and rev) else None),
        })

    # naracija — SAMO brojke i smjer; rečenice se grade iz podataka
    parts, missing = [], []
    rv = [(s["year"], s["revenue"]) for s in series if s["revenue"] is not None]
    missing += [f"FY{s['year']}: {rev_label.lower()} nema u bazi"
                for s in series if s["revenue"] is None]
    if len(rv) >= 2:
        chain = [f"{rv[0][0]}. {_meur_hr(rv[0][1])}"]
        for (y0, v0), (y1, v1) in zip(rv, rv[1:]):
            chain.append(f"{y1}. {_meur_hr(v1)} ({_pct_hr(v1 / v0 - 1)})"
                         if v0 else f"{y1}. {_meur_hr(v1)}")
        d = _direction(rv[0][1], rv[-1][1])
        tot = (f"; ukupno kroz razdoblje {_pct_hr(rv[-1][1] / rv[0][1] - 1)}"
               if rv[0][1] else "")
        parts.append(f"{rev_label}: " + " → ".join(chain)
                     + (f". Smjer: {d}{tot}." if d else "."))
    elif len(rv) == 1:
        parts.append(f"{rev_label}: samo {rv[0][0]}. u bazi ({_meur_hr(rv[0][1])}) "
                     f"— trend se ne računa iz jedne godine.")
    if is_fin:
        parts.append("EBITDA: n/p za financijski sektor"
                     + (" — vidi bankovne pokazatelje (CIR, NIM)." if is_bank else
                        " (osiguranje: premije/pričuve, ne operativna marža)."))
    else:
        mg = [(s["year"], s["ebitda_margin"]) for s in series
              if s["ebitda_margin"] is not None]
        missing += [f"FY{s['year']}: EBITDA nema u bazi"
                    for s in series if s["ebitda"] is None]
        if len(mg) >= 2:
            chain = " → ".join(f"{m * 100:.1f}%".replace(".", ",") for _, m in mg)
            d = _direction(mg[0][1], mg[-1][1])
            parts.append(f"EBITDA marža: {chain} ({mg[0][0]}.–{mg[-1][0]}.)."
                         + (f" Smjer: {d}." if d else ""))
        elif len(mg) == 1:
            parts.append(f"EBITDA marža: {mg[0][1] * 100:.1f}%".replace(".", ",")
                         + f" ({mg[0][0]}.) — jedna godina u bazi.")
    if missing:
        parts.append("Nedostaje: " + "; ".join(missing) + ".")
    return {
        "series": series,
        "revenue_label": rev_label,
        "narration": " ".join(parts) if parts else None,
        "note": ("naracija je izvedena isključivo iz brojki u bazi (bez ocjena); "
                 "smjer = usporedba ruba razdoblja uz prag ±1%"),
    }


def _risks(sector, is_group, sotp, liquidity, ownership, assumption_flags,
           bank_kpi, rec) -> dict:
    """DIO 1: 'Rizici i kontekst' — ČINJENIČNE kartice izvedene isključivo iz
    podataka u ovom exportu (brojke + činjenice, bez ocjena i preporuka)."""
    cards = []
    if sotp and sotp.get("market_vs_fair_pct") is not None:
        mv = sotp["market_vs_fair_pct"]
        cards.append({"l": "SOTP RASKORAK",
                      "txt": (f"Tržište vrednuje uvrštene kćeri {mv:+.1f}% u odnosu "
                              f"na našu fer-procjenu; fer-zona matice koristi našu "
                              f"procjenu, pa razlika ostaje otvoreno pitanje tržišta.")})
    if is_group and sotp and sotp.get("parts"):
        deps = ", ".join(f"{p['name']} ({p['pct']:.0%})" for p in sotp["parts"][:4])
        cards.append({"l": "OVISNOST O KĆERIMA",
                      "txt": f"Vrijednost i dividende matice ovise o društvima: {deps}."})
    ff = (ownership or {}).get("free_float_pct_approx")
    liq_flags = [c for c in (liquidity or {}).get("classes", []) if c["flag"] != "ok"]
    if ff is not None and ff < 0.40 or liq_flags:
        t = []
        if ff is not None and ff < 0.40:
            t.append(f"free float približno {ff:.0%}")
        for c in liq_flags[:2]:
            t.append(f"{c['class_ticker']}: {c['note']}")
        cards.append({"l": "KONCENTRACIJA I LIKVIDNOST", "txt": "; ".join(t) + "."})
    if bank_kpi:
        miss = [k["label"] for k in bank_kpi["kpis"] if k["missing"]]
        if miss:
            cards.append({"l": "REGULATORNI POKAZATELJI",
                          "txt": ("U izvješću nisu objavljeni (nema u bazi): "
                                  + ", ".join(miss[:4]) + ".")})
    if assumption_flags:
        cards.append({"l": "PRETPOSTAVKE PROCJENE",
                      "txt": ("Procjena počiva na označenim pretpostavkama: "
                              + "; ".join(f["label"] for f in assumption_flags) + ".")})
    if rec and rec.get("dispersion_all") and rec["dispersion_all"] > 0.30:
        cards.append({"l": "RASKORAK METODA",
                      "txt": (f"Sve metode zajedno raspinju "
                              f"{rec['all_methods_low']:,.0f}–{rec['all_methods_high']:,.0f} € "
                              f"(raspon {rec['dispersion_all'] * 100:.0f}%) — svaka leća "
                              f"mjeri drugo svojstvo; sidrena zona je uža.")})
    return {"cards": cards[:4],
            "note": ("činjenični kontekst izveden iz podataka ovog exporta — "
                     "bez ocjena i preporuka; zaključak je čitateljev")}


def _news(cur, company_id: int) -> dict:
    """Novosti tab: SLUŽBENE objave izdavatelja (EHO) — naslov+datum+link kako
    jesu; bez medija, bez agregacije, bez komentara."""
    cur.execute(
        """SELECT published_at, title, source_url, category FROM announcements
           WHERE company_id=%s AND title IS NOT NULL
           ORDER BY published_at DESC NULLS LAST LIMIT 30""", (company_id,))
    items = [{"date": str(d) if d else None, "title": t, "url": u, "category": c}
             for d, t, u, c in cur.fetchall()]
    return {"items": items,
            "note": ("službene objave izdavatelja s EHO-a (zse.hr) — bez medijskih "
                     "napisa i bez komentara platforme; prazno = nema objava u bazi")}


def _business_profile(cur, company_id: int) -> dict | None:
    """M9: profil poslovanja — činjenice iz izvješća s citatima; epiteti
    izdavatelja ODVOJENO u issuer_claims. Nema profila -> null (frontend
    prikazuje 'nema u bazi', ništa se ne generira)."""
    cur.execute(
        """SELECT fiscal_year, activity, activity_source_page, segments,
                  markets, export_share, issuer_claims, source
           FROM business_profiles WHERE company_id=%s""", (company_id,))
    r = cur.fetchone()
    if not r:
        return None
    return {
        "fiscal_year": r[0], "activity": r[1], "activity_source_page": r[2],
        "segments": r[3] or [], "markets": r[4] or [],
        "export_share": r[5], "issuer_claims": r[6] or [], "source": r[7],
        "note": ("samo činjenice iz izvješća s citatima; kvalitativne tvrdnje "
                 "('vodeći' i sl.) su TVRDNJE IZDAVATELJA, označene i citirane "
                 "— platforma ih ne generira niti potvrđuje"),
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
                """SELECT trade_date, close_eur, volume, turnover_eur FROM prices_eod
                   WHERE share_class_id=%s AND volume IS NOT NULL AND volume > 0
                   ORDER BY trade_date DESC LIMIT 1""", (sc_id,))
            r = cur.fetchone()
            if r:
                # stvarni promet iz tečajnice kad postoji; inače close×volumen
                tov = _f(r[3]) if r[3] is not None else (_f(r[1]) or 0) * (_f(r[2]) or 0)
                last_trade = {"date": str(r[0]), "close_eur": _f(r[1]),
                              "volume": _f(r[2]), "turnover_eur": tov}
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
        """SELECT COALESCE(sc.ticker, c.ticker), p.trade_date, p.close_eur, p.volume,
                  p.turnover_eur, p.source
           FROM prices_eod p JOIN companies c ON c.id = p.company_id
           LEFT JOIN share_classes sc ON sc.id = p.share_class_id
           WHERE p.company_id = %s ORDER BY p.trade_date, 1""", (company_id,))
    return [{"class_ticker": r[0], "trade_date": str(r[1]), "close_eur": _f(r[2]),
             "volume": _f(r[3]), "turnover_eur": _f(r[4]), "source": r[5]}
            for r in cur.fetchall()]


def _price_summary(cur, classes: list[dict], as_of) -> dict:
    """Zaglavlje profila po klasi: zadnja cijena, dnevna promjena, 52-tjedni
    raspon, prosječni promet — SVE iz prices_eod, ništa izvedeno izvan baze."""
    from datetime import timedelta

    cutoff_52w = as_of - timedelta(days=365)
    out = []
    for c in classes:
        cur.execute("SELECT id FROM share_classes WHERE ticker=%s", (c["ticker"],))
        r = cur.fetchone()
        if not r:
            continue
        sc_id = r[0]
        cur.execute(
            """SELECT trade_date, close_eur FROM prices_eod
               WHERE share_class_id=%s AND close_eur IS NOT NULL
               ORDER BY trade_date DESC LIMIT 2""", (sc_id,))
        rows = cur.fetchall()
        if not rows:
            out.append({"class_ticker": c["ticker"], "last": None,
                        "note": "nema cijena u bazi"})
            continue
        last_d, last_px = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        change_pct = ((float(last_px) / float(prev[1])) - 1.0) if prev and prev[1] else None
        cur.execute(
            """SELECT MAX(close_eur), MIN(close_eur) FROM prices_eod
               WHERE share_class_id=%s AND close_eur IS NOT NULL
                 AND trade_date >= %s""", (sc_id, cutoff_52w))
        hi52, lo52 = cur.fetchone()
        cur.execute(
            """SELECT AVG(t) FROM (SELECT turnover_eur AS t FROM prices_eod
                 WHERE share_class_id=%s AND turnover_eur IS NOT NULL
                 ORDER BY trade_date DESC LIMIT 20) x""", (sc_id,))
        avg_tov = cur.fetchone()[0]
        cur.execute("SELECT MIN(trade_date) FROM prices_eod WHERE share_class_id=%s",
                    (sc_id,))
        data_from = cur.fetchone()[0]
        note = None
        if data_from and data_from > cutoff_52w:
            note = (f"povijest dostupna od {data_from} — 52-tjedni raspon pokriva "
                    f"kraće razdoblje")
        out.append({
            "class_ticker": c["ticker"],
            "last": {"date": str(last_d), "close_eur": _f(last_px)},
            "prev_close_eur": _f(prev[1]) if prev else None,
            "change_pct": _f(change_pct),
            "high_52w_eur": _f(hi52), "low_52w_eur": _f(lo52),
            "avg_turnover_20d_eur": _f(avg_tov),
            "data_from": str(data_from) if data_from else None,
            "note": note,
        })
    return {
        "as_of": str(as_of), "classes": out,
        "note": ("dani bez trgovanja nisu u seriji (nema zapisa); promjena je vs "
                 "prethodni TRGOVANI dan, ne kalendarski"),
    }


def _dividend_calendar(cur, company_id: int, as_of) -> dict:
    """Jedinstveni pogled: isplaćene (povijest) + izglasane/najavljene nadolazeće.
    Statusi iz PODATAKA (datumi iz EHO objava) — datumi koji fale ostaju null."""
    cur.execute(
        """SELECT class_ticker, fiscal_year, amount_eur, div_type, ex_date,
                  record_date, payment_date, source_url
           FROM dividends WHERE company_id=%s
           ORDER BY COALESCE(ex_date, payment_date) DESC NULLS LAST, class_ticker""",
        (company_id,))
    events, n_upcoming = [], 0
    for ct, fy, amt, dtyp, ex, rec, pay, src in cur.fetchall():
        if pay is not None and pay <= as_of:
            status, label = "paid", "isplaćena"
        elif dtyp and "rijedlog" in dtyp:
            status, label = "proposed", "prijedlog (nije izglasana)"
        else:
            status, label = "upcoming", "izglasana — nadolazeća"
        if status != "paid":
            n_upcoming += 1
        events.append({
            "class_ticker": ct, "fiscal_year": fy, "amount_eur": _f(amt),
            "div_type": dtyp, "ex_date": str(ex) if ex else None,
            "record_date": str(rec) if rec else None,
            "payment_date": str(pay) if pay else None,
            "status": status, "status_hr": label, "source_url": src,
        })
    return {
        "as_of": str(as_of), "events": events, "upcoming_count": n_upcoming,
        "note": ("izvor: EHO objave izdavatelja (odluke GS / obavijesti o dividendi); "
                 "fiscal_year = godina dobiti iz koje se isplaćuje (ex-godina − 1); "
                 "prijedlozi su označeni i NISU izglasane isplate"),
    }


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


def _market_only_json(cur, company_id: int, ticker: str, name, sector, is_group,
                      comp_isin) -> dict:
    """Firma NIJE live (izvješća u obradi / needs_review): objavljujemo SAMO
    javne tržišne podatke (cijene, dividende, likvidnost). Financije i
    valuacija se NE objavljuju dok ne prođu validate/promotion gate."""
    from datetime import date
    today = date.today()
    classes = _share_classes(cur, company_id)
    # dps je dividendna činjenica (EHO objava s citatom) — javna, smije van
    cur.execute("""SELECT value_eur FROM financials
                   WHERE company_id=%s AND item='dps'
                   ORDER BY fiscal_year DESC LIMIT 1""", (company_id,))
    r = cur.fetchone()
    dps = _f(r[0]) if r else None
    per_class = [{
        "class_ticker": c["ticker"],
        "price": c["last_price"]["close_eur"] if c["last_price"] else None,
        "pe": None, "pb": None,
        "div_yield": (dps / c["last_price"]["close_eur"]
                      if dps and c["last_price"] and c["last_price"]["close_eur"] else None),
        "basis": "samo tržišni podaci — P/E i P/B čekaju validirana izvješća",
    } for c in classes]
    mcap = sum((c["last_price"]["close_eur"] or 0) * (c["shares_ex_treasury"] or 0)
               for c in classes if c["last_price"] and c["shares_ex_treasury"]) or None
    return {
        "ticker": ticker, "name": name, "sector": sector, "is_group": is_group,
        "isin": comp_isin, "fiscal_year": None, "audited": None,
        "generated_at": str(today),
        "data_status": "market_only",
        "data_note": ("financijska izvješća su u obradi (needs_review) — "
                      "prikazani su samo javni tržišni podaci; financije i "
                      "vrednovanje se objavljuju tek nakon validacije"),
        "financials_3y": None, "balance": None, "segments": None,
        "ownership": None, "bank_kpi": None,
        "share_classes": classes,
        "metrics": {"eps": None, "bvps": None, "roe": None, "dps": dps,
                    "shares_ex_treasury": None, "market_cap_eur": _f(mcap),
                    "ebitda_eur": None, "per_class": per_class,
                    "basis_note": "trž.kap = Σ zadnji close klase × uvrštene dionice"},
        "fundamentals": [],
        "price_summary": _price_summary(cur, classes, today),
        "dividend_calendar": _dividend_calendar(cur, company_id, today),
        "prices": _price_history(cur, company_id),
        "liquidity": _liquidity(cur, classes, today),
        "news": _news(cur, company_id),
        "valuation": None,
        "mar_note": ("Informativni prikaz javnih tržišnih podataka; nije "
                     "investicijski savjet ni preporuka."),
    }


def build_stock_json(conn, ticker: str) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT id, name, sector, is_group, isin, is_live FROM companies "
                "WHERE ticker = %s", (ticker,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"nepoznat ticker: {ticker}")
    company_id, name, sector, is_group, comp_isin, is_live = row
    if not is_live:
        return _market_only_json(cur, company_id, ticker, name, sector, is_group,
                                 comp_isin)
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
        # M8: sidrena fer-zona — arhetip, uloge metoda, raspon svih metoda
        "archetype": rec.get("archetype"),
        "anchor_methods": rec.get("anchor_methods"),
        "method_roles": {k: {"role": v["role"], "note": v["note"],
                             "vs_zone_pct": _f(v["vs_zone_pct"])}
                         for k, v in (rec.get("method_roles") or {}).items()},
        "zone_note": rec.get("zone_note"),
        "all_methods_low": _f(rec.get("all_methods_low")),
        "all_methods_high": _f(rec.get("all_methods_high")),
        "dispersion_all": _f(rec.get("dispersion_all")),
        "method_bases": {k: _f(v) for k, v in (rec.get("method_bases") or {}).items()},
        # M12: QA konvergencije ulaza + lanac zaključivanja do sidra
        "qa_flags": rec.get("qa_flags") or [],
        "vs_market_pct": _f(rec.get("vs_market_pct")),
        "anchor_inconsistency": rec.get("anchor_inconsistency") or [],
        "reasoning": rec.get("reasoning"),
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
            "sotp_fair": a.get("sotp_fair"),
            "sotp_market": a.get("sotp_market"),
            "market_vs_fair_pct": a.get("market_vs_fair_pct"),
            "market_vs_fair_note": a.get("market_vs_fair_note"),
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
        "data_status": "full",
        "financials_3y": _financials_3y(cur, company_id, shares,
                                        BANK_THREE_Y_ROWS if is_bank else THREE_Y_ROWS),
        "trend": _trend(cur, company_id, sector),
        "news": _news(cur, company_id),
        "business_profile": _business_profile(cur, company_id),
        "risks": _risks(sector, is_group, sotp_breakdown,
                        _liquidity(cur, classes, today),
                        _ownership(cur, company_id, ticker),
                        assumption_flags,
                        _bank_kpi(cur, company_id, latest_fy) if is_bank else None,
                        reconciliation),
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
        "price_summary": _price_summary(cur, classes, today),
        "dividend_calendar": _dividend_calendar(cur, company_id, today),
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
