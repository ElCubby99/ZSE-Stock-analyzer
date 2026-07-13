"""
valuation_methods.py — registar valuacijskih metoda za ZSE analitiku.

DIZAJN (vidi razgovor):
- Po dionici pokrećemo SVAKU primjenjivu metodu, ne jednu.
- Primjenjivost je RULE-GATED + DATA-GATED: metoda se pokreće samo ako (a) prođe
  strukturni test I (b) postoje potrebni ulazi s dovoljnim confidenceom.
  Model NE odlučuje slobodno smije li metoda raditi — inače pokrene EV/EBITDA na banci
  jer "zna podijeliti". Modelova prosudba je samo za sivu zonu i za NARACIJU raskoraka.
- Output nije jedan broj nego skup (metoda -> raspon) + reconciliation: slaganje/neslaganje
  metoda JE signal (ADRS: P/B leća ~knjiga vs SOTP leća ~NAV; raskorak = holding diskont).

IMPLEMENTACIJA (compute_*):
- Eligibility logika je NEPROMIJENJENA (zahtjev). Implementirani su samo compute_*,
  Ctx-iz-baze (build_ctx) i CLI.
- Sve pretpostavke (trošak kapitala r, rast g, peer multiplikatori, holding diskont)
  su PARAMETRIZIRANE (Params) i UVIJEK vidljive u ValueRange.assumptions. Defaulti su
  jasno označeni "PLACEHOLDER" — nisu tržišno utvrđeni. Svaki raspon (low/base/high)
  proizlazi iz pomicanja tih pretpostavki, ne iz izmišljanja brojki.
- Ako ulaz nedostaje (npr. nema cijena za SOTP), compute degradira (base=0, niski
  confidence) i u assumptions["missing"] navede ŠTO fali — radije prazno nego izmišljeno.

Radni primjeri:
- CROS (jedan osiguratelj): multiples DA, justified_pb_roe DA, ddm DA, ev_ebitda NE,
  dcf NE, sotp NE (nema materijalnih udjela).
- ADRS (holding): multiples DA, justified_pb_roe DA, ddm DA, sotp DA,
  ev_ebitda NE (konsolidira CROS -> osiguratelj), dcf NE (holding).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

FINANCIAL_SECTORS = {"bank", "insurance"}
OPERATING_SECTORS = {"industrial", "tourism", "aquaculture", "energy", "utility", "retail"}
MATERIAL_PCT = 0.20          # udjel iznad kojeg holding "broji" za SOTP
MIN_CONFIDENCE = 0.85        # ispod ovoga ulaz se tretira kao da ga nema


# ---------- Pretpostavke (PLACEHOLDER) — vidljive u svakom outputu ----------
@dataclass
class Params:
    """Valuacijske pretpostavke. Defaulti su PLACEHOLDER — NISU tržišno utvrđeni.

    Zamijeni stvarnima (CAPM trošak kapitala, peer set sa zse.hr/usporedivih) prije
    nego se ijedan broj tretira kao valuacija, a ne kao ilustracija mehanike.
    """
    cost_of_equity: float = 0.09      # PLACEHOLDER r (DDM, opravdani P/B)
    perpetual_growth: float = 0.025   # g za justified P/B / RI (konzervativni kapitalni g)
    terminal_growth: float = 0.04     # M11 terminal g za DCF/DDM: nominalni BDP (~2% real + ~2% inflacija)
    wacc: float = 0.09                # PLACEHOLDER (DCF diskont)
    peer_pe: float = 12.0             # PLACEHOLDER P/E sidro
    peer_pb: float = 1.5              # PLACEHOLDER P/B sidro
    peer_ev_ebitda: float = 7.0       # PLACEHOLDER EV/EBITDA sidro
    band: float = 0.15                # ±raspon oko sidra za low/high
    holding_discount_low: float = 0.15
    holding_discount_high: float = 0.25
    placeholder: bool = True          # zastava: pretpostavke nisu potvrđene
    # granularna kalibracija (M3): confidence po metodi ovisi o TOME jesu li
    # baš NJEZINI ulazi kalibrirani, ne o globalnoj zastavi
    rates_calibrated: bool = False    # r i g imaju izvor (CAPM komponente)
    beta_calibrated: bool = False     # beta IZMJERENA iz serije (M10), ne 1,0
    peers_calibrated: bool = False    # peer multipli izvedeni iz baze (n>=3)
    sources: dict = field(default_factory=dict)  # komponenta -> izvor/obrazloženje


# ---------- Kontekst koji motor sastavi po firmi PRIJE eligibility provjere ----------
@dataclass
class Ctx:
    ticker: str
    sector: str
    is_group: bool
    holdings: list           # redovi iz v_sotp_inputs (može biti prazno)
    has_segments: bool       # postoje li segment_financials
    # data() vraća (value_eur, confidence) ili None; čita iz v_financials_current
    data: Callable[[str], Optional[tuple]]
    # --- polja koja koristi SAMO compute (ne diraju eligibility) ---
    shares_ex_treasury: Optional[float] = None
    price: Optional[float] = None                       # zadnja cijena primarne klase
    own_market_cap: Optional[float] = None              # vlastita trž.kap (po klasi)
    market_cap_of: Optional[Callable[[str], Optional[float]]] = None  # ticker -> trž.kap ili None
    segment_ebitda_of: Optional[Callable[[str], Optional[float]]] = None  # segment_key -> EBITDA ili None
    # Dio 0.5: fer-vrijednost uvrštene kćeri iz NJENOG sidra (rekurzivno) ili None
    fair_equity_of: Optional[Callable[[int], Optional[tuple]]] = None
    # M11: signal rasta IZ PODATAKA (3g CAGR prihoda) ili None kad serije nema
    growth_hint: Optional[dict] = None
    # M11 (KOEI): dobit matici kćeri po company_id (standalone ostatak SOTP-a)
    ni_parent_of: Optional[Callable[[int], Optional[float]]] = None
    params: Params = field(default_factory=Params)

    def have(self, item: str) -> bool:
        """Ulaz postoji I confidence >= prag. Ovo je 'data gate'."""
        r = self.data(item)
        return r is not None and r[0] is not None and r[1] >= MIN_CONFIDENCE

    @property
    def consolidates_insurer(self) -> bool:
        # Vlasnički graf radi DVOSTRUKI posao: pokreće SOTP I diskvalificira EV/EBITDA.
        return any(h["is_insurance"] and h["ownership_pct"] > 0.50 for h in self.holdings)

    @property
    def material_holdings(self) -> list:
        return [h for h in self.holdings if h["ownership_pct"] >= MATERIAL_PCT]

    @property
    def is_holding(self) -> bool:
        return self.is_group and len(self.material_holdings) >= 1

    # --- compute helperi (ne diraju eligibility) ---
    def val(self, item: str) -> Optional[float]:
        r = self.data(item)
        return r[0] if (r and r[0] is not None) else None


@dataclass
class ValueRange:
    low: float
    base: float
    high: float
    assumptions: dict = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class Method:
    key: str
    label: str
    eligible: Callable[[Ctx], tuple]   # -> (bool, razlog)  razlog se UVIJEK loggira (i za NE)
    compute: Callable[[Ctx], ValueRange]


# ============================================================
#  ELIGIBILITY PREDIKATI  (jezgra — "model mora odlučiti može li")
#  Svaki vraća (bool, razlog). Razlog za NE je također koristan output
#  ("SOTP nije primjenjiv jer nema materijalnih udjela").
#  >>> NEPROMIJENJENO (zahtjev: ne mijenjaj eligibility logiku) <<<
# ============================================================

def elig_multiples(c: Ctx):
    if c.have("net_income_parent") or c.have("total_equity") or c.have("dps"):
        return True, "ima zaradu/knjigu/dividendu"
    return False, "nema osnovnih per-share ulaza"

def elig_ev_ebitda(c: Ctx):
    if c.sector in FINANCIAL_SECTORS:
        return False, f"financijski sektor ({c.sector}) — EBITDA nije smislena"
    if c.consolidates_insurer:
        return False, "konsolidira osiguratelja — EV/EBITDA kontaminiran (deck: 10,7× s ogradom)"
    if not (c.have("ebitda") or (c.have("ebit") and c.have("depreciation_amortization"))):
        return False, "nema EBITDA niti (EBIT + D&A)"
    return True, "operativna firma s EBITDA"

def elig_dcf(c: Ctx):
    if c.sector in FINANCIAL_SECTORS:
        return False, "financije — FCF loše definiran"
    if c.is_holding:
        return False, "holding — FCF ne hvata vrijednost udjela"
    if not (c.have("operating_cf") and c.have("capex")):
        return False, "nema operativni CF i capex"
    return True, "operativna firma s mjerljivim FCF"

def elig_ddm(c: Ctx):
    if not c.have("dps"):
        return False, "ne isplaćuje (ili nepoznata) dividenda"
    return True, "stabilan isplatitelj dividende"

def elig_justified_pb_roe(c: Ctx):
    if not (c.have("total_equity") and c.have("net_income_parent")):
        return False, "nema kapital i/ili dobit za ROE"
    # Posebno vrijedno za financije i niska-ROE holdinge (deck: opravdani P/B 0,6–0,8 -> 55–74€)
    return True, "ima knjigu i ROE (osobito za financije/holding)"

def elig_sotp(c: Ctx):
    if not c.is_group:
        return False, "nije grupa"
    if not (c.material_holdings or c.has_segments):
        return False, "nema materijalnih udjela ni odvojivih segmenata (npr. CROS: jedan biznis)"
    return True, "holding s odvojivim dijelovima (uvršteni udjeli i/ili segmenti)"


# --- M5: NOVI predikat (postojeći iznad su NEPROMIJENJENI) ---
def elig_residual_income(c: Ctx):
    if c.sector not in FINANCIAL_SECTORS:
        return False, f"RI predložak je za financijske firme (banka/osiguranje), ne {c.sector}"
    if not ((c.have("equity_parent") or c.have("total_equity")) and c.have("net_income_parent")):
        return False, "nema kapital i/ili dobit matici za ROE"
    return True, "financijska firma — RI kroz višak povrata na kapital"


# ============================================================
#  COMPUTE — implementirano. Svaki vraća raspon (low/base/high) + vidljive
#  pretpostavke + confidence. Per-share (EUR po dionici), dionice = shares_ex_treasury.
# ============================================================

def _per_share(equity_value: Optional[float], c: Ctx) -> Optional[float]:
    n = c.shares_ex_treasury
    if not equity_value or not n:
        return None
    return equity_value / n


def _missing(c: Ctx, *needed: str) -> ValueRange:
    return ValueRange(0, 0, 0, assumptions={"missing": list(needed)}, confidence=0.0)


def _peer_confidence(p, assum: dict) -> float:
    """Pouzdanost multipl-metoda ovisi o peer skupu (Korak 1 audita):
    kalibriran (n>=3) 0,7; uski skup (n=2) 0,6; PLACEHOLDER 0,3 — placeholder
    P/E 12 / P/B 1,5 nije podatak nego pretpostavka pa metoda ne smije nositi
    srednju pouzdanost. Ne dira eligibility."""
    if p.peers_calibrated and not getattr(p, "peers_narrow", False):
        return 0.7
    if p.peers_calibrated:
        assum["narrow_peers"] = "uski peer skup (n=2) -> snižena pouzdanost"
        return 0.6
    assum["low_confidence"] = ("peer multipli su placeholder (nema peer skupa "
                               "na ZSE) -> niska pouzdanost")
    return 0.3


def compute_multiples(c: Ctx) -> ValueRange:
    """P/E i P/B leća: vrijednost/dionica = peer_multiple × (zarada matice | knjiga matice) / dionice.

    P/B leća: za OPERATIVNE firme se NE koristi kad P/E leća postoji —
    standardna praksa: operativna firma se multiplira na zaradu/EBITDA, P/B je
    smislen za financijske (i njih ionako nosi opravdani P/B iz vlastitog
    ROE-a). P/B ostaje samo kao FALLBACK bez pozitivne zarade, skaliran
    omjerom ROE naniže (peer P/B nije prenosiv na drugačiju profitabilnost)."""
    p = c.params
    ni = c.val("net_income_parent")
    eq = c.val("equity_parent") or c.val("total_equity")
    lenses, assum = [], {"placeholder": p.placeholder}
    if ni is not None and ni > 0:
        pe_ps = _per_share(p.peer_pe * ni, c)
        if pe_ps is not None:
            lenses.append(pe_ps); assum["peer_pe"] = p.peer_pe
    arche = ARCHETYPE_OF.get(c.sector or "", "operating")
    use_pb = (arche == "capital") or not lenses   # operativna: P/E leća dovoljna
    if eq is not None and use_pb:
        pb_mult = p.peer_pb
        peer_roe = getattr(p, "peer_roe", None)
        own_roe = (ni / eq) if (ni is not None and eq and ni > 0) else None
        if peer_roe and own_roe:
            # korekcija SAMO NANIŽE: firmi nižeg ROE-a peer P/B se smanjuje;
            # višem ROE-u se NE ekstrapolira naviše (zarada je već u P/E leći)
            scale = max(0.3, min(1.0, own_roe / peer_roe))
            pb_mult = p.peer_pb * scale
            assum["pb_roe_scale"] = (
                f"P/B leća skalirana omjerom ROE: vlastiti {own_roe:.1%} / "
                f"peer medijan {peer_roe:.1%} = {own_roe / peer_roe:.2f} "
                f"(klampano na [0,3–1,0] -> {scale:.2f}); peer P/B bez ROE "
                f"konteksta nije prenosiv, a naviše se ne ekstrapolira")
        pb_ps = _per_share(pb_mult * eq, c)
        if pb_ps is not None:
            lenses.append(pb_ps); assum["peer_pb"] = round(pb_mult, 2)
    elif eq is not None and not use_pb:
        assum["pb_lens"] = ("P/B leća izostavljena: operativna firma se "
                            "multiplira na zaradu (P/E) i EBITDA; peer P/B "
                            "nije prenosiv bez ROE konteksta")
    if not lenses:
        return _missing(c, "net_income_parent|equity_parent", "shares_ex_treasury")
    if p.sources.get("peers"):
        assum["sources"] = {"peers": p.sources["peers"]}
    base = sum(lenses) / len(lenses)
    return ValueRange(base * (1 - p.band), base, base * (1 + p.band), assum,
                      _peer_confidence(p, assum))


def compute_ev_ebitda(c: Ctx) -> ValueRange:
    """EV = peer_ev_ebitda × EBITDA; equity = EV − net_dug; /dionice. (Ne treba tekuća cijena.)"""
    p = c.params
    ebitda = c.val("ebitda")
    if ebitda is None:
        ebit, da = c.val("ebit"), c.val("depreciation_amortization")
        ebitda = (ebit + da) if (ebit is not None and da is not None) else None
    if ebitda is None:
        return _missing(c, "ebitda")
    net_debt = c.val("net_debt")
    if net_debt is None:
        return _missing(c, "net_debt")
    def ps(mult):
        ev = mult * ebitda
        return _per_share(ev - net_debt, c)  # net_debt<0 (neto novac) => equity > EV
    base = ps(p.peer_ev_ebitda)
    if base is None:
        return _missing(c, "shares_ex_treasury")
    lo, hi = ps(p.peer_ev_ebitda * (1 - p.band)), ps(p.peer_ev_ebitda * (1 + p.band))
    assum = {"peer_ev_ebitda": p.peer_ev_ebitda, "net_debt": net_debt, "placeholder": p.placeholder}
    if p.sources.get("peers"):
        assum["sources"] = {"peers": p.sources["peers"]}
    return ValueRange(lo, base, hi, assum, _peer_confidence(p, assum))


def compute_dcf(c: Ctx) -> ValueRange:
    """M11 dvofazni DCF: eksplicitna faza rasta (g1 iz 3g CAGR-a prihoda,
    linearni fade prema terminalnom g kroz 5 g) + terminalna vrijednost.
    NE rasti trailing FCF terminalnim g-om; bez serije rasta -> jednofazno
    s OZNAKOM da eksplicitna faza nije izvedena iz podataka."""
    p = c.params
    fcf = c.val("free_cash_flow")
    if fcf is None:
        ocf, capex = c.val("operating_cf"), c.val("capex")
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
    if fcf is None:
        return _missing(c, "free_cash_flow|operating_cf+capex")
    net_debt = c.val("net_debt") or 0.0
    gT = p.terminal_growth
    gh = c.growth_hint or {}
    g1 = gh.get("g1")

    def ps(wacc):
        if wacc <= gT:
            return None
        if g1 is None:
            ev = fcf * (1 + gT) / (wacc - gT)
        else:
            ev, f = 0.0, fcf
            for yr in range(1, 6):
                g_yr = g1 + (gT - g1) * (yr - 1) / 4     # linearni fade g1 -> gT
                f *= (1 + g_yr)
                ev += f / (1 + wacc) ** yr
            ev += (f * (1 + gT) / (wacc - gT)) / (1 + wacc) ** 5
        return _per_share(ev - net_debt, c)

    base = ps(p.wacc)
    if base is None:
        return _missing(c, "shares_ex_treasury|wacc>g")
    lo, hi = ps(p.wacc + 0.01), ps(p.wacc - 0.01)
    assum = {"wacc": p.wacc, "g_terminal": gT, "g1_explicit": g1,
             "model": ("dvofazni: 5 g eksplicitno (g1 fade->gT) + terminal"
                       if g1 is not None else
                       "jednofazni Gordon — RAST NIJE IZVEDEN (nema 3g serije prihoda)"),
             "growth_source": gh.get("source"),
             "placeholder": p.placeholder}
    src = {k: p.sources[k] for k in ("wacc", "g") if p.sources.get(k)}
    if src:
        assum["sources"] = src
    return ValueRange(lo or base, base, hi or base, assum,
                      0.6 if p.rates_calibrated else 0.4)


def compute_ddm(c: Ctx) -> ValueRange:
    """M11 dvofazni DDM: DPS raste g1 (iz 3g CAGR-a prihoda, fade->gT) 5 g,
    zatim Gordon terminal; bez serije -> jednofazno s oznakom."""
    p = c.params
    dps = c.val("dps")
    if dps is None:
        return _missing(c, "dps")
    gT = p.terminal_growth
    gh = c.growth_hint or {}
    g1 = gh.get("g1")

    def v(r):
        if r <= gT:
            return None
        if g1 is None:
            return dps * (1 + gT) / (r - gT)
        pv, d = 0.0, dps
        for yr in range(1, 6):
            g_yr = g1 + (gT - g1) * (yr - 1) / 4
            d *= (1 + g_yr)
            pv += d / (1 + r) ** yr
        return pv + (d * (1 + gT) / (r - gT)) / (1 + r) ** 5

    base = v(p.cost_of_equity)
    if base is None:
        return _missing(c, "r>g")
    lo, hi = v(p.cost_of_equity + 0.01), v(p.cost_of_equity - 0.01)
    assum = {"dps": dps, "r": p.cost_of_equity, "g_terminal": gT, "g1_explicit": g1,
             "model": ("dvofazni DDM" if g1 is not None else
                       "jednofazni Gordon — RAST NIJE IZVEDEN"),
             "growth_source": gh.get("source"), "placeholder": p.placeholder}
    src = {k: p.sources[k] for k in ("r", "g") if p.sources.get(k)}
    if src:
        assum["sources"] = src
    return ValueRange(lo or base, base, hi or base, assum,
                      0.7 if p.rates_calibrated else 0.5)


def compute_justified_pb_roe(c: Ctx) -> ValueRange:
    """Opravdani P/B = (ROE − g)/(r − g); vrijednost/dionica = opravdani_PB × BVPS."""
    p = c.params
    ni = c.val("net_income_parent")
    eq = c.val("equity_parent") or c.val("total_equity")
    if ni is None or not eq:
        return _missing(c, "net_income_parent", "equity_parent")
    bvps = _per_share(eq, c)
    if bvps is None:
        return _missing(c, "shares_ex_treasury")
    roe = ni / eq
    def v(r):
        if r <= p.perpetual_growth:
            return None
        jpb = (roe - p.perpetual_growth) / (r - p.perpetual_growth)
        return jpb * bvps
    base = v(p.cost_of_equity)
    if base is None:
        return _missing(c, "r>g")
    lo, hi = v(p.cost_of_equity + 0.01), v(p.cost_of_equity - 0.01)
    assum = {"roe": round(roe, 4), "r": p.cost_of_equity, "g": p.perpetual_growth,
             "bvps": round(bvps, 2), "placeholder": p.placeholder}
    src = {k: p.sources[k] for k in ("r", "g") if p.sources.get(k)}
    if src:
        assum["sources"] = src
    return ValueRange(lo or base, base, hi or base, assum,
                      0.7 if p.rates_calibrated else 0.5)


def compute_sotp(c: Ctx) -> ValueRange:
    """
    Σ vrijednost udjela + neto novac − holding diskont, sve / shares_ex_treasury.
      - listed (basis='market'): trž.kap.(held) × pct  [trž.kap = cijena × shares_ex_treasury TE firme]
      - unlisted (basis='ebitda_multiple'): segment_ebitda × default_multiple × pct
    Neto novac = −net_debt (derivat iz ekstrakcije: dug − novac); fallback na
    cash_and_equivalents ako net_debt ne postoji (tada je to BRUTO novac — flag).
    FLAGOVI koji MORAju biti eksplicitni u assumptions (deckov sofisticirani dio):
      - net_cash_excludes_insurance_portfolio: portfelj u CO-u pokriva osig. obveze, NIJE slobodan novac
      - holding_discount: raspon 0.15–0.25 (low/high scenariji) + zašto (holding_discount_reason)
      - listed_stake_repricing: scenarij 'CROS po fer P/E 12' kao konzervativno sidro (deck: NAV ~95€)
    Breakdown po komponenti ide u assumptions["parts"]:
      {name, value_eur, basis, pct, placeholder} — placeholder=True za multiple
      komponente (default_multiple je pretpostavka), False za tržišne.
    """
    p = c.params
    assum = {
        "holding_discount_range": [p.holding_discount_low, p.holding_discount_high],
        "holding_discount_reason": (
            "empirijski raspon konglomeratskog/holding diskonta za europske "
            "holdinge (nelikvidnost, dvostruko oporezivanje dividendi, trošak "
            "centra); PLACEHOLDER dok se ne kalibrira na ZSE povijest"
        ),
        "net_cash_excludes_insurance_portfolio": True,
        "listed_repricing_scenario": "CROS @ P/E 12 = konzervativno sidro",
        "placeholder": p.placeholder,
    }
    # Dio 0.5 (rekurzivni SOTP): za UVRŠTENE kćeri vodimo DVIJE vrijednosti —
    # tržišnu (kao dosad) i NAŠU fer-procjenu (sidro kćeri, rekurzivno).
    # Primarni NAV (fer-zona) koristi fer-procjenu; obje brojke idu u izlaz.
    gross_fair, gross_mkt, parts, missing = 0.0, 0.0, [], []
    for h in c.holdings:
        pct = h["ownership_pct"]
        if h["valuation_basis"] == "market":
            mc = c.market_cap_of(h["held_company_id"]) if (c.market_cap_of and h.get("held_company_id")) else None
            if mc is None:
                missing.append(f"trž.kap({h['held_name']})"); continue
            stake_mkt = mc * pct
            fv = c.fair_equity_of(h["held_company_id"]) if c.fair_equity_of else None
            if fv is not None:
                stake_fair = fv[0] * pct
                basis = f"fer-procjena: {fv[1]} × {pct:.4f}"
                fair_basis = "our_estimate"
            else:
                stake_fair = stake_mkt
                basis = (f"market: trž.kap {mc:,.0f} × {pct:.4f} — kći nije "
                         f"analizirana u sustavu, tržišna vrijednost")
                fair_basis = "market_fallback"
            gross_mkt += stake_mkt
            gross_fair += stake_fair
            parts.append({"name": h["held_name"], "value_eur": round(stake_fair, 0),
                          "value_market_eur": round(stake_mkt, 0),
                          "fair_basis": fair_basis,
                          "basis": basis, "pct": pct, "placeholder": False})
            continue
        elif h["valuation_basis"] == "ebitda_multiple":
            seg = c.segment_ebitda_of(h["segment_key"]) if (c.segment_ebitda_of and h.get("segment_key")) else None
            if seg is None:
                missing.append(f"segment_ebitda({h['segment_key']})"); continue
            stake = seg * (h["default_multiple"] or 0) * pct
            basis = (f"ebitda_multiple: {seg:,.0f} [{h['segment_key']}] "
                     f"× {h['default_multiple']} × {pct:.2f}")
            is_placeholder = True  # default_multiple je pretpostavka
        elif h["valuation_basis"] == "residual_pe":
            # standalone ostatak matice: (NI matici grupe - Σ pripisive NI
            # uvrštenih kćeri) × peer P/E — aproksimacija, jasno označena
            ni_group = c.val("net_income_parent")
            if ni_group is None or not c.ni_parent_of:
                missing.append(f"residual_pe({h['held_name']})"); continue
            attributable = 0.0
            for h2 in c.holdings:
                if h2["valuation_basis"] == "market" and h2.get("held_company_id"):
                    ni_sub = c.ni_parent_of(h2["held_company_id"])
                    if ni_sub is not None:
                        attributable += ni_sub * h2["ownership_pct"]
            resid_ni = ni_group - attributable
            if resid_ni <= 0:
                missing.append(f"residual_pe({h['held_name']}): ostatak dobiti <= 0")
                continue
            stake = resid_ni * p.peer_pe * pct
            basis = (f"residual_pe: (NI matici {ni_group:,.0f} - pripisivo kćerima "
                     f"{attributable:,.0f}) × P/E {p.peer_pe} × {pct:.2f} — aproksimacija")
            is_placeholder = not p.peers_calibrated
        elif h["valuation_basis"] == "no_data":
            # dio bez podataka u bazi (npr. JV) — NE blokira, ide u napomenu
            missing.append(f"{h['held_name']}: nema podataka u bazi (udjel "
                           f"{pct:.0%}) — dio NIJE u NAV-u")
            continue
        else:
            missing.append(f"{h['valuation_basis']}({h['held_name']})"); continue
        gross_fair += stake
        gross_mkt += stake
        parts.append({"name": h["held_name"], "value_eur": round(stake, 0),
                      "value_market_eur": round(stake, 0), "fair_basis": "multiple",
                      "basis": basis, "pct": pct, "placeholder": is_placeholder})
    gross = gross_fair
    assum["parts"] = parts
    if missing:
        assum["missing"] = missing
        if not parts:
            # NIJEDNA komponenta nije izračunljiva -> prazno, ne izmišljeno
            return ValueRange(0, 0, 0, assum, 0.0)
        assum["missing_note"] = ("dijelovi bez ulaza NISU u NAV-u (konzervativno "
                                 "podcjenjuje) — vidi missing")
    nd = c.val("net_debt")
    if nd is not None:
        net_cash = -nd
        assum["net_cash"] = {"value_eur": round(net_cash, 0),
                             "basis": "−net_debt (dug − novac, izvedeno iz ekstrakcije)"}
    else:
        net_cash = c.val("cash_and_equivalents") or 0.0
        assum["net_cash"] = {"value_eur": round(net_cash, 0),
                             "basis": "BRUTO novac (net_debt nedostupan!) — precijenjeno"}
    assum["net_cash_note"] = (
        "grupni agregat: uključuje i novac/dug konsolidiranih društava koja su "
        "već vrednovana tržišno/multiplom — gruba NAV aproksimacija"
    )
    nav = gross + net_cash
    nav_mkt = gross_mkt + net_cash
    lo = _per_share(nav * (1 - p.holding_discount_high), c)
    base = _per_share(nav * (1 - (p.holding_discount_low + p.holding_discount_high) / 2), c)
    hi = _per_share(nav * (1 - p.holding_discount_low), c)
    if base is None:
        assum["missing"] = ["shares_ex_treasury"]
        return ValueRange(0, 0, 0, assum, 0.0)
    assum["nav_gross_eur"] = round(gross, 0)
    assum["nav_total_eur"] = round(nav, 0)
    # Dio 0.5: obje SOTP brojke + signal razlike (tržište kćeri vs naša procjena)
    mid_disc = 1 - (p.holding_discount_low + p.holding_discount_high) / 2
    assum["sotp_fair"] = {"nav_eur": round(nav, 0),
                          "base_per_share": _per_share(nav * mid_disc, c),
                          "note": "kćeri po NAŠOJ fer-procjeni (sidro kćeri, rekurzivno)"}
    assum["sotp_market"] = {"nav_eur": round(nav_mkt, 0),
                            "base_per_share": _per_share(nav_mkt * mid_disc, c),
                            "note": "kćeri po tržišnoj kapitalizaciji"}
    if nav:
        assum["market_vs_fair_pct"] = round((nav_mkt / nav - 1) * 100, 1)
        assum["market_vs_fair_note"] = (
            "pozitivno = tržište vrednuje uvrštene kćeri IZNAD naše procjene "
            "(fer-zona matice koristi našu procjenu); razlika je signal, ne preporuka")
    if p.sources.get("holding_discount"):
        assum["sources"] = {"holding_discount": p.sources["holding_discount"]}
    # TRŽIŠNA USPOREDBA (dokaz uz diskont): vlastita trž.kap vs NAV prije diskonta
    if c.own_market_cap and nav:
        prem = c.own_market_cap / nav - 1
        assum["market_check"] = {
            "own_market_cap_eur": round(c.own_market_cap, 0),
            "nav_pre_discount_eur": round(nav, 0),
            "price_vs_nav_pct": round(prem * 100, 1),
            "note": ("tekuća cijena vs OVAJ (konzervativni) NAV; povijesna "
                     "serija cijena↔NAV je kalibrirana (M10) — vidi izvor "
                     "holding diskonta i docs/calibration.md"),
        }
    # confidence: većina NAV-a iz tržišnih cijena -> 0.6; inače 0.5.
    market_share = (sum(x["value_eur"] for x in parts if not x["placeholder"]) / gross) if gross else 0
    assum["market_based_share_of_gross"] = round(market_share, 2)
    return ValueRange(lo, base, hi, assum, 0.6 if market_share >= 0.7 else 0.5)


def compute_residual_income(c: Ctx) -> ValueRange:
    """Rezidualni dohodak (M5, za financije): V = BV0 + Σ RI_t/(1+COE)^t.

    RI_t = (ROE_t − COE) × BV_{t-1}; ROE linearno FEJDA od tekućeg ROE-a prema
    COE kroz FADE_YEARS godina (u zadnjoj godini ROE=COE → RI=0 → terminal 0,
    konzervativno). BV raste stopom g.

    ISKRENA OGRADA (uvijek u assumptions): jednostupanjski RI (konstantan ROE,
    rast g) je MATEMATIČKI identičan opravdanom P/B-u ((ROE−g)/(COE−g)×BVPS).
    Bez eksplicitnih forecasta ROE-a razlika prema justified_pb_roe dolazi
    isključivo iz fadea — sličnost tih dviju brojki je provjera konzistentnosti,
    ne nova informacija.
    """
    p = c.params
    FADE_YEARS = 5
    ni = c.val("net_income_parent")
    eq = c.val("equity_parent") or c.val("total_equity")
    if ni is None or not eq:
        return _missing(c, "net_income_parent", "equity_parent")
    bvps = _per_share(eq, c)
    if bvps is None:
        return _missing(c, "shares_ex_treasury")
    roe0 = ni / eq
    g = p.perpetual_growth

    def v(coe):
        if coe <= g:
            return None
        val, bv = bvps, bvps
        for t in range(1, FADE_YEARS + 1):
            roe_t = roe0 + (coe - roe0) * t / FADE_YEARS   # fade: ROE_N == COE
            val += (roe_t - coe) * bv / (1 + coe) ** t
            bv *= (1 + g)
        return val

    base = v(p.cost_of_equity)
    if base is None:
        return _missing(c, "COE>g")
    lo, hi = v(p.cost_of_equity + 0.01), v(p.cost_of_equity - 0.01)
    assum = {
        "roe0": round(roe0, 4), "r": p.cost_of_equity, "g": p.perpetual_growth,
        "fade_years": FADE_YEARS, "bvps": round(bvps, 2),
        "terminal": "0 (ROE se u zadnjoj godini stapa s COE — RI iščezava)",
        "equivalence_note": ("jednostupanjski RI ≡ opravdani P/B ((ROE−g)/(COE−g)); "
                             "razlika prema justified_pb_roe dolazi SAMO iz "
                             f"{FADE_YEARS}g fadea ROE→COE — konzistencijska provjera, "
                             "prava dodana vrijednost traži eksplicitne ROE forecaste"),
        "placeholder": p.placeholder,
    }
    src = {k: p.sources[k] for k in ("r", "g") if p.sources.get(k)}
    if src:
        assum["sources"] = src
    return ValueRange(lo or base, base, hi or base, assum,
                      0.7 if p.rates_calibrated else 0.5)


REGISTRY = [
    Method("multiples_relative", "Relativni multiplikatori", elig_multiples,      compute_multiples),
    Method("ev_ebitda",          "EV/EBITDA",                elig_ev_ebitda,      compute_ev_ebitda),
    Method("dcf_fcf",            "DCF (FCF)",                elig_dcf,            compute_dcf),
    Method("ddm_gordon",         "Dividendni diskont",       elig_ddm,            compute_ddm),
    Method("justified_pb_roe",   "Opravdani P/B (ROE)",      elig_justified_pb_roe, compute_justified_pb_roe),
    Method("residual_income",    "Rezidualni dohodak (RI)",  elig_residual_income, compute_residual_income),
    Method("sotp_nav",           "Sum-of-the-parts / NAV",   elig_sotp,           compute_sotp),
]


# ============================================================
#  HIJERARHIJA METODA PO ARHETIPU (M8) — NE dira eligibility.
#  Svaki arhetip deklarira SIDRO (headline fer-zona = low–high sidrenih
#  metoda) + razlog zašto sekundarne odstupaju. Sekundarne se i dalje
#  računaju i prikazuju, ali IZVAN headline zone, s razlogom odstupanja.
# ============================================================
ARCHETYPE_OF = {
    "holding": "holding",
    "bank": "capital", "insurance": "capital",
    # sve ostalo (industrial, consumer, tourism, telecom, technology...)
    # -> "operating"
}

HIERARCHY = {
    "holding": {
        "anchor": ("sotp_nav",),
        "secondary_note": ("operativna leća — mjeri maticu kroz zaradu/knjigu/"
                           "dividendu pa strukturno podcjenjuje holding čiji "
                           "udjeli imaju tržišnu cijenu"),
    },
    "capital": {
        "anchor": ("justified_pb_roe", "residual_income"),
        "secondary_note": ("sekundarna leća uz kapitalno sidro (RI / opravdani "
                           "P/B) — multipli i DDM ovise o peer skupu i politici "
                           "isplate, ne o profitabilnosti kapitala"),
    },
    "operating": {
        "anchor": ("dcf_fcf", "multiples_relative", "ev_ebitda"),
        "secondary_note": ("sekundarna leća uz operativno sidro (DCF + multipli) "
                           "— knjiga/dividenda ne mjere operativni zamah"),
    },
}


def hierarchy_for(sector: Optional[str]) -> tuple[str, dict]:
    arche = ARCHETYPE_OF.get(sector or "", "operating")
    return arche, HIERARCHY[arche]


def value_company(c: Ctx) -> dict:
    # eligibility petlja NEPROMIJENJENA — hijerarhija je sloj IZNAD rezultata
    results, skipped = {}, {}
    for m in REGISTRY:
        ok, reason = m.eligible(c)
        if ok:
            results[m.key] = {"label": m.label, "range": m.compute(c)}
        else:
            skipped[m.key] = reason          # zašto NE — ide na sajt ("SOTP n/p: ...")
    rec = reconcile(results, c.sector)
    # M11 QA: drastičan raskorak metoda ili zone vs tržišta -> red flag o
    # PRETPOSTAVKAMA (ne o tržištu); činjenica za reviziju, ne ocjena
    if rec.get("status") != "no_value":
        flags = []
        for s in rec.get("anchor_inconsistency") or []:
            flags.append(f"ULAZI NEKONZISTENTNI: {s} — uskladi pretpostavke, "
                         "ne širi zonu")
        if rec.get("dispersion_all", 0) > 0.60:
            flags.append(f"metode se međusobno razilaze {rec['dispersion_all']:.0%} "
                         "(sve metode) — provjeri ulaze/pretpostavke")
        if c.price and rec.get("zone_low") is not None:
            mid = (rec["zone_low"] + rec["zone_high"]) / 2
            gap = c.price / mid - 1 if mid else None
            if gap is not None:
                rec["vs_market_pct"] = round(gap * 100, 1)
                if abs(gap) > 0.50:
                    flags.append(f"fer-zona odstupa {gap:+.0%} od tržišta — "
                                 "mogući propust u pretpostavkama (rast, arhetip, "
                                 "jedinice) ili tržišni raskorak; tretiraj kao "
                                 "pitanje, ne zaključak")
        rec["qa_flags"] = flags
        rec["reasoning"] = _reasoning(c, results, rec)
    return {
        "ran": results,
        "skipped": skipped,
        "reconciliation": rec,
    }

def _plain_risk(flag: str) -> str:
    """QA flag -> jedna rečenica OBIČNIM jezikom (tehnički tekst ostaje u
    qa_flags; ovo je prezentacijski sloj za naraciju, ne mijenja izračun)."""
    if flag.startswith("ULAZI NEKONZISTENTNI"):
        return ("neke metode se ne slažu s glavnom procjenom — najčešće zato što "
                "dijelu ulaza još fali kalibracija (npr. multiplikatori "
                "usporedivih firmi); razliku bilježimo, ne skrivamo je")
    if flag.startswith("metode se međusobno razilaze"):
        return ("različite metode daju vrlo različite brojke — to je signal za "
                "provjeru ulaznih podataka, ne za izbor najljepše brojke")
    if flag.startswith("fer-zona odstupa"):
        return ("naša procjena je daleko od tržišne cijene — to je pitanje za "
                "provjeru pretpostavki, ne zaključak da je tržište u krivu")
    return flag


def _reasoning(c: Ctx, results: dict, rec: dict) -> str:
    """M12: ČINJENIČNI lanac zaključivanja do sidra — iz podataka, bez
    preporuke. Pisan OBIČNIM jezikom (for-dummies); tehnički izvod ostaje u
    assumptions/sources svake metode."""
    p = c.params
    gh = c.growth_hint or {}
    prim = (rec.get("anchor_methods") or [None])[0]
    parts = []
    if gh.get("forward"):
        parts.append(f"Očekivani rast {gh['g1']:+.1%} godišnje procijenjen je iz "
                     f"zadnjeg izvješća — {gh.get('drivers', 'forward signali')}"
                     + (f"; povijesni prosjek ({gh['rev_cagr_3y']:+.1%} godišnje) "
                        f"služi samo kao kontekst"
                        if gh.get("rev_cagr_3y") is not None else ""))
    elif gh.get("rev_cagr_3y") is not None:
        parts.append(f"Prihodi su zadnje tri godine rasli u prosjeku "
                     f"{gh['rev_cagr_3y']:+.1%} godišnje (izračun iz objavljenih "
                     f"izvješća; forward procjena iz backloga/guidance-a još "
                     f"nije izvedena)")
    else:
        parts.append("Stopu rasta ne možemo izračunati — u bazi još nije cijela "
                     "trogodišnja serija prihoda ni forward procjena, pa računamo "
                     "oprezno, bez faze rasta")
    rev, ebd = c.val("revenue"), c.val("ebitda")
    if rev and ebd is not None:
        parts.append(f"Od svakih 100 € prihoda firmi ostaje {ebd / rev * 100:,.0f} € "
                     f"operativne zarade (EBITDA marža {ebd / rev:.1%})")
    if prim == "sotp_nav" and prim in results:
        a = results[prim]["range"].assumptions
        sf = a.get("sotp_fair")
        if sf:
            parts.append(f"Vrijednost smo složili po dijelovima: uvrštene "
                         f"tvrtke-kćeri po našoj procjeni, neuvrštene usporedbom "
                         f"sa sličnima, minus dug grupe — ukupno "
                         f"{sf['nav_eur'] / 1e6:,.0f} M€. Burza holdinge obično "
                         f"vrednuje uz popust ({p.holding_discount_low:.0%}–"
                         f"{p.holding_discount_high:.0%}), pa je sidro "
                         f"{results[prim]['range'].base:,.2f} € po dionici")
        if a.get("market_vs_fair_pct") is not None:
            mv = a["market_vs_fair_pct"]
            parts.append(f"Tržište te iste kćeri trenutačno vrednuje "
                         f"{abs(mv):,.1f}% {'više' if mv > 0 else 'niže'} nego mi")
        risk = ("koliki popust na holding vrijedi i koliko vrijede neuvršteni "
                "dijelovi — oboje su pretpostavke")
    elif prim == "dcf_fcf" and prim in results:
        fcf = c.val("free_cash_flow")
        if fcf is None:
            ocf, capex = c.val("operating_cf"), c.val("capex")
            fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
        if fcf is not None:
            grow = (f", uz izračunati rast {gh['g1']:.1%} kroz pet godina i zatim "
                    f"dugoročni rast {p.terminal_growth:.0%}"
                    if gh.get("g1") is not None else
                    f", bez faze rasta (samo dugoročni rast {p.terminal_growth:.0%})")
            parts.append(f"Firma je lani stvorila {fcf / 1e6:,.1f} M€ slobodnog "
                         f"novca (ono što ostane nakon ulaganja). Budući novac "
                         f"vrijedi manje od današnjeg, pa ga svodimo na danas uz "
                         f"zahtijevani prinos {p.wacc:.1%}{grow} — tako izlazi "
                         f"{results[prim]['range'].base:,.2f} € po dionici")
        risk = ("procjena stoji na jednoj godini novčanog toka — jedna netipična "
                "godina može iskriviti sliku" if gh.get("g1") is None
                else "hoće li se dosadašnji tempo rasta održati sljedećih pet godina")
    elif prim in ("justified_pb_roe", "residual_income") and prim in results:
        eq, ni = c.val("equity_parent") or c.val("total_equity"), c.val("net_income_parent")
        if eq and ni is not None:
            roe, r_ = ni / eq, p.cost_of_equity
            parts.append(f"Firma ima {eq / 1e6:,.0f} M€ vlastitog kapitala "
                         f"('knjiga') i na njemu zarađuje {roe:.1%} godišnje — "
                         f"{'više' if roe > r_ else 'manje'} od {r_:.1%} koliko "
                         f"ulagač razumno traži za ovaj rizik. Kapital koji "
                         f"zarađuje {'iznad' if roe > r_ else 'ispod'} zahtjeva "
                         f"vrijedi {'više' if roe > r_ else 'manje'} od "
                         f"knjigovodstvene brojke — sidro je "
                         f"{results[prim]['range'].base:,.2f} € po dionici")
        risk = "koliko je današnja zarada na kapital održiva"
    elif prim and prim in results:
        parts.append(f"Gledali smo koliko tržište plaća slične firme po euru "
                     f"zarade i operativne dobiti te to primijenili na njezine "
                     f"brojke — sidro je {results[prim]['range'].base:,.2f} € "
                     f"po dionici")
        risk = "koliko su odabrane usporedive firme zaista usporedive"
    else:
        return "Sidro nije dostupno — vidi preskočene metode i razloge."
    alt = [f"{results[k]['label'] if k in results else k} "
           f"{v['vs_zone_pct']:+.0%}"
           for k, v in (rec.get("method_roles") or {}).items()
           if v.get("role") == "anchor_alt" and v.get("vs_zone_pct") is not None]
    if alt:
        parts.append("Kontrolne metode uz sidro: " + ", ".join(alt) +
                     " (razlog odstupanja naveden je uz svaku metodu)")
    if rec.get("qa_flags"):
        risk = _plain_risk(rec["qa_flags"][0])
    return ". ".join(parts) + f". Glavni rizik za procjenu: {risk}."


def reconcile(results: dict, sector: Optional[str] = None) -> dict:
    """
    NE bira pobjednika među SVIM metodama — ali fer-zona je sidrena arhetipom
    (M8): holding -> SOTP low–high; banka/osiguranje -> RI / opravdani P/B;
    operativna firma -> DCF + multipli. Naivni min–max svih baza bi npr. kod
    holdinga razvukao zonu operativnim lećama koje ga strukturno podcjenjuju.
    Sekundarne metode ostaju u izlazu s ulogom i razlogom odstupanja.
    (MAR-safe: prikaz metoda + objašnjenje, bez rejtinga i preporuka.)
    """
    bases = {k: r["range"].base for k, r in results.items() if r["range"].base}
    if not bases:
        return {"status": "no_value"}
    arche, h = hierarchy_for(sector)
    anchors_all = [k for k in h["anchor"] if k in bases]
    # sidro s nepozitivnom bazom (npr. DCF u godini negativnog FCF-a) ne smije
    # definirati fer-zonu — ostaje prikazano, ali izvan zone, s napomenom
    anchors = [k for k in anchors_all if bases[k] > 0]
    dropped = [k for k in anchors_all if k not in anchors]
    if anchors:
        prim = anchors[0]              # primarno sidro (redoslijed arhetipa)
        vr = results[prim]["range"]
        zone_low = vr.low or bases[prim]
        zone_high = vr.high or bases[prim]
        zone_note = (f"zona = {prim} ± osjetljivost na ključnu pretpostavku "
                     f"(r/wacc ±1 p.b.); ostala sidra su potvrda")
        if dropped:
            zone_note += (f"; isključeno (nepozitivna baza): {', '.join(dropped)}")
        anchors = [prim] + [k for k in anchors if k != prim]
    else:
        # sidro nije dostupno (npr. holding bez SOTP ulaza) -> pošten fallback
        zone_low, zone_high = min(bases.values()), max(bases.values())
        zone_note = ("sidrena metoda nije dostupna — zona je min–max svih "
                     "baza (fallback); vidi 'skipped' za razlog")
    lo_all, hi_all = min(bases.values()), max(bases.values())
    spread_all = (hi_all - lo_all) / hi_all if hi_all else 0
    # headline disperzija = širina SIDRENE zone (konsolidacija: sekundarne
    # leće su prigušene s razlogom pa NE smiju voditi "razilaze se" naraciju);
    # raspon svih metoda ostaje u izlazu kao informacija
    spread = ((zone_high - zone_low) / zone_high if zone_high else 0) \
        if anchors else spread_all

    roles = {}
    mid = (zone_low + zone_high) / 2 if anchors else None
    inconsistent = []
    for k in results.keys():
        if anchors and k == anchors[0]:
            roles[k] = {"role": "anchor", "note": None, "vs_zone_pct": None}
            continue
        if k in anchors:
            dev = (bases[k] / mid - 1) if (mid and bases.get(k)) else None
            roles[k] = {"role": "anchor_alt",
                        "note": "sidro-potvrda: ista r/rast pretpostavka, druga leća",
                        "vs_zone_pct": dev}
            if dev is not None and abs(dev) > 0.25:
                inconsistent.append(f"{k} {dev:+.0%} vs primarno sidro")
            continue
        if k in dropped:
            roles[k] = {"role": "anchor_excluded",
                        "note": ("sidrena metoda ISKLJUČENA iz zone — "
                                 "nepozitivna baza (jednogodišnji ulaz)"),
                        "vs_zone_pct": None}
            continue
        b = bases.get(k)
        if b is None:
            roles[k] = {"role": "secondary", "note": h["secondary_note"],
                        "vs_zone_pct": None}
        elif b < zone_low:
            roles[k] = {"role": "secondary", "note": h["secondary_note"],
                        "vs_zone_pct": b / zone_low - 1}
        elif b > zone_high:
            roles[k] = {"role": "secondary", "note": h["secondary_note"],
                        "vs_zone_pct": b / zone_high - 1}
        else:
            roles[k] = {"role": "secondary", "note": h["secondary_note"],
                        "vs_zone_pct": 0.0}

    return {
        "method_bases": {k: r["range"].base for k, r in results.items()},
        "archetype": arche,
        "anchor_methods": anchors,
        "method_roles": roles,
        "zone_low": zone_low, "zone_high": zone_high,
        "zone_note": zone_note,
        "all_methods_low": lo_all, "all_methods_high": hi_all,
        "anchor_inconsistency": inconsistent or None,
        "dispersion": spread,                # širina sidrene zone (headline)
        "dispersion_all": spread_all,        # raspon SVIH metoda (info/signal)
        "divergent": spread > 0.30,          # >30% SIDRA -> naracija raskoraka
    }


def class_positions(conn, ticker: str, zone_low: Optional[float],
                    zone_high: Optional[float]) -> dict:
    """M8: pozicija SVAKE klase naspram sidrene fer-zone + faktografska
    usporedba klasa (premija, dividenda, prinos). Činjenice, ne preporuke."""
    cur = conn.cursor()
    cur.execute(
        """SELECT sc.id, sc.ticker, sc.class_type, sc.is_primary_line
           FROM share_classes sc JOIN companies c ON c.id = sc.company_id
           WHERE c.ticker = %s
           ORDER BY sc.is_primary_line DESC NULLS LAST, sc.ticker""", (ticker,))
    rows = cur.fetchall()
    out = []
    for scid, tk, ctype, prim in rows:
        cur.execute(
            """SELECT close_eur, trade_date FROM prices_eod
               WHERE share_class_id=%s AND close_eur IS NOT NULL
               ORDER BY trade_date DESC LIMIT 1""", (scid,))
        r = cur.fetchone()
        price = float(r[0]) if r else None
        pdate = str(r[1]) if r else None
        cur.execute(
            """SELECT amount_eur FROM dividends
               WHERE class_ticker=%s AND div_type='Izglasana dividenda'
               ORDER BY ex_date DESC LIMIT 1""", (tk,))
        d = cur.fetchone()
        dps = float(d[0]) if d else None
        position, gap = None, None
        if price is not None and zone_low and zone_high:
            if price > zone_high:
                position, gap = "iznad", price / zone_high - 1
            elif price < zone_low:
                position, gap = "ispod", price / zone_low - 1
            else:
                position, gap = "unutar", 0.0
        out.append({
            "class_ticker": tk,
            "class_type": ctype,
            "is_primary": bool(prim),
            "price": price, "price_date": pdate,
            "dps_last_declared": dps,
            "div_yield": (dps / price) if (dps and price) else None,
            "position": position, "gap_pct": gap,
        })
    notes = []
    priced = [c for c in out if c["price"] is not None]
    if len(priced) >= 2:
        a, b = priced[0], priced[1]     # primarna vs druga klasa
        prem = a["price"] / b["price"] - 1
        notes.append(f"{a['class_ticker']} ({a['class_type']}) trguje uz "
                     f"{prem:+.1%} prema {b['class_ticker']} ({b['class_type']})")
        if a["dps_last_declared"] is not None and b["dps_last_declared"] is not None:
            if abs(a["dps_last_declared"] - b["dps_last_declared"]) < 1e-9:
                notes.append(
                    f"zadnja izglasana dividenda jednaka za obje klase "
                    f"({a['dps_last_declared']:.2f} €) -> dividendni prinos "
                    f"{a['class_ticker']} {a['div_yield']:.2%} vs "
                    f"{b['class_ticker']} {b['div_yield']:.2%}")
            else:
                notes.append(
                    f"zadnja izglasana dividenda: {a['class_ticker']} "
                    f"{a['dps_last_declared']:.2f} € vs {b['class_ticker']} "
                    f"{b['dps_last_declared']:.2f} €")
    return {
        "classes": out,
        "comparison_notes": notes,
        "mar_note": "pozicija naspram zone je činjenica iz podataka, ne preporuka",
    }


# ============================================================
#  CTX IZ BAZE  (glue: v_financials_current / v_sotp_inputs / v_shares_canonical)
# ============================================================
def build_ctx(conn, ticker: str, params: Optional[Params] = None,
              _depth: int = 0, _visited: Optional[set] = None) -> Ctx:
    params = params or Params()
    cur = conn.cursor()

    cur.execute("SELECT id, sector, is_group FROM companies WHERE ticker = %s", (ticker,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"nepoznat ticker u companies: {ticker}")
    company_id, sector, is_group = row

    def data(item: str):
        # zadnja (najnovija) annual/consolidated vrijednost + confidence iz financials
        cur.execute(
            """
            SELECT fin.value_eur, fin.confidence
            FROM   financials fin
            JOIN   filings f ON f.id = fin.filing_id
            WHERE  f.company_id = %s AND fin.item = %s
                   AND f.period_type = 'annual' AND f.basis = 'consolidated'
            ORDER BY f.fiscal_year DESC
            LIMIT 1
            """,
            (company_id, item),
        )
        r = cur.fetchone()
        return (float(r[0]) if r and r[0] is not None else None,
                float(r[1]) if r and r[1] is not None else 0.0) if r else None

    cur.execute("SELECT * FROM v_sotp_inputs WHERE parent_company_id = %s", (company_id,))
    cols = [d[0] for d in cur.description]
    holdings = [dict(zip(cols, r)) for r in cur.fetchall()]
    for h in holdings:  # numerički tipovi -> float za usporedbe
        h["ownership_pct"] = float(h["ownership_pct"]) if h["ownership_pct"] is not None else 0.0
        if h.get("default_multiple") is not None:
            h["default_multiple"] = float(h["default_multiple"])

    cur.execute("SELECT EXISTS(SELECT 1 FROM segment_financials WHERE company_id = %s)", (company_id,))
    has_segments = bool(cur.fetchone()[0])

    def shares_of(cid: int):
        cur.execute("SELECT shares_ex_treasury FROM v_shares_canonical WHERE company_id = %s", (cid,))
        r = cur.fetchone()
        if r and r[0]:
            return float(r[0])
        # fallback: shares_outstanding iz financials (KOEI nema share_classes seed)
        cur.execute(
            """SELECT fin.value_eur FROM financials fin JOIN filings f ON f.id=fin.filing_id
               WHERE f.company_id=%s AND fin.item='shares_outstanding'
               ORDER BY f.fiscal_year DESC LIMIT 1""", (cid,))
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else None

    def latest_price(cid: int):
        # kod više klasa isti dan preferiraj primarnu liniju (ADRS vs ADRS2)
        cur.execute(
            """SELECT p.close_eur FROM prices_eod p
               LEFT JOIN share_classes sc ON sc.id = p.share_class_id
               WHERE p.company_id=%s AND p.close_eur IS NOT NULL
               ORDER BY p.trade_date DESC, COALESCE(sc.is_primary_line, TRUE) DESC
               LIMIT 1""", (cid,))
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else None

    def market_cap_of(held_company_id):
        if not held_company_id:
            return None
        # precizno po KLASI: Σ zadnji close klase × dionice klase (bez trezorskih);
        # klase bez ijedne cijene obaraju rezultat u None (radije prazno nego krivo)
        cur.execute(
            """SELECT COUNT(*) FILTER (WHERE px.close_eur IS NULL) AS bez_cijene,
                      SUM(px.close_eur * (sc.shares_issued - COALESCE(sc.treasury_shares, 0)))
               FROM share_classes sc
               LEFT JOIN LATERAL (
                   SELECT close_eur FROM prices_eod p
                   WHERE p.share_class_id = sc.id AND p.close_eur IS NOT NULL
                   ORDER BY p.trade_date DESC LIMIT 1
               ) px ON TRUE
               WHERE sc.company_id = %s AND sc.shares_issued IS NOT NULL""",
            (held_company_id,))
        r = cur.fetchone()
        if r and r[1] is not None and not r[0]:
            return float(r[1])
        # fallback (firme bez share_classes): zadnja cijena × kanonske dionice
        px, n = latest_price(held_company_id), shares_of(held_company_id)
        return px * n if (px is not None and n) else None

    def segment_ebitda_of(segment_key):
        if not segment_key:
            return None
        cur.execute(
            """SELECT ebitda FROM segment_financials WHERE company_id=%s AND segment_key=%s
               ORDER BY fiscal_year DESC LIMIT 1""", (company_id, segment_key))
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else None

    # M13 (Korak 2): rast eksplicitne faze PRIMARNO iz FORWARD signala zadnjeg
    # izvješća (backlog, book-to-bill, guidance — tablica growth_estimates,
    # verified seed s citatima); trailing 3g CAGR je samo POMOĆNI kontekst i
    # fallback kad forward procjene nema. Cap [0, 20%] vrijedi za obje rute.
    rev_item = "total_operating_income" if sector == "bank" else "revenue"
    cur.execute(
        """SELECT f.fiscal_year, fin.value_eur FROM financials fin
           JOIN filings f ON f.id = fin.filing_id
           WHERE f.company_id=%s AND fin.item=%s AND f.period_type='annual'
                 AND f.basis='consolidated' AND fin.value_eur IS NOT NULL
           ORDER BY f.fiscal_year DESC LIMIT 3""", (company_id, rev_item))
    revs = cur.fetchall()
    trailing = None
    if len(revs) >= 3 and revs[-1][1] and float(revs[-1][1]) > 0:
        yrs = revs[0][0] - revs[-1][0]
        trailing = (float(revs[0][1]) / float(revs[-1][1])) ** (1 / yrs) - 1
    growth_hint = None
    try:
        cur.execute(
            """SELECT g1, rule, drivers, basis, fiscal_year FROM growth_estimates
               WHERE company_id=%s AND method='forward_signals'
               ORDER BY fiscal_year DESC, created_at DESC LIMIT 1""", (company_id,))
        fw = cur.fetchone()
    except Exception:  # noqa: BLE001 — tablica je opcionalna nadogradnja
        conn.rollback()
        fw = None
    if fw and fw[0] is not None:
        g1 = max(0.0, min(0.20, float(fw[0])))
        growth_hint = {
            "g1": round(g1, 4), "forward": True, "rule": fw[1],
            "drivers": fw[2],
            "rev_cagr_3y": round(trailing, 4) if trailing is not None else None,
            "archetype": "growth" if g1 > 0.08 else "mature",
            "source": (f"g1={g1:.1%}: FORWARD procjena iz GI FY{fw[4]} "
                       f"(pravilo {fw[1]}; {fw[2]}). {fw[3]}"
                       + (f" Trailing 3g CAGR {trailing:+.1%} je pomoćni kontekst."
                          if trailing is not None else
                          " Trailing 3g serije u bazi nema — forward je jedini signal.")),
        }
    elif trailing is not None:
        g1 = max(0.0, min(0.20, trailing))
        growth_hint = {"g1": round(g1, 4), "rev_cagr_3y": round(trailing, 4),
                       "archetype": "growth" if trailing > 0.08 else "mature",
                       "source": (f"g1={g1:.1%}: CAGR prihoda FY{revs[-1][0]}->"
                                  f"FY{revs[0][0]} iz baze (cap 0-20%) — POVIJESNI "
                                  "proxy jer forward procjena (backlog/guidance) "
                                  "još nije ekstrahirana; eksplicitna faza 5 g s "
                                  "fadeom prema terminalnom g")}

    def ni_parent_of(cid):
        cur.execute(
            """SELECT fin.value_eur FROM financials fin
               JOIN filings f ON f.id = fin.filing_id
               WHERE f.company_id=%s AND fin.item='net_income_parent'
                     AND f.period_type='annual' AND f.basis='consolidated'
               ORDER BY f.fiscal_year DESC LIMIT 1""", (cid,))
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else None

    # --- rekurzivni SOTP (Dio 0.5): fer-vrijednost UVRŠTENE kćeri iz NJENOG
    # sidra (arhetip kćeri), rekurzivno; dubina/ciklus guardovi. Ne dira
    # eligibility — koristi ga SAMO compute_sotp.
    visited = set(_visited or ()) | {ticker}

    def fair_equity_of(held_company_id):
        """-> (fair_equity_eur, opis) | None. None = kći nije analizirana
        (pozivatelj radi fallback na tržišnu vrijednost s oznakom)."""
        if not held_company_id or _depth >= 2:
            return None
        cur.execute("SELECT ticker, is_live FROM companies WHERE id=%s",
                    (held_company_id,))
        r = cur.fetchone()
        if not r or r[0] in visited or not r[1]:
            return None            # ciklus, neanaliziran ili nije live
        sub_ticker = r[0]
        try:
            from .params_calibrated import build_params  # lazy (kruženje importa)
            sub_ctx = build_ctx(conn, sub_ticker, params=build_params(sub_ticker),
                                _depth=_depth + 1, _visited=visited)
            sub_out = value_company(sub_ctx)
        except Exception:  # noqa: BLE001 — kći bez ulaza nije greška roditelja
            return None
        rec = sub_out["reconciliation"]
        if rec.get("status") == "no_value" or not rec.get("anchor_methods"):
            return None
        sh = shares_of(held_company_id)
        if not sh:
            return None
        mid = (rec["zone_low"] + rec["zone_high"]) / 2
        return (mid * sh,
                f"fer-procjena {sub_ticker}: sidro {rec['archetype']} "
                f"({', '.join(rec['anchor_methods'])}) sredina zone "
                f"{rec['zone_low']:,.0f}–{rec['zone_high']:,.0f} €/dionici × "
                f"{sh:,.0f} dionica")

    return Ctx(
        ticker=ticker, sector=sector, is_group=is_group,
        holdings=holdings, has_segments=has_segments, data=data,
        shares_ex_treasury=shares_of(company_id), price=latest_price(company_id),
        own_market_cap=market_cap_of(company_id),
        market_cap_of=market_cap_of, segment_ebitda_of=segment_ebitda_of,
        fair_equity_of=fair_equity_of, growth_hint=growth_hint,
        ni_parent_of=ni_parent_of, params=params,
    )


# ============================================================
#  CLI
# ============================================================
def _fmt(x):
    return "—" if x is None else f"{x:,.2f}"


def _print_company(ticker: str, out: dict) -> None:
    print(f"\n================  {ticker}  ================")
    rec = out["reconciliation"]
    roles = rec.get("method_roles", {}) if rec.get("status") != "no_value" else {}
    print("POKRENUTE METODE (vrijednost €/dionica: low / base / high):")
    if not out["ran"]:
        print("  (nijedna)")
    # sidrene metode prve, pa sekundarne
    ordered = sorted(out["ran"].items(),
                     key=lambda kv: 0 if roles.get(kv[0], {}).get("role") == "anchor" else 1)
    for key, r in ordered:
        vr = r["range"]
        flag = "  [bez vrijednosti — vidi 'missing']" if not vr.base else ""
        role = roles.get(key, {})
        tag = {"anchor": "[SIDRO]     ",
               "anchor_excluded": "[SIDRO-van] "}.get(role.get("role"), "[sekundarna]")
        dev = role.get("vs_zone_pct")
        devtxt = ""
        if role.get("role") == "secondary" and dev is not None:
            devtxt = (" — unutar sidrene zone" if dev == 0
                      else f" — {dev:+.0%} vs sidrena zona")
        print(f"  • {tag} {r['label']:26} {_fmt(vr.low)} / {_fmt(vr.base)} / {_fmt(vr.high)}  (conf {vr.confidence}){flag}{devtxt}")
        if role.get("note") and vr.base:
            print(f"      razlog odstupanja: {role['note']}")
        keys = {k: v for k, v in vr.assumptions.items() if k in
                ("peer_pe", "peer_pb", "peer_ev_ebitda", "r", "g", "wacc", "roe", "dps", "missing",
                 "holding_discount_range")}
        if keys:
            print(f"      pretpostavke: {keys}")
        if key == "sotp_nav" and vr.assumptions.get("parts"):
            a = vr.assumptions
            print("      SOTP BREAKDOWN (EUR):")
            for part in a["parts"]:
                ph = ("PLACEHOLDER multipla" if part["placeholder"] else
                      {"our_estimate": "NAŠA PROCJENA",
                       "market_fallback": "tržišno (kći neanalizirana)"}.get(
                          part.get("fair_basis"), "tržišno"))
                print(f"        {part['name']:20} {part['value_eur']:>15,.0f}   "
                      f"[{ph}]  {part['basis']}")
            nc = a.get("net_cash")
            if nc:
                print(f"        {'Neto novac':20} {nc['value_eur']:>15,.0f}   "
                      f"[{nc['basis']}]")
                print(f"          ({a.get('net_cash_note', '')})")
            if a.get("nav_total_eur") is not None:
                print(f"        {'NAV (prije diskonta)':20} {a['nav_total_eur']:>15,.0f}")
                sf, sm = a.get("sotp_fair"), a.get("sotp_market")
                if sf and sm:
                    print(f"        SOTP PO NAŠOJ PROCJENI: NAV {sf['nav_eur']:,.0f} "
                          f"-> {_fmt(sf['base_per_share'])} €/dionici  [sidro fer-zone]")
                    print(f"        SOTP PO TRŽIŠTU:        NAV {sm['nav_eur']:,.0f} "
                          f"-> {_fmt(sm['base_per_share'])} €/dionici")
                    if a.get("market_vs_fair_pct") is not None:
                        print(f"        SIGNAL: tržište kćeri {a['market_vs_fair_pct']:+.1f}% "
                              f"vs naša procjena ({a.get('market_vs_fair_note', '')})")
                print(f"        holding diskont {a['holding_discount_range']} — "
                      f"{a.get('holding_discount_reason', '')}")
            mc = a.get("market_check")
            if mc:
                print(f"        MARKET CHECK: vlastita trž.kap {mc['own_market_cap_eur']:,.0f} "
                      f"vs NAV {mc['nav_pre_discount_eur']:,.0f} -> cijena je "
                      f"{mc['price_vs_nav_pct']:+.1f}% vs NAV ({mc['note']})")
        src = vr.assumptions.get("sources")
        if src:
            for sk, sv in src.items():
                print(f"      IZVOR[{sk}]: {sv}")

    print("\nPRESKOČENE METODE (zašto):")
    for key, reason in out["skipped"].items():
        print(f"  • {key:20} — {reason}")

    rec = out["reconciliation"]
    print("\nRECONCILIATION (M8 — fer-zona sidrena arhetipom):")
    if rec.get("status") == "no_value":
        print("  zona: nema brojčanih vrijednosti (metode pokrenute ali bez dovoljno ulaza)")
    else:
        anchors = ", ".join(rec.get("anchor_methods") or []) or "—"
        print(f"  arhetip: {rec.get('archetype')} | sidro: {anchors}")
        print(f"  FER-ZONA €/dionica: {_fmt(rec['zone_low'])} – {_fmt(rec['zone_high'])}"
              f"  (raspon sidra, NE min–max svih metoda)")
        if rec.get("zone_note"):
            print(f"  NAPOMENA: {rec['zone_note']}")
        print(f"  disperzija SIDRA: {rec['dispersion'] * 100:.0f}% "
              f"(divergent={rec['divergent']}); sve metode (info): "
              f"{_fmt(rec.get('all_methods_low'))} – {_fmt(rec.get('all_methods_high'))} "
              f"(raspon {rec.get('dispersion_all', 0) * 100:.0f}%)")
        print(f"  baze po metodi: { {k: round(v, 2) for k, v in rec['method_bases'].items() if v} }")
        for f in rec.get("qa_flags") or []:
            print(f"  QA RED-FLAG: {f}")
        if rec.get("reasoning"):
            print(f"  LANAC: {rec['reasoning']}")


def _print_class_positions(cp: dict) -> None:
    print("\nKLASE NASPRAM FER-ZONE (činjenice, ne preporuke):")
    for c in cp["classes"]:
        if c["price"] is None:
            print(f"  • {c['class_ticker']:6} ({c['class_type']}): nema cijene u bazi")
            continue
        pos = ("nema zone" if c["position"] is None else
               "unutar zone" if c["position"] == "unutar" else
               f"{abs(c['gap_pct']):.1%} {c['position']} zone")
        dy = f", prinos {c['div_yield']:.2%}" if c["div_yield"] else ""
        dps = (f", zadnja izglasana dividenda {c['dps_last_declared']:.2f} €"
               if c["dps_last_declared"] is not None else "")
        print(f"  • {c['class_ticker']:6} ({c['class_type']}, "
              f"{'primarna' if c['is_primary'] else 'druga linija'}): "
              f"{c['price']:,.2f} € ({c['price_date']}) -> {pos}{dps}{dy}")
    for n in cp["comparison_notes"]:
        print(f"  ↔ {n}")
    print(f"  [{cp['mar_note']}]")


def _print_sensitivity(ticker: str, conn, base_params: Params) -> None:
    """Osjetljivost na r ±1%: ponovno izračunaj r-ovisne metode; SOTP r ne koristi."""
    import copy
    print(f"\n--- OSJETLJIVOST {ticker} na r ±1% (r_base={base_params.cost_of_equity:.4f}) ---")
    rows = {}
    for dr in (-0.01, 0.0, +0.01):
        p = copy.deepcopy(base_params)
        p.cost_of_equity = base_params.cost_of_equity + dr
        ctx = build_ctx(conn, ticker, params=p)
        out = value_company(ctx)
        for k in ("justified_pb_roe", "ddm_gordon", "sotp_nav"):
            if k in out["ran"]:
                rows.setdefault(k, {})[dr] = out["ran"][k]["range"].base
    for k, v in rows.items():
        if len(set(round(x, 4) for x in v.values())) == 1:
            print(f"  {k:18}: {_fmt(v.get(0.0))} — NEOSJETLJIV na r "
                  f"(metoda ne koristi r; SOTP = tržišne cijene + multiple, "
                  f"osjetljivost mu je na holding diskont: vidi low/high raspon)")
        else:
            print(f"  {k:18}: r-1%: {_fmt(v.get(-0.01))}  |  r: {_fmt(v.get(0.0))}  "
                  f"|  r+1%: {_fmt(v.get(0.01))}")


def main(argv=None) -> int:
    import sys
    args = list(argv if argv is not None else sys.argv[1:])
    sensitivity = "--sensitivity" in args
    if sensitivity:
        args.remove("--sensitivity")
    tickers = args or ["ADRS", "CROS"]

    from .db import get_conn
    from .params_calibrated import build_params
    with get_conn() as conn:
        for t in tickers:
            try:
                params = build_params(t)
                ctx = build_ctx(conn, t, params=params)
            except ValueError as e:
                print(f"\n================  {t}  ================\n  GREŠKA: {e}")
                continue
            out = value_company(ctx)
            _print_company(t, out)
            rec = out["reconciliation"]
            if rec.get("status") != "no_value":
                _print_class_positions(
                    class_positions(conn, t, rec["zone_low"], rec["zone_high"]))
            if sensitivity:
                _print_sensitivity(t, conn, params)
    print("\nNAPOMENA: r i g su kalibrirani (CAPM; izvori uz svaku metodu). Peer multipli: "
          "ADRS iz baze (medijan), CROS placeholder (nema usporedivog osiguratelja na ZSE). "
          "Beta=1,0, holding diskont i multiple neuvrštenih ostaju OZNAČENE pretpostavke.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
