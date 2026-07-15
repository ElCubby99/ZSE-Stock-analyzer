"""Z1: disciplina bete i troška kapitala.

Problem koji rješava (stale-price bias): regresijska beta nelikvidne dionice
je statistički smeće — rijetko trgovanje obara betu i umjetno SNIŽAVA r, pa
procjena ispada preoptimistična (CROS: β 0,76 uz ~40% trgovanih dana).

Pravila (v2.2 metodologije):
1. PRAG LIKVIDNOSTI: vlastita regresijska beta koristi se SAMO ako je klasa
   trgovana >= 60% burzovnih dana (zadnjih 365 d) I prosječni dnevni promet
   >= 1.000 EUR. Ispod praga -> sektorska beta.
2. IZNAD praga: Blume adjustment (0,67·β + 0,33·1) — regresijske bete
   mean-revertiraju prema 1.
3. ISPOD praga / bez serije: sektorska beta (Damodaran, Europe) relevered
   s D/E firme gdje je dug dostupan (HR porez 18%); financijski sektori
   koriste sektorsku levered betu izravno (relever nema smisla).
4. CLAMP: finalna beta u [0,7, 1,8]; izlazak se bilježi kao porijeklo 'clamp'.
5. PREMIJA NELIKVIDNOSTI na r (zasebna komponenta, ne kroz betu):
   +1,0 p.b. ispod praga; +2,0 p.b. za vrlo nelikvidne (<20% dana ili
   <300 EUR/dan). Prikazuje se kao vlastita kartica u pretpostavkama.
"""
from __future__ import annotations

import json

LIQ_MIN_RATIO = 0.60      # min. udio trgovanih dana (zadnjih 365 d)
LIQ_MIN_TURNOVER = 1000.0  # min. prosječni dnevni promet (EUR)
VLOW_RATIO = 0.20
VLOW_TURNOVER = 300.0
BETA_MIN, BETA_MAX = 0.7, 1.8
HR_TAX = 0.18

# Sektorske UNLEVERED bete (Damodaran, Europe; korigirano za novac).
# NAPOMENA O IZVORU: pages.stern.nyu.edu je nedostupan iz build okruženja
# (egress 403) — vrijednosti su unesene ručno prema Damodaranovoj tablici
# (siječanj 2026) i označene sector_beta_exact_unverified (ista praksa kao
# ERP). Financijski sektori (bank/insurance/fund): LEVERED sektorska beta,
# relever se ne primjenjuje (poluga je dio poslovnog modela).
SECTOR_BETA = {
    #  sektor        (beta, levered?, Damodaran grana)
    "bank":         (1.05, True,  "Banks (Regional)"),
    "insurance":    (0.95, True,  "Insurance (General)"),
    "fund":         (0.90, True,  "Investments & Asset Management"),
    "tourism":      (0.90, False, "Hotel/Gaming"),
    "consumer":     (0.65, False, "Food Processing / Retail"),
    "industrial":   (1.00, False, "Machinery / Electrical Equipment"),
    "holding":      (0.85, False, "Diversified"),
    "telecom":      (0.70, False, "Telecom Services"),
    "technology":   (1.00, False, "Software (System & Application)"),
    "energy":       (0.70, False, "Oil/Gas Distribution (pipeline)"),
    "shipping":     (0.90, False, "Shipbuilding & Marine"),
    "transport":    (1.10, False, "Air Transport"),
    "construction": (0.90, False, "Engineering/Construction"),
    "real_estate":  (0.80, False, "R.E. (Operations & Services)"),
    "aquaculture":  (0.70, False, "Farming/Agriculture"),
    "other":        (0.85, False, "Total market ex-financials (aproks.)"),
}
SECTOR_BETA_SRC = ("sektorske unlevered/levered bete: Damodaran (pages.stern."
                   "nyu.edu, Europe, tablica siječanj 2026); TOČAN REDAK "
                   "NEPROVJEREN (egress 403) — sector_beta_exact_unverified=true")


