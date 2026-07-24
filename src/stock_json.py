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
import re
import sys
import unicodedata
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


def _vfc(cur, company_id: int, fiscal_year: int, item: str, allow_q4: bool = False):
    """Jedna stavka iz v_financials_current za PUNU godinu (konsolidirano).
    Godišnji (revidirani) red ima prednost; uz allow_q4=True, ako godišnjeg
    nema, uzima se q4 kumulativ (TFI kraj godine — nerevidirano) kako puna
    godina koja postoji samo kao kvartalni kumulativ ne bi bila nevidljiva
    (isti izvor koji KPI kartica koristi za TTM)."""
    cur.execute(
        """SELECT value_eur FROM v_financials_current
           WHERE company_id=%s AND fiscal_year=%s AND item=%s
             AND basis='consolidated' AND period_type = ANY(%s)
           ORDER BY (period_type='annual') DESC LIMIT 1""",
        (company_id, fiscal_year, item,
         ["annual", "q4"] if allow_q4 else ["annual"]),
    )
    r = cur.fetchone()
    return _f(r[0]) if r else None


def _full_years(cur, company_id: int, limit: int = 3):
    """Fiskalne godine s PUNIM podacima (uzlazno) + je li godina nerevidirana.
    Godišnji (annual) red = revidirano; ako ga nema, q4 kumulativ (TFI kraj
    godine) drži godinu vidljivom, ali označenu kao nerevidiranu. Vraća
    [(godina:int, preliminary:bool)]."""
    cur.execute(
        """SELECT fiscal_year, bool_or(period_type='annual') AS has_annual
           FROM v_financials_current
           WHERE company_id=%s AND basis='consolidated'
             AND period_type IN ('annual','q4')
             AND statement IN ('income','balance','cashflow') AND item <> 'dps'
           GROUP BY fiscal_year
           ORDER BY fiscal_year DESC LIMIT %s""", (company_id, limit))
    return sorted((fy, not has_annual) for fy, has_annual in cur.fetchall())