def liquidity_stats(conn, ticker: str) -> dict:
    """Likvidnost primarne klase firme (zadnjih 365 dana)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT sc.id FROM share_classes sc JOIN companies c ON c.id=sc.company_id
               WHERE c.ticker=%s ORDER BY sc.is_primary_line DESC NULLS LAST, sc.id
               LIMIT 1""", (ticker,))
        r = cur.fetchone()
        if not r:
            return {"ratio": 0.0, "avg_turnover": 0.0, "trading_days": 0, "idx_days": 0}
        scid = r[0]
        cur.execute(
            """SELECT
                 (SELECT COUNT(*) FROM prices_eod p WHERE p.share_class_id=%s
                    AND p.trade_date > CURRENT_DATE - 365
                    AND COALESCE(p.turnover_eur, 0) > 0),
                 (SELECT COALESCE(SUM(p.turnover_eur), 0) FROM prices_eod p
                    WHERE p.share_class_id=%s AND p.trade_date > CURRENT_DATE - 365),
                 (SELECT COUNT(DISTINCT trade_date) FROM index_eod
                    WHERE trade_date > CURRENT_DATE - 365)""",
            (scid, scid))
        days, turnover, idx_days = cur.fetchone()
    idx_days = max(int(idx_days or 0), 1)
    return {"trading_days": int(days or 0), "idx_days": idx_days,
            "ratio": (days or 0) / idx_days,
            "avg_turnover": float(turnover or 0) / 252.0}


def _de_ratio(conn, ticker: str) -> float | None:
    """Tržišni D/E: (kratkoročni + dugoročni fin. dug) / trž. kap; None kad
    dug nije u bazi (tada UNLEVERED uz napomenu — radije prazno nego krivo)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT fin.item, fin.value_eur FROM financials fin
               JOIN filings f ON f.id=fin.filing_id
               JOIN companies c ON c.id=f.company_id
               WHERE c.ticker=%s AND f.period_type='annual' AND f.basis='consolidated'
                 AND fin.item IN ('short_term_debt','long_term_debt','total_debt')
                 AND f.fiscal_year=(SELECT MAX(f2.fiscal_year) FROM filings f2
                    WHERE f2.company_id=c.id AND f2.period_type='annual'
                      AND f2.basis='consolidated')""", (ticker,))
        items = {k: float(v) for k, v in cur.fetchall() if v is not None}
        debt = items.get("total_debt")
        if debt is None and ("short_term_debt" in items or "long_term_debt" in items):
            debt = items.get("short_term_debt", 0.0) + items.get("long_term_debt", 0.0)
        if debt is None:
            return None
        cur.execute(
            """SELECT SUM(px.close_eur * (sc.shares_issued - COALESCE(sc.treasury_shares,0)))
               FROM share_classes sc
               JOIN companies c ON c.id=sc.company_id
               LEFT JOIN LATERAL (SELECT close_eur FROM prices_eod p
                 WHERE p.share_class_id=sc.id AND p.close_eur IS NOT NULL
                 ORDER BY p.trade_date DESC LIMIT 1) px ON TRUE
               WHERE c.ticker=%s AND sc.shares_issued IS NOT NULL""", (ticker,))
        r = cur.fetchone()
        mcap = float(r[0]) if r and r[0] else None
    if not mcap or mcap <= 0:
        return None
    return debt / mcap


def resolve_beta(conn, ticker: str, sector: str | None) -> dict:
    """Finalna beta + porijeklo + premija nelikvidnosti. Sve odluke se
    vraćaju s objašnjenjem (src) za 'Pretpostavke' kartice."""
    liq = liquidity_stats(conn, ticker)
    liquid = liq["ratio"] >= LIQ_MIN_RATIO and liq["avg_turnover"] >= LIQ_MIN_TURNOVER
    vlow = liq["ratio"] < VLOW_RATIO or liq["avg_turnover"] < VLOW_TURNOVER
    liq_txt = (f"{liq['trading_days']}/{liq['idx_days']} trgovanih dana "
               f"({liq['ratio']:.0%}), prosj. promet {liq['avg_turnover']:,.0f} €/dan")

    # kalibrirana regresijska beta (M10)
    cal = None
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM calibrations WHERE key=%s", (f"beta:{ticker}",))
        r = cur.fetchone()
        if r:
            cal = r[0] if isinstance(r[0], dict) else json.loads(r[0])
            if not cal.get("calibrated"):
                cal = None

    origin, beta, src = None, None, None
    if cal and liquid:
        raw = float(cal["beta"])
        beta = 0.67 * raw + 0.33 * 1.0  # Blume adjustment
        origin = "regresija"
        src = (f"beta={beta:.2f}: IZMJERENA regresijom (OLS tjednih log-prinosa "
               f"{cal['class_ticker']} vs CROBEX, {cal['period']}, n={cal['n_weeks']} tj., "
               f"R²={cal['r2']}) uz Blume prilagodbu 0,67·{raw} + 0,33·1 "
               f"(regresijske bete mean-revertiraju prema 1). Likvidnost iznad praga: {liq_txt}.")
    else:
        sb, levered, branch = SECTOR_BETA.get(sector) or SECTOR_BETA["other"]
        why_sector = (f"vlastita regresijska beta ODBAČENA — likvidnost ispod praga "
                      f"(prag: ≥{LIQ_MIN_RATIO:.0%} dana i ≥{LIQ_MIN_TURNOVER:,.0f} €/dan; "
                      f"stanje: {liq_txt}); stale-price bias nelikvidne serije umjetno "
                      f"obara betu" if cal else
                      f"nema kalibrirane regresijske bete (serija prekratka/nelikvidna; {liq_txt})")
        if levered:
            beta = sb
            src = (f"beta={beta:.2f}: SEKTORSKA levered ({branch}) — {why_sector}. "
                   f"{SECTOR_BETA_SRC}. Financijski sektor: poluga je dio poslovnog "
                   f"modela, relever se ne primjenjuje.")
        else:
            de = _de_ratio(conn, ticker)
            if de is not None:
                beta = sb * (1 + (1 - HR_TAX) * de)
                src = (f"beta={beta:.2f}: SEKTORSKA unlevered {sb} ({branch}) "
                       f"relevered s D/E={de:.2f} firme (porez 18%): "
                       f"β = βU·(1+(1−t)·D/E). {why_sector}. {SECTOR_BETA_SRC}.")
            else:
                beta = sb
                src = (f"beta={beta:.2f}: SEKTORSKA unlevered {sb} ({branch}) — "
                       f"D/E firme nije u bazi pa se koristi unlevered (konzervativno "
                       f"za zaduženije firme, NAPOMENA uz procjenu). {why_sector}. "
                       f"{SECTOR_BETA_SRC}.")
        origin = "sektorska (nelikvidno)" if cal else "sektorska (nema serije)"

    # clamp [0,7, 1,8]
    if beta < BETA_MIN or beta > BETA_MAX:
        rub = BETA_MIN if beta < BETA_MIN else BETA_MAX
        src += (f" CLAMP: izračunata beta {beta:.2f} izvan granica "
                f"[{BETA_MIN}, {BETA_MAX}] -> zamijenjena rubom {rub}.")
        beta = rub
        origin = "clamp"

    # premija nelikvidnosti (zasebna komponenta r-a)
    if liquid:
        premium, prem_src = 0.0, None
    else:
        premium = 0.02 if vlow else 0.01
        prem_src = (f"premija nelikvidnosti +{premium * 100:.1f} p.b. na r: {liq_txt} — "
                    f"izlazak iz pozicije nosi stvaran trošak (širok spread, plitka "
                    f"knjiga); stupnjevano: <{VLOW_RATIO:.0%} dana ili "
                    f"<{VLOW_TURNOVER:.0f} €/dan -> +2,0 p.b., ispod praga "
                    f"({LIQ_MIN_RATIO:.0%} dana / {LIQ_MIN_TURNOVER:,.0f} €/dan) -> +1,0 p.b. "
                    f"Literatura: nelikvidnosna premija je standardan dodatak na CAPM "
                    f"za netrgovane/slabo trgovane dionice.")

    return {"beta": round(beta, 3), "origin": origin, "src": src,
            "illiq_premium": premium, "illiq_src": prem_src,
            "liquidity": liq}