def _financials_3y(cur, company_id: int, shares: float | None,
                   rows_spec=None) -> dict:
    """DIO 1: zadnje 3 fiskalne godine + YoY (FY0 vs FY-1) + CAGR (FY-2 -> FY0).
    Puna godina koja postoji samo kao q4 kumulativ (TFI kraj godine) ulazi
    NEREVIDIRANA i označena — inače bi zadnja godina 'nestala' iz tablice
    dok se KPI kartica već oslanja na nju (TTM)."""
    fy_list = _full_years(cur, company_id, limit=3)
    years = [fy for fy, _ in fy_list]
    prelim_years = [fy for fy, prelim in fy_list if prelim]
    rows = []
    for item, label in (rows_spec or THREE_Y_ROWS):
        vals = {}
        for y in years:
            if item == "eps":
                ni = _vfc(cur, company_id, y, "net_income_parent", allow_q4=True)
                # EPS uz KANONSKI (današnji) broj dionica — napomena u note sekcije
                vals[str(y)] = (ni / shares) if (ni is not None and shares) else None
            else:
                vals[str(y)] = _vfc(cur, company_id, y, item, allow_q4=True)
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
        # NEREVIDIRANE godine (samo q4 kumulativ) — frontend prikazuje ogradu
        # kroz i18n ključ (bez dinamičkog HR teksta u podacima)
        "preliminary_years": prelim_years,
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
    fy_list = _full_years(cur, company_id, limit=3)
    years = [fy for fy, _ in fy_list]
    prelim = {fy for fy, p in fy_list if p}
    if not years:
        return None
    series = []
    for y in years:
        rev = _vfc(cur, company_id, y, rev_item, allow_q4=True)
        ebd = None if is_fin else _vfc(cur, company_id, y, "ebitda", allow_q4=True)
        series.append({
            "year": y, "revenue": _f(rev), "ebitda": _f(ebd),
            "ebitda_margin": (_f(ebd / rev) if (ebd is not None and rev) else None),
            "preliminary": y in prelim,
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
        # NEREVIDIRANE godine (samo q4 kumulativ) — ograda ide kroz i18n ključ
        "preliminary_years": sorted(prelim),
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


def _global_peers(sector: str | None) -> dict | None:
    """Z4: kurirani globalni peer set sektora (config/global_peers.json).
    KONTEKST, ne sidro (v2 §8) — multipli se prikazuju samo iz ručnog
    snapshotta s datumom; bez snapshotta ide lista peera + razlog."""
    import os
    try:
        with open(os.path.join("config", "global_peers.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:  # noqa: BLE001
        return None
    sec = (cfg.get("sectors") or {}).get(sector)
    if not sec:
        return None
    has_metrics = any(p.get("metrics") for p in sec["peers"])
    return {
        "as_of": cfg.get("as_of"),
        "metrics_set": sec["metrics_set"],
        "peers": sec["peers"],
        "has_metrics": has_metrics,
        "levels_hr": {"hr_region": "HR/regija", "eu": "EU", "global": "globalno"},
        "note": ("globalni peerovi su KONTEKST — ne ulaze u sidro fer-zone "
                 "(v2 §8); cross-market razlike (rast, likvidnost, veličina, "
                 "trošak kapitala tržišta) objašnjavaju dio raskoraka u "
                 "multiplima"),
        "no_metrics_reason": (None if has_metrics else
                              "multipli globalnih peera zahtijevaju ručni "
                              "snapshot s izvorom i datumom — vanjski tržišni "
                              "podaci nisu dostupni automatskim putem; do unosa "
                              "snapshotta prikazuje se samo kurirana lista"),
    }


# Z3.2: generički jednorečenični opisi po sektoru — fallback kad profil iz
# izvješća još nije ekstrahiran; JASNO označeni kao generički, ne tvrde ništa
# specifično o firmi (samo sektorska činjenica iz registra/NACE)
GENERIC_ACTIVITY = {
    "bank": "Kreditna institucija sa sjedištem u Republici Hrvatskoj (bankovni sektor).",
    "insurance": "Društvo za osiguranje sa sjedištem u Republici Hrvatskoj.",
    "fund": "Zatvoreni investicijski fond / investicijsko društvo uvršteno na Zagrebačkoj burzi.",
    "tourism": "Društvo u djelatnosti turizma i ugostiteljstva (hoteli/marine/odmarališta).",
    "consumer": "Društvo u potrošačkom sektoru (proizvodnja/distribucija robe široke potrošnje).",
    "industrial": "Industrijsko društvo (proizvodnja i/ili industrijske usluge).",
    "holding": "Društvo koje upravlja grupom povezanih društava (holding/uprava grupe).",
    "telecom": "Telekomunikacijsko društvo.",
    "technology": "Društvo u sektoru informacijskih tehnologija.",
    "energy": "Društvo u energetskom sektoru (energetska infrastruktura/usluge).",
    "shipping": "Brodarsko / pomorsko-prijevozničko društvo.",
    "transport": "Prijevozničko društvo.",
    "construction": "Društvo u graditeljstvu i inženjeringu.",
    "real_estate": "Društvo za poslovanje nekretninama.",
    "aquaculture": "Društvo u marikulturi/akvakulturi.",
    "other": "Uvršteno dioničko društvo (djelatnost prema sudskom/NACE registru).",
}


def _business_profile(cur, company_id: int, sector: str | None = None) -> dict | None:
    """M9: profil poslovanja — činjenice iz izvješća s citatima; epiteti
    izdavatelja ODVOJENO u issuer_claims. Z3.2: bez ekstrahiranog profila
    vraća GENERIČKI sektorski opis (označen), ne null."""
    cur.execute(
        """SELECT fiscal_year, activity, activity_source_page, segments,
                  markets, export_share, issuer_claims, source, bp_en
           FROM business_profiles WHERE company_id=%s""", (company_id,))
    r = cur.fetchone()
    if not r:
        generic = GENERIC_ACTIVITY.get(sector or "other", GENERIC_ACTIVITY["other"])
        return {
            "fiscal_year": None, "activity": generic,
            "activity_source_page": None, "segments": [], "markets": [],
            "export_share": None, "issuer_claims": [],
            "generic": True,
            "source": "generički opis iz sektorskog registra (NACE)",
            "note": ("GENERIČKI OPIS — profil iz godišnjeg izvješća još nije "
                     "ekstrahiran; opis navodi samo sektorsku činjenicu iz "
                     "registra i ne tvrdi ništa specifično o firmi"),
        }
    segments = r[3] or []
    markets = r[4] or []
    claims = r[6] or []
    out = {
        "fiscal_year": r[0], "activity": r[1], "activity_source_page": r[2],
        "segments": segments, "markets": markets,
        "export_share": r[5], "issuer_claims": claims, "source": r[7],
        "note": ("samo činjenice iz izvješća s citatima; kvalitativne tvrdnje "
                 "('vodeći' i sl.) su TVRDNJE IZDAVATELJA, označene i citirane "
                 "— platforma ih ne generira niti potvrđuje"),
    }
    # M40: EN prijevod (bp_en) — overlay po indeksu; source_page se NE prevodi,
    # nego dijeli s HR. Frontend čita *_en polja na /en stranicama.
    en = r[8]
    if en:
        out["activity_en"] = en.get("activity")
        en_seg = en.get("segments") or []
        for i, s in enumerate(out["segments"]):
            if i < len(en_seg):
                s["name_en"] = en_seg[i].get("name")
                s["description_en"] = en_seg[i].get("description")
        en_mkt = en.get("markets") or []
        for i, m in enumerate(out["markets"]):
            if i < len(en_mkt):
                m["market_en"] = en_mkt[i]
        en_claims = en.get("claims") or []
        for i, c in enumerate(out["issuer_claims"]):
            if i < len(en_claims):
                c["claim_en"] = en_claims[i]
        if out.get("export_share") and en.get("export_basis"):
            out["export_share"]["basis_en"] = en["export_basis"]
    return out


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


def _norm_holder(name: str) -> str:
    """Normalizacija za sparivanje imena preko izvora (ZSE uppercase vs
    izvješće mixed-case; dijakritici/ligature iz PDF-a; kratice fondova).
    Prikaz UVIJEK ostaje točno kako je objavljeno — ovo služi samo za
    usporedbu snapshota."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"[.,*()\"']", " ", s)
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = []
    for t in s.split(" "):
        if t == "omf":
            toks += ["obvezni", "mirovinski", "fond"]
        elif t == "dmf":
            toks += ["dobrovoljni", "mirovinski", "fond"]
        elif t == "co":  # 'PBZ CO OMF' = PBZ Croatia Osiguranje OMF
            toks += ["croatia", "osiguranje"]
        elif re.fullmatch(r"kategorij\w*", t):
            toks.append("kategorije")
        elif t in ("-", "–"):
            continue
        else:
            toks.append(t)
    return " ".join(toks)


def _client_key(norm: str) -> str:
    """Za skrbnički zapis 'BANKA/KLIJENT' vrati klijentski dio — godišnja
    izvješća često imenuju krajnjeg imatelja izravno, ZSE preko skrbnika."""
    if "/" in norm:
        tail = norm.rsplit("/", 1)[1].strip()
        if len(tail) >= 4:
            return tail
    return norm


def _match_snapshots(cur_rows: list[dict], prev_rows: list[dict]) -> None:
    """1:1 sparivanje redova dva snapshota: (1) točno normalizirano ime,
    (2) klijentski dio skrbničkog zapisa, (3) podskup tokena (npr.
    'REPUBLIKA HRVATSKA' unutar 'CERP - Republika Hrvatska'). Nespareno =
    ušao/izašao. Upisuje prev_pct/change_pp/prev_name/entered u cur_rows."""
    for r in cur_rows:
        r["prev_pct"] = r["change_pp"] = r["prev_name"] = None
        r["entered"] = True
    free_prev = {id(p): p for p in prev_rows}

    def _pair(r, p):
        r["prev_pct"] = p["pct"]
        r["prev_name"] = p["name"] if _norm_holder(p["name"]) != _norm_holder(r["name"]) else None
        if r["pct"] is not None and p["pct"] is not None:
            r["change_pp"] = round(r["pct"] - p["pct"], 2)
        r["entered"] = False
        free_prev.pop(id(p), None)

    for match_fn in (
        lambda r, p: _norm_holder(r["name"]) == _norm_holder(p["name"]),
        lambda r, p: _client_key(_norm_holder(r["name"])) == _client_key(_norm_holder(p["name"])),
        lambda r, p: (lambda a, b: (set(a.split()) <= set(b.split())
                                    or set(b.split()) <= set(a.split()))
                      and min(len(a.split()), len(b.split())) >= 2)(
            _client_key(_norm_holder(r["name"])), _client_key(_norm_holder(p["name"]))),
    ):
        for r in cur_rows:
            if not r["entered"]:
                continue
            for p in list(free_prev.values()):
                if match_fn(r, p):
                    _pair(r, p)
                    break
    for p in prev_rows:
        p["_left"] = id(p) in free_prev


def _top10_block(cur, company_id: int) -> dict | None:
    """M23: top 10 dioničara iz tablice shareholders + PROMJENE između zadnja
    dva snapshota. Jedan snapshot -> stanje s datumom, BEZ izmišljenih
    promjena. Imena točno kako su objavljena (SKDD/izvješće)."""
    cur.execute(
        """SELECT DISTINCT snapshot_date, source FROM shareholders
           WHERE company_id = %s ORDER BY snapshot_date DESC""",
        (company_id,))
    snaps = cur.fetchall()
    if not snaps:
        return None

    def _rows(snap_date, source):
        cur.execute(
            """SELECT rank, holder_name, shares, pct, is_custody, source_detail
               FROM shareholders
               WHERE company_id = %s AND snapshot_date = %s AND source = %s
               ORDER BY rank""",
            (company_id, snap_date, source))
        return [{"rank": rk, "name": nm, "shares": _f(sh), "pct": _f(p),
                 "is_custody": cu, "source_detail": det}
                for rk, nm, sh, p, cu, det in cur.fetchall()]

    cur_date, cur_src = snaps[0]
    rows = _rows(cur_date, cur_src)
    prev = None
    for d, s in snaps[1:]:
        if d < cur_date:
            prev = (d, s)
            break

    src_label = {"zse_skdd": "ZSE stranica papira (izvor SKDD)",
                 "annual_report": "godišnje izvješće"}
    entered = left = None
    prev_date = prev_src = None
    if prev:
        prev_date, prev_src = prev
        prev_rows = _rows(prev_date, prev_src)
        _match_snapshots(rows, prev_rows)
        entered = [r["name"] for r in rows if r.get("entered")]
        left = [p["name"] for p in prev_rows if p.get("_left")]
    else:
        for r in rows:
            r["prev_pct"] = r["change_pp"] = r["prev_name"] = None
            r["entered"] = False

    # free float iz top 10: samo kad je lista puna (10 redova) — inače bi
    # "100 − suma" precijenio free float
    ff_top10 = None
    if len(rows) >= 10 and all(r["pct"] is not None for r in rows):
        ff_top10 = round(max(0.0, 100.0 - sum(r["pct"] for r in rows)), 2)

    return {
        "snapshot_date": str(cur_date),
        "source": cur_src,
        "source_label": src_label.get(cur_src, cur_src),
        "rows": rows,
        "prev_snapshot_date": str(prev_date) if prev_date else None,
        "prev_source": prev_src,
        "prev_source_label": src_label.get(prev_src, prev_src) if prev_src else None,
        "entered": entered, "left": left,
        "free_float_from_top10_pct": ff_top10,
        "note": ("promjene = usporedba zadnja dva snapshota; udjeli u p.p."
                 if prev else
                 "samo jedan snapshot u bazi — prikazuje se stanje s datumom, "
                 "bez promjena (povijest se gradi mjesečnim snapshotima)"),
        "custody_note": ("skrbnički/zbirni računi (oznaka) nisu stvarni "
                         "krajnji vlasnici — dionice drže za klijente"),
    }


def _ownership(cur, company_id: int, ticker: str) -> dict:
    """DIO 5: top 10 dioničara (M23) + obrnuti holdings graf + free float."""
    top10 = _top10_block(cur, company_id)
    cur.execute(
        """SELECT p.name, p.ticker, h.ownership_pct, h.source_page
           FROM holdings h JOIN companies p ON p.id = h.parent_company_id
           WHERE h.held_company_id = %s ORDER BY h.ownership_pct DESC""",
        (company_id,),
    )
    holders = [{"name": n, "ticker": t, "pct": _f(pct), "source": src}
               for n, t, pct, src in cur.fetchall()]
    ff_t10 = top10["free_float_from_top10_pct"] if top10 else None
    if ff_t10 is not None:
        known = round(100.0 - ff_t10, 2) / 100.0
        ff = ff_t10 / 100.0
        note = ("free float ≈ 100% − Σ top 10 dioničara "
                f"(snapshot {top10['snapshot_date']}, {top10['source_label']}); "
                "aproksimacija — imatelji izvan top 10 nisu obuhvaćeni")
        liq_link = (f"manjinski free float (~{ff * 100:.1f}%) znači plitku "
                    "knjigu naloga — vidi oznaku likvidnosti uz cijenu"
                    if ff < 0.40 else None)
    elif holders:
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
    return {"top10": top10, "holders": holders, "known_pct": known,
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


def _last_dividend(cur, company_id: int):
    """Z2: zadnja STVARNA dividenda (bez prijedloga) + fiskalna godina —
    DIV. PRINOS se računa iz zadnje izglasane isplate, ne '—'."""
    cur.execute(
        """SELECT amount_eur,
                  COALESCE(fiscal_year,
                           EXTRACT(YEAR FROM COALESCE(ex_date, payment_date))::int - 1)
           FROM dividends
           WHERE company_id=%s AND div_type NOT ILIKE '%%rijedlog%%'
             AND amount_eur IS NOT NULL
           ORDER BY 2 DESC NULLS LAST,
                    COALESCE(ex_date, payment_date) DESC NULLS LAST
           LIMIT 1""", (company_id,))
    r = cur.fetchone()
    if not r:
        return None, None
    return _f(r[0]), (int(r[1]) if r[1] is not None else None)


def _dividend_calendar(cur, company_id: int, as_of) -> dict:
    """Jedinstveni pogled: isplaćene (povijest) + izglasane/najavljene nadolazeće.
    Statusi iz PODATAKA (datumi iz EHO objava) — datumi koji fale ostaju null.
    Z2: + povijest po fiskalnim godinama i metrike (kontinuitet, rast, prosjek)."""
    cur.execute(
        """SELECT class_ticker, fiscal_year, amount_eur, div_type, ex_date,
                  record_date, payment_date, source_url,
                  payout_type, payout_ratio, classified_reason
           FROM dividends WHERE company_id=%s
           ORDER BY COALESCE(fiscal_year,
                    EXTRACT(YEAR FROM COALESCE(ex_date, payment_date))::int - 1)
                    DESC NULLS LAST, class_ticker""",
        (company_id,))
    events, n_upcoming = [], 0
    for ct, fy, amt, dtyp, ex, rec, pay, src, ptype, pratio, preason in cur.fetchall():
        derived = bool(dtyp and "izvedeno" in dtyp)
        if derived:
            status, label = "paid", "isplaćena (izvedeno iz NT obrasca)"
        elif pay is not None and pay <= as_of:
            status, label = "paid", "isplaćena"
        elif (pay is None and ex is None and fy is not None
              and fy < as_of.year - 1):
            # M35.1: povijesni zapis bez datuma — nikad "nadolazeća"
            status, label = "paid", "isplaćena (povijesni zapis bez datuma)"
        elif dtyp and "rijedlog" in dtyp:
            status, label = "proposed", "prijedlog (nije izglasana)"
        else:
            status, label = "upcoming", "izglasana — nadolazeća"
        if status != "paid":
            n_upcoming += 1
        events.append({
            "class_ticker": ct,
            "fiscal_year": (fy if fy is not None
                            else (int(str(ex)[:4]) - 1 if ex else None)),
            "amount_eur": _f(amt),
            "div_type": dtyp, "ex_date": str(ex) if ex else None,
            # v3 DIV: tip isplate + % dobiti pripadne fiskalne godine
            "payout_type": ptype, "payout_ratio": _f(pratio),
            "classified_reason": preason,
            "record_date": str(rec) if rec else None,
            "payment_date": str(pay) if pay else None,
            "status": status, "status_hr": label, "source_url": src,
        })
    # Z2: povijest po fiskalnoj godini (bez prijedloga; jedan iznos po FY —
    # primarna/prva klasa) + metrike
    by_fy = {}
    for e in events:
        if e["status"] == "proposed" or e["fiscal_year"] is None or not e["amount_eur"]:
            continue
        by_fy.setdefault(e["fiscal_year"], e["amount_eur"])
    history = None
    if by_fy:
        years = sorted(by_fy, reverse=True)
        last5 = years[:5]
        window_years = set(range(max(years) - 4, max(years) + 1))
        cont = len([y for y in years if y in window_years])
        cagr = None
        if len(years) >= 3 and by_fy[years[-1]] > 0 and by_fy[years[0]] > 0:
            span = years[0] - years[-1]
            if span > 0:
                cagr = (by_fy[years[0]] / by_fy[years[-1]]) ** (1 / span) - 1
        history = {
            "per_year": [{"fiscal_year": y, "amount_eur": by_fy[y]} for y in years],
            "continuity": {"paid_years": cont, "window": 5,
                           "coverage_from": min(years),
                           "note": (f"isplata u {cont} od zadnjih 5 fiskalnih godina; "
                                    f"podaci dostupni od FY{min(years)}")},
            "avg_amount_5y": round(sum(by_fy[y] for y in last5) / len(last5), 4),
            "growth_cagr": (_f(round(cagr, 4)) if cagr is not None else None),
            "growth_note": (f"CAGR FY{years[-1]}->FY{years[0]}" if cagr is not None
                            else "rast n/p (manje od 3 godine podataka)"),
        }
    return {
        "as_of": str(as_of), "events": events, "upcoming_count": n_upcoming,
        "history": history,
        "note": ("izvor: EHO objave izdavatelja (odluke GS / obavijesti o dividendi) "
                 "i NT obrasci (izvedeni povijesni iznosi — ukupno isplaćeno / broj "
                 "dionica, označeno); fiscal_year = godina dobiti iz koje se "
                 "isplaćuje (godina isplate − 1); prijedlozi su označeni i NISU "
                 "izglasane isplate"),
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
    dps_fy_label = None
    if dps is None:  # Z2: zadnja izglasana/isplaćena iz dividends tablice
        dps, dps_fy = _last_dividend(cur, company_id)
        if dps is not None and dps_fy is not None:
            dps_fy_label = f"zadnja isplata FY{dps_fy}"
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
        "business_profile": _business_profile(cur, company_id, sector),
        "global_peers": _global_peers(sector),
        "share_classes": classes,
        "metrics": {"eps": None, "bvps": None, "roe": None, "dps": dps,
                    "dps_label": dps_fy_label,
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


ARCHETYPE_STORY = {
    # v3 (M17): template po arhetipu — popunjava se STVARNIM podacima procjene
    "holding_operating": (
        "{name} je integrirani industrijski holding: vrijednost čine udjeli u "
        "{parts} plus vlastiti biznis, pa je sidro zbroj dijelova (SOTP) — bez "
        "holding popusta, jer matica kontrolira i konsolidira kćeri iste "
        "djelatnosti. Konsolidirani DCF i peer usporedba služe kao kontrola."),
    "holding_passive": (
        "{name} je diversificirani holding: vrijednost čine udjeli u {parts}, "
        "pa je sidro zbroj dijelova (SOTP). Popust na zbroj dijelova se MJERI "
        "iz povijesti vlastite cijene prema vrijednosti dijelova, ne "
        "pretpostavlja."),
    "bank": (
        "{name} je banka: vrijednost banke određuje koliko zarađuje na "
        "vlastitom kapitalu u odnosu na zahtijevani prinos, pa je sidro "
        "opravdani P/B / rezidualni dohodak. Dividendni model i peer "
        "usporedba su potvrda."),
    "insurance": (
        "{name} je osiguratelj: kao i kod banke, vrijednost nosi povrat na "
        "kapital -> sidro je opravdani P/B / rezidualni dohodak."),
    "tourism": (
        "{name} je turistička firma: sektor se uspoređuje po EV/EBITDA "
        "(vrijednost poslovanja prema operativnoj zaradi, uz napomenu o "
        "najmovima), pa je sidro peer usporedba uz DCF kao drugu kotvu."),
    "cyclical": (
        "{name} je ciklična firma (niža profitabilnost kapitala ili poluga): "
        "zarada zna varirati kroz ciklus, pa je sidro {anchor_hr} — "
        "guidance-DCF kad uprava daje brojke, inače knjiga kapitala; peer "
        "usporedba je kontrola, a EV/EBITDA se izbjegava jer laska "
        "zaduženima."),
    "industrial_forward": (
        "{name} ima kvantificirani signal budućeg posla ({drivers}), pa je "
        "sidro DCF s rastom izvedenim iz tog signala. Peer usporedba je "
        "kontrola."),
    "industrial_noforward": (
        "{name} nema kvantificirani forward signal (backlog/guidance) u "
        "zadnjem izvješću, pa je sidro peer usporedba (što tržište plaća za "
        "slične firme); opravdani P/B je potvrda."),
}

ANCHOR_HR = {
    "sotp_nav": "zbroj dijelova (SOTP)", "dcf_fcf": "DCF (novčani tokovi)",
    "comps": "peer usporedba", "justified_pb_roe": "opravdani P/B",
    "residual_income": "rezidualni dohodak", "ddm_gordon": "dividendni model",
}


def _methodology_note(cur, company_id, name, rec, params, sotp, flags, ctxgh):
    """DIO 2 (M17): 'Kako je nastala ova procjena' — generirano iz ISTIH
    podataka koji su dali valuaciju; bez ručno pisanog teksta po firmi."""
    from .params_calibrated import ERP, RF
    from .valuation_methods import _plain_risk
    arche = rec.get("archetype")
    prim = (rec.get("anchor_methods") or [None])[0]
    parts = ", ".join(x["item"] for x in ((sotp or {}).get("identity") or [])
                      if x.get("basis") in ("our_estimate", "market_fallback"))
    story = ARCHETYPE_STORY.get(arche, "Sidro je {anchor_hr}.").format(
        name=name, parts=parts or "uvrštenim i neuvrštenim dijelovima",
        anchor_hr=ANCHOR_HR.get(prim, prim or "n/p"),
        drivers=(ctxgh or {}).get("drivers", "backlog/guidance"))
    # parametri OVE procjene
    pars = []
    beta = params.get("beta")
    pars.append({
        "k": "Trošak kapitala r", "v": f"{params['r'] * 100:.2f}%".replace(".", ","),
        "why": (f"CAPM: nerizična stopa {RF:.2%} (HR 10g obveznica) + beta "
                f"{beta if beta is not None else 'n/p'} × premija rizika {ERP:.2%} "
                f"(Damodaran, HR). Beta je "
                + ("izmjerena iz burzovne serije ove dionice."
                   if params.get("beta_calibrated") else
                   "pretpostavka 1,0 (serija prekratka/nelikvidna).")
                + " Ponderirani country-risk za izvoznike je planiran, još nije aktivan."),
    })
    pars.append({
        "k": "Dugoročni rast g",
        "v": (f"{params['g'] * 100:.1f}% / {params.get('g_terminal', 0) * 100:.1f}%"
              ).replace(".", ","),
        "why": ("kapitalne metode 2,5% (konzervativno), DCF terminal 4,0% "
                "(nominalni BDP proxy: realni rast + inflacija)"),
    })
    if ctxgh and ctxgh.get("g1") is not None:
        # v3.1 DIO 2: kompozitni g1 — raspis ide iz growth_hint.source
        _origin = (ctxgh.get("signals") or {}).get("origin") or "kompozit"
        pars.append({"k": "Rast eksplicitne faze g1 (kompozit)",
                     "v": f"{ctxgh['g1'] * 100:.1f}%".replace(".", ","),
                     "why": (f"medijan tri signala iz objavljenih brojki "
                             f"(serija / održivi rast / terminalno sidro); "
                             f"presudio je signal '{_origin}'")})
    if params.get("peers_calibrated"):
        pars.append({"k": "Peer multipli",
                     "v": f"P/E {params['peer_pe']}",
                     "why": ("medijan iz baze (ZSE peeri istog sektora)"
                             + ("; USKI SKUP (n=2) — snižena pouzdanost"
                                if params.get("peers_narrow") else ""))})
    else:
        pars.append({"k": "Peer multipli", "v": "placeholder",
                     "why": ("na ZSE nema dovoljno usporedivih firmi ovog "
                             "sektora — metoda peer usporedbe nosi NISKU "
                             "pouzdanost i ne sidri zonu")})
    if sotp and sotp.get("holding_discount_range"):
        dr = sotp["holding_discount_range"]
        pars.append({"k": "Holding diskont",
                     "v": f"{dr[0] * 100:.0f}–{dr[1] * 100:.0f}%",
                     "why": sotp.get("holding_discount_reason", "")[:200]})
    # ograničenja: QA flagovi laički + pretpostavke
    lims = [_plain_risk(f) for f in (rec.get("qa_flags") or [])]
    lims += [f"{f['label']} — {f['why']}" for f in flags
             if f.get("status") == "pretpostavka"]
    # povijest promjena
    cur.execute("""SELECT changed_on, old_low, old_high, new_low, new_high,
                          reason, kind FROM valuation_changelog
                   WHERE company_id=%s ORDER BY changed_on DESC, id DESC LIMIT 12""",
                (company_id,))
    changelog = [{"date": str(r[0]), "old_low": _f(r[1]), "old_high": _f(r[2]),
                  "new_low": _f(r[3]), "new_high": _f(r[4]),
                  "reason": r[5], "kind": r[6]} for r in cur.fetchall()]
    return {
        "story": story,
        "parameters": pars,
        "limitations": lims,
        "changelog": changelog,
        "notes": [
            "Rast čitamo iz forward signala zadnjeg izvješća (backlog, guidance) "
            "— povijesni prosjek je samo kontekst.",
            "Konzervativnost se primjenjuje JEDNOM (npr. popust se ne slaže na "
            "već konzervativne procjene).",
            "Svaka brojka nosi izvor (dokument + stranica) — vidljivo uz metode "
            "i pretpostavke.",
            "Analize generira automatizirani sustav uz ljudski nadzor.",
        ],
        "link": "/metodologija",
        "mar": ("Informativna analiza, ne investicijski savjet ni preporuka — "
                "zaključak je čitateljev."),
    }


def _class_zones_safe(conn, company_id, rec):
    """v3 S: po-klasne fer-zone (None za jednu klasu/bez zone) — izolirano."""
    try:
        from .class_ratio import class_zones
        return class_zones(conn, company_id,
                           rec.get("zone_low"), rec.get("zone_high"))
    except Exception:  # noqa: BLE001 — raspodjela ne smije srušiti export
        conn.rollback()
        return None


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

    # v2 §7: vrednuje se FIRMA (fer po dionici je klasno-agnostična); stranica
    # OBJAŠNJAVA prava po klasi i zašto se tržišne cijene klasa razlikuju
    share_class_explainer = None
    if len(classes) > 1:
        rows = []
        for c0 in classes:
            typ = c0.get("class_type")
            rows.append({
                "ticker": c0["ticker"],
                "type": "redovna" if typ == "ordinary" else "povlaštena",
                "rights": ("pravo glasa na glavnoj skupštini; dividenda nakon "
                           "povlaštenih" if typ == "ordinary" else
                           "bez prava glasa (u pravilu); prioritetna dividenda — "
                           "uvjeti u statutu/odluci o izdanju"),
            })
        share_class_explainer = {
            "rows": rows,
            "note": ("Fer vrijednost po dionici je KLASNO-AGNOSTIČNA (firma / sve "
                     "dionice ex-trezor). Tržišne cijene klasa se ipak razlikuju: "
                     "glasačka premija redovne, razlika u likvidnosti i članstvo u "
                     "indeksu. Ta premija je tržišna struktura — prikazuje se i "
                     "objašnjava, ali se NE ugrađuje u fer (v2 §7)."),
        }

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
        # doktrina v2: red rules (§8) + market-implied check (§6)
        "red_rules": rec.get("red_rules") or [],
        "market_implied": json.loads(json.dumps(rec.get("market_implied"), default=_f))
        if rec.get("market_implied") else None,
        # v3 FAZA A: triangulacija + sanity testovi
        "qualified_methods": rec.get("qualified_methods") or [],
        # v3 FAZA S: po-klasne zone iz ISTE vrijednosti firme (tržišni omjer)
        "class_zones": _class_zones_safe(conn, company_id, rec),
        "recalibrating": rec.get("recalibrating"),
        "dividend_sanity": json.loads(json.dumps(rec.get("dividend_sanity"),
                                                 default=_f))
        if rec.get("dividend_sanity") else None,
        "low_float_note": rec.get("low_float_note"),
    })

    shares = _f(ctx.shares_ex_treasury)
    ni_parent = _val(fund, "net_income_parent")
    eq_parent = _val(fund, "equity_parent") or _val(fund, "total_equity")
    dps = _val(fund, "dps")
    dps_fy_label = None
    if dps is None:
        # Z2: DIV. PRINOS iz zadnje izglasane/isplaćene dividende (dividends
        # tablica), s oznakom fiskalne godine — ne '—' dok povijest postoji
        dps, dps_fy = _last_dividend(cur, company_id)
        if dps is not None and dps_fy is not None:
            dps_fy_label = f"zadnja isplata FY{dps_fy}"
    eps = (ni_parent / shares) if (ni_parent and shares) else None
    bvps = (eq_parent / shares) if (eq_parent and shares) else None
    roe = (ni_parent / eq_parent) if (ni_parent and eq_parent) else None

    # Prezentacija: RASKORAK prinosne i knjigovodstvene vrijednosti — kad je
    # fer-zona bitno ispod (ili iznad) knjige, čitatelju se STAV objašnjava
    # generiranim tekstom iz brojki te firme (LPLH-tip nalaz; činjenice bez
    # preporuke, zaključak je čitateljev). Banke/osiguranja se preskaču —
    # njihovo sidro je ionako kapitalna metoda vezana uz knjigu.
    value_vs_book = None
    _zl, _zh = _f(rec.get("zone_low")), _f(rec.get("zone_high"))
    _roe_used = _f((getattr(ctx, "roe_hint", None) or {}).get("used")) or _f(roe)
    _r_used = _f(params.cost_of_equity)
    _px = _f(ctx.price)

    def _hr(x, dec=2):
        """hrvatski zapis broja: 1.234,56 (točka tisućice, zarez decimale)"""
        return (f"{x:,.{dec}f}".replace(",", "\x00")
                .replace(".", ",").replace("\x00", "."))
    if (sector not in ("bank", "insurance") and bvps and bvps > 0
            and _zl and _zh and _roe_used is not None and _r_used):
        _pb_mkt = (_px / bvps) if _px else None
        _nums = {"zone_low": _zl, "zone_high": _zh, "bvps": round(bvps, 2),
                 "roe": _roe_used, "r": _r_used, "price": _px,
                 "pb_market": (round(_pb_mkt, 2) if _pb_mkt else None)}
        if _zh < 0.75 * bvps and _roe_used < _r_used:
            value_vs_book = {
                "kind": "ispod_knjige", **_nums,
                "title": "Zašto je naša procjena ispod knjigovodstvene vrijednosti",
                "plain": (
                    f"Fer-zona ({_hr(_zl)}–{_hr(_zh)} €) niža je od knjigovodstvene "
                    f"vrijednosti ({_hr(bvps)} € po dionici). To je posljedica "
                    f"prinosnog pristupa, ne previda: firma na vlastitom kapitalu "
                    f"trenutačno zarađuje oko {_hr(_roe_used * 100, 1)} % godišnje, a ulagač za "
                    f"ovaj rizik traži {_hr(_r_used * 100, 1)} % — kapital koji trajno zarađuje "
                    f"manje od zahtijevanog prinosa u pravilu vrijedi manje od svoje "
                    f"knjige. Knjigovodstvena vrijednost pritom nije gotovina: "
                    f"većinom je to dugotrajna imovina po amortiziranom trošku, a "
                    f"punu knjigu bi opravdala tek prodaja imovine blizu tih "
                    f"vrijednosti — što procjena poslovanja koje nastavlja "
                    f"poslovati ne pretpostavlja."
                    + (f" Tržišna cijena ({_hr(_px)} €; P/B {_hr(_pb_mkt)}×) stoji "
                       f"između te dvije kotve — koliko vrijedi mogućnost prodaje "
                       f"imovine ili oporavka profitabilnosti, zaključak je "
                       f"čitateljev." if _px and _pb_mkt else
                       " Zaključak je čitateljev.")),
            }
        elif _zl > 1.5 * bvps and _roe_used > _r_used:
            value_vs_book = {
                "kind": "iznad_knjige", **_nums,
                "title": "Zašto je naša procjena iznad knjigovodstvene vrijednosti",
                "plain": (
                    f"Fer-zona ({_hr(_zl)}–{_hr(_zh)} €) viša je od knjigovodstvene "
                    f"vrijednosti ({_hr(bvps)} € po dionici). Firma na vlastitom "
                    f"kapitalu zarađuje oko {_hr(_roe_used * 100, 1)} % godišnje, više od "
                    f"zahtijevanog prinosa od {_hr(_r_used * 100, 1)} % — kapital koji trajno "
                    f"zarađuje iznad tražene stope opravdano vrijedi više od knjige "
                    f"(ista logika po kojoj slab povrat vuče vrijednost ispod nje). "
                    f"Zaključak je čitateljev."),
            }

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
            # v2 §5: reconciliation identitet — raščlamba po stavkama
            "identity": json.loads(json.dumps(a.get("identity"), default=_f))
            if a.get("identity") else None,
            "identity_note": a.get("identity_note"),
            "parent_child_mismatch": a.get("parent_child_mismatch"),
        }

    # pretpostavke s izvorima (read-only na stranici) + eksplicitne oznake nesigurnosti
    assumption_flags = []
    borigin = getattr(params, "beta_origin", None)
    if borigin and borigin != "regresija":
        bval = getattr(params, "beta", None)
        assumption_flags.append(
            {"key": "beta",
             "label": f"β = {bval:.2f} ({borigin})" if bval else f"β ({borigin})",
             "status": "pretpostavka",
             "why": ("vlastita burzovna serija ove dionice ne daje pouzdanu "
                     "betu (nelikvidnost/kratka serija) — korištena je "
                     "sektorska beta (Damodaran, Europa)"
                     + ("; finalna vrijednost ograničena na raspon [0,7, 1,8]"
                        if borigin == "clamp" else "")
                     + "; postupak je opisan u Metodologiji")})
    if getattr(params, "illiq_premium", 0.0):
        assumption_flags.append(
            {"key": "illiq", "label": f"premija nelikvidnosti "
             f"+{params.illiq_premium * 100:.1f} p.b.", "status": "izvor",
             "why": getattr(params, "illiq_src", "") or ""})
    # v3 FAZA G: osnova ključnih ulaza (TTM / godišnje) + izvor rasta —
    # badge `godišnji podatak` kad se TTM ne gradi, `kratka serija` za
    # fallback rast; sve s razlogom (radije oznaka nego kriva brojka)
    tm = getattr(ctx, "ttm_meta", {}) or {}
    _ni_m = tm.get("net_income_parent") or {}
    if _ni_m.get("basis") == "ttm":
        assumption_flags.append(
            {"key": "ttm", "label": f"TTM podaci ({_ni_m.get('period')})",
             "status": "izvor",
             "why": ("zarada/prihodi/ROE računaju se na zadnjih 12 mjeseci "
                     "(zadnje godišnje + ovogodišnji kvartali − lanjski "
                     "kvartali) — v3 FAZA G; kvartalni izvještaji su "
                     "nerevidirani")})
    elif _ni_m.get("basis") == "annual" and _ni_m.get("reason"):
        assumption_flags.append(
            {"key": "annual_data", "label": "godišnji podatak",
             "status": "pretpostavka",
             "why": (f"TTM se ne gradi: {_ni_m['reason']} — vrednuje se iz "
                     "zadnjeg godišnjeg izvješća")})
    _gh = ctx.growth_hint or {}
    if _gh.get("short_series"):
        assumption_flags.append(
            {"key": "short_series", "label": "kratka serija (rast)",
             "status": "pretpostavka",
             "why": ("u bazi nema tri godišnja izvješća pa kompozitni g1 "
                     "nastaje bez signala serije — iz održivog rasta "
                     "(ROE × zadržana dobit) i terminalnog sidra, uz cap 8%; "
                     "jedna godišnja usporedba nije stopa rasta (v3.1)")})
    _rh = getattr(ctx, "roe_hint", None)
    if _rh and _rh.get("basis") == "ttm":
        assumption_flags.append(
            {"key": "roe_rule", "label": "ROE pravilo (TTM + 3g medijan)",
             "status": "izvor", "why": _rh["rule"]})
    # v3 FAZA K: rf/ERP/CRP su ručni unosi s datumom (exact_unverified) —
    # eksplicitna oznaka nesigurnosti, ista praksa kao dosad za ERP
    if getattr(params, "crp", None) is not None:
        _illiq_p = getattr(params, "illiq_premium", 0.0) or 0.0
        _r_label = (f"komponente traženog prinosa r = {params.cost_of_equity * 100:.2f}%: "
                    f"nerizična stopa {params.rf * 100:.2f}% + β {getattr(params, 'beta', 0):.2f} × "
                    f"tržišna premija {params.erp * 100:.2f}% + premija rizika zemlje "
                    f"{params.crp * 100:.1f} p.b."
                    + (f" + premija nelikvidnosti {_illiq_p * 100:.1f} p.b."
                       if _illiq_p else ""))
        _r_why = ("nerizična stopa, tržišna premija i premija rizika zemlje "
                  "referentne su tržišne veličine; rizik Hrvatske uračunava "
                  "se točno jednom — kroz premiju rizika zemlje, ne kroz "
                  "nerizičnu stopu ni tržišnu premiju")
        if _illiq_p:
            _r_why += (f". Dodatno se dodaje premija nelikvidnosti "
                       f"{_illiq_p * 100:.1f} p.b. jer se ova dionica rijetko "
                       f"trguje — izlazak iz pozicije nosi stvaran trošak, a niska "
                       f"beta taj rizik ne obuhvaća; zato je traženi prinos viši "
                       f"(i fer-vrijednost niža) nego kod likvidnih dionica")
        _r_why += " (postupak u Metodologiji)"
        assumption_flags.append(
            {"key": "r_components", "label": _r_label,
             "status": "pretpostavka", "why": _r_why})
    if sotp_breakdown is not None:  # samo gdje se SOTP primjenjuje
        # v2 §4: flag opisuje STVARNO primijenjeni diskont, ne default;
        # 'pretpostavka' je samo kad je korišten default 15–25%
        dr = sotp_breakdown.get("holding_discount_range") or [None, None]
        dreason = sotp_breakdown.get("holding_discount_reason") or ""
        if dr[0] is not None:
            lbl = f"holding diskont {dr[0] * 100:.0f}–{dr[1] * 100:.0f}%"
            if "integrirani operativni parent" in dreason:
                assumption_flags.append(
                    {"key": "holding_discount", "label": lbl, "status": "izvor",
                     "why": ("taksonomija v2 §4: kontrola + konsolidacija iste "
                             "djelatnosti — ne tretira se kao pasivni holding")})
            elif "IZMJERENI" in dreason:
                assumption_flags.append(
                    {"key": "holding_discount", "label": lbl, "status": "izvor",
                     "why": ("izmjereni vlastiti P/NAV (serija) — premija se "
                             "klampa na 0; vidi izvor uz SOTP")})
            else:
                assumption_flags.append(
                    {"key": "holding_discount", "label": lbl,
                     "status": "pretpostavka",
                     "why": "vlastiti P/NAV nemjerljiv — default raspon (v2 §4)"})
        # flag samo ako SOTP stvarno sadrži placeholder dijelove (default
        # multiple / nekalibrirani peer P/E) — ne prepisuje se tuđi flag
        ph_parts = [x["name"] for x in (sotp_breakdown.get("parts") or [])
                    if x.get("placeholder")]
        if ph_parts:
            assumption_flags.append(
                {"key": "sotp_multiples",
                 "label": f"SOTP dijelovi na pretpostavljenim multiplama: "
                          f"{', '.join(ph_parts[:3])}",
                 "status": "pretpostavka",
                 "why": "default multiple / nekalibrirani peer P/E — nisu tržišno kalibrirane"})
    if not params.peers_calibrated:
        assumption_flags.append(
            {"key": "peer_multiples", "label": "peer multipli (P/E 12, P/B 1,5)",
             "status": "pretpostavka",
             "why": "nema usporedivog osiguratelja na ZSE (kriteriji odabira "
                    "peera opisani u Metodologiji)"})

    latest_fy = max((r["fiscal_year"] for r in fund if r["fiscal_year"]), default=None)
    audited = any(r["audited"] for r in fund if r["audited"] is not None)

    from datetime import date
    today = date.today()

    # M18: POKAZATELJI — deterministički derivacijski sloj (TTM gdje je izračunljivo,
    # kvartalni sloj, sektorski guardovi). Sve izvedenice u kodu (src/indicators.py).
    from .indicators import build_indicators
    cur.execute("SELECT COALESCE(holding_type,'') FROM companies WHERE id=%s", (company_id,))
    _ht = cur.fetchone()
    is_holding = bool(_ht and _ht[0] == "passive")
    cur.execute("""SELECT id FROM share_classes WHERE company_id=%s
                   ORDER BY is_primary_line DESC, ticker LIMIT 1""", (company_id,))
    _pc = cur.fetchone()
    primary_class_id = _pc[0] if _pc else None
    _liq = _liquidity(cur, classes, today)
    _prim_tk = next((c["ticker"] for c in classes if c.get("is_primary")),
                    classes[0]["ticker"] if classes else None)
    _illiq = any(cl["flag"] in ("low", "very_low") for cl in _liq["classes"]
                 if cl["class_ticker"] == _prim_tk)
    indicators = build_indicators(cur, company_id, ticker, sector, is_holding,
                                  shares, _f(ctx.own_market_cap), primary_class_id,
                                  illiquid=_illiq)

    return {
        "ticker": ticker, "name": name, "sector": sector, "is_group": is_group,
        "isin": comp_isin, "fiscal_year": latest_fy, "audited": audited,
        "generated_at": str(today),
        "data_status": "full",
        "financials_3y": _financials_3y(cur, company_id, shares,
                                        BANK_THREE_Y_ROWS if is_bank else THREE_Y_ROWS),
        "trend": _trend(cur, company_id, sector),
        "news": _news(cur, company_id),
        "business_profile": _business_profile(cur, company_id, sector),
        "global_peers": _global_peers(sector),
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
            "dps_label": dps_fy_label,  # Z2: "zadnja isplata FY20XX" kad je fallback
            "shares_ex_treasury": shares,
            "market_cap_eur": _f(ctx.own_market_cap),
            "ebitda_eur": _val(fund, "ebitda"),
            "per_class": _per_class_ratios(classes, eps, bvps, dps),
            "basis_note": ("per-share: FY konsolidirane financije / dionice bez "
                           "trezorskih; trž.kap = Σ zadnji close klase × dionice klase"),
        },
        "fundamentals": fund,
        "price_summary": _price_summary(cur, classes, today),
        # v3 DIV: kalendar + raspis održive dividende (D_sust) iz motora
        "dividend_calendar": {
            **_dividend_calendar(cur, company_id, today),
            "d_sust": getattr(ctx, "dsust_hint", None),
        },
        "prices": _price_history(cur, company_id),
        "share_class_explainer": share_class_explainer,
        "valuation": {
            "params": {
                "r": _f(params.cost_of_equity), "g": _f(params.perpetual_growth),
                "g_terminal": _f(getattr(params, "terminal_growth", None)),
                "beta": _f(getattr(params, "beta", None)),
                "beta_calibrated": getattr(params, "beta_calibrated", False),
                # Z1: badge porijekla bete + premija nelikvidnosti (komponenta r)
                "beta_origin": getattr(params, "beta_origin", None),
                "illiq_premium": _f(getattr(params, "illiq_premium", 0.0)),
                "illiq_src": getattr(params, "illiq_src", None),
                # v2 §4: STVARNO primijenjeni diskont (iz SOTP-a), ne default
                "holding_discount_low": _f(
                    (sotp_breakdown.get("holding_discount_range") or [None])[0]
                    if sotp_breakdown else params.holding_discount_low),
                "holding_discount_high": _f(
                    (sotp_breakdown.get("holding_discount_range") or [None, None])[1]
                    if sotp_breakdown else params.holding_discount_high),
                "holding_discount_reason": (
                    sotp_breakdown.get("holding_discount_reason")
                    if sotp_breakdown else None),
                "peer_pe": _f(params.peer_pe), "peer_pb": _f(params.peer_pb),
                "rates_calibrated": params.rates_calibrated,
                "peers_calibrated": params.peers_calibrated,
                "peers_narrow": getattr(params, "peers_narrow", False),
                # v3 FAZA K: komponente r-a za raspis u UI
                # (r = rf + β×ERP + CRP + nelikvidnost, svaka s izvorom)
                "rf": _f(getattr(params, "rf", None)),
                "erp": _f(getattr(params, "erp", None)),
                "crp": _f(getattr(params, "crp", None)),
                "sources": params.sources,
                # v3.1 DIO 2: kompozitni g1 — raspis tri signala,
                # pobjednik i badge porijekla za UI (Pretpostavke)
                "growth": ({
                    "g1": _f(_gh.get("g1")),
                    "signals": (_gh.get("signals") or {}).get("signals"),
                    "origin": (_gh.get("signals") or {}).get("origin"),
                    "winner": (_gh.get("signals") or {}).get("winner"),
                    "badges": (_gh.get("signals") or {}).get("badges") or [],
                    "ttm_context": _f(_gh.get("ttm_vs_lani_kontekst")),
                    "short_series": bool(_gh.get("short_series")),
                    # M47: verdikt održivosti + narativ (zašto je rast održiv/nije)
                    "verdict": _gh.get("verdict"),
                    "assessment": _gh.get("assessment"),
                    "source": _gh.get("source"),
                } if _gh.get("g1") is not None else None),
            },
            "assumption_flags": assumption_flags,
            "ran": ran, "skipped": skipped, "reconciliation": reconciliation,
            "sotp": sotp_breakdown,
            # raskorak prinosne i knjigovodstvene vrijednosti (generirano)
            "value_vs_book": value_vs_book,
        },
        # M17: 'Kako je nastala ova procjena' — generirano iz istih podataka
        "methodology": (_methodology_note(
            cur, company_id, name, reconciliation,
            {"r": _f(params.cost_of_equity), "g": _f(params.perpetual_growth),
             "g_terminal": _f(getattr(params, "terminal_growth", None)),
             "beta": _f(getattr(params, "beta", None)),
             "beta_calibrated": getattr(params, "beta_calibrated", False),
             "peers_calibrated": params.peers_calibrated,
             "peers_narrow": getattr(params, "peers_narrow", False),
             "peer_pe": _f(params.peer_pe)},
            sotp_breakdown, assumption_flags, ctx.growth_hint)
            if reconciliation else None),
        # M18: puni set pokazatelja (≥ investiramo.com) s TTM/kvartalnim slojem
        "indicators": indicators,
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
