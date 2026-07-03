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
    perpetual_growth: float = 0.02    # PLACEHOLDER g (terminalni rast)
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


def compute_multiples(c: Ctx) -> ValueRange:
    """P/E i P/B leća: vrijednost/dionica = peer_multiple × (zarada matice | knjiga matice) / dionice."""
    p = c.params
    ni = c.val("net_income_parent")
    eq = c.val("equity_parent") or c.val("total_equity")
    lenses, assum = [], {"placeholder": p.placeholder}
    if ni is not None:
        pe_ps = _per_share(p.peer_pe * ni, c)
        if pe_ps is not None:
            lenses.append(pe_ps); assum["peer_pe"] = p.peer_pe
    if eq is not None:
        pb_ps = _per_share(p.peer_pb * eq, c)
        if pb_ps is not None:
            lenses.append(pb_ps); assum["peer_pb"] = p.peer_pb
    if not lenses:
        return _missing(c, "net_income_parent|equity_parent", "shares_ex_treasury")
    if p.sources.get("peers"):
        assum["sources"] = {"peers": p.sources["peers"]}
    base = sum(lenses) / len(lenses)
    return ValueRange(base * (1 - p.band), base, base * (1 + p.band), assum,
                      0.7 if p.peers_calibrated else 0.5)


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
    return ValueRange(lo, base, hi, assum, 0.7 if p.peers_calibrated else 0.5)


def compute_dcf(c: Ctx) -> ValueRange:
    """Pojednostavljeni jednofazni DCF: EV = FCF×(1+g)/(wacc−g); equity = EV − net_dug; /dionice."""
    p = c.params
    fcf = c.val("free_cash_flow")
    if fcf is None:
        ocf, capex = c.val("operating_cf"), c.val("capex")
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
    if fcf is None:
        return _missing(c, "free_cash_flow|operating_cf+capex")
    net_debt = c.val("net_debt") or 0.0
    def ps(wacc):
        if wacc <= p.perpetual_growth:
            return None
        ev = fcf * (1 + p.perpetual_growth) / (wacc - p.perpetual_growth)
        return _per_share(ev - net_debt, c)
    base = ps(p.wacc)
    if base is None:
        return _missing(c, "shares_ex_treasury|wacc>g")
    lo, hi = ps(p.wacc + 0.01), ps(p.wacc - 0.01)   # viši diskont => niža vrijednost
    assum = {"wacc": p.wacc, "g": p.perpetual_growth, "model": "jednofazni Gordon (pojednostavljeno)",
             "placeholder": p.placeholder}
    src = {k: p.sources[k] for k in ("wacc", "g") if p.sources.get(k)}
    if src:
        assum["sources"] = src
    return ValueRange(lo or base, base, hi or base, assum,
                      0.6 if p.rates_calibrated else 0.4)


def compute_ddm(c: Ctx) -> ValueRange:
    """Gordon: vrijednost/dionica = DPS×(1+g)/(r−g)."""
    p = c.params
    dps = c.val("dps")
    if dps is None:
        return _missing(c, "dps")
    def v(r):
        return dps * (1 + p.perpetual_growth) / (r - p.perpetual_growth) if r > p.perpetual_growth else None
    base = v(p.cost_of_equity)
    if base is None:
        return _missing(c, "r>g")
    lo, hi = v(p.cost_of_equity + 0.01), v(p.cost_of_equity - 0.01)
    assum = {"dps": dps, "r": p.cost_of_equity, "g": p.perpetual_growth, "placeholder": p.placeholder}
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
    gross, parts, missing = 0.0, [], []
    for h in c.holdings:
        pct = h["ownership_pct"]
        if h["valuation_basis"] == "market":
            mc = c.market_cap_of(h["held_company_id"]) if (c.market_cap_of and h.get("held_company_id")) else None
            if mc is None:
                missing.append(f"trž.kap({h['held_name']})"); continue
            stake = mc * pct
            basis = f"market: trž.kap {mc:,.0f} × {pct:.4f}"
            is_placeholder = False
        elif h["valuation_basis"] == "ebitda_multiple":
            seg = c.segment_ebitda_of(h["segment_key"]) if (c.segment_ebitda_of and h.get("segment_key")) else None
            if seg is None:
                missing.append(f"segment_ebitda({h['segment_key']})"); continue
            stake = seg * (h["default_multiple"] or 0) * pct
            basis = (f"ebitda_multiple: {seg:,.0f} [{h['segment_key']}] "
                     f"× {h['default_multiple']} × {pct:.2f}")
            is_placeholder = True  # default_multiple je pretpostavka
        else:
            missing.append(f"{h['valuation_basis']}({h['held_name']})"); continue
        gross += stake
        parts.append({"name": h["held_name"], "value_eur": round(stake, 0),
                      "basis": basis, "pct": pct, "placeholder": is_placeholder})
    assum["parts"] = parts
    if missing:
        assum["missing"] = missing
        # Nedostaju ulazi (cijene/segmenti) => ne proizvodi vrijednost, radije prazno nego izmišljeno.
        return ValueRange(0, 0, 0, assum, 0.0)
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
    lo = _per_share(nav * (1 - p.holding_discount_high), c)
    base = _per_share(nav * (1 - (p.holding_discount_low + p.holding_discount_high) / 2), c)
    hi = _per_share(nav * (1 - p.holding_discount_low), c)
    if base is None:
        assum["missing"] = ["shares_ex_treasury"]
        return ValueRange(0, 0, 0, assum, 0.0)
    assum["nav_gross_eur"] = round(gross, 0)
    assum["nav_total_eur"] = round(nav, 0)
    if p.sources.get("holding_discount"):
        assum["sources"] = {"holding_discount": p.sources["holding_discount"]}
    # TRŽIŠNA USPOREDBA (dokaz uz diskont): vlastita trž.kap vs NAV prije diskonta
    if c.own_market_cap and nav:
        prem = c.own_market_cap / nav - 1
        assum["market_check"] = {
            "own_market_cap_eur": round(c.own_market_cap, 0),
            "nav_pre_discount_eur": round(nav, 0),
            "price_vs_nav_pct": round(prem * 100, 1),
            "note": ("tekuća cijena vs OVAJ (konzervativni) NAV; povijesni "
                     "diskont neizvediv iz baze — premalo dana cijena"),
        }
    # confidence: većina NAV-a iz tržišnih cijena -> 0.6; inače 0.5.
    market_share = (sum(x["value_eur"] for x in parts if not x["placeholder"]) / gross) if gross else 0
    assum["market_based_share_of_gross"] = round(market_share, 2)
    return ValueRange(lo, base, hi, assum, 0.6 if market_share >= 0.7 else 0.5)


REGISTRY = [
    Method("multiples_relative", "Relativni multiplikatori", elig_multiples,      compute_multiples),
    Method("ev_ebitda",          "EV/EBITDA",                elig_ev_ebitda,      compute_ev_ebitda),
    Method("dcf_fcf",            "DCF (FCF)",                elig_dcf,            compute_dcf),
    Method("ddm_gordon",         "Dividendni diskont",       elig_ddm,            compute_ddm),
    Method("justified_pb_roe",   "Opravdani P/B (ROE)",      elig_justified_pb_roe, compute_justified_pb_roe),
    Method("sotp_nav",           "Sum-of-the-parts / NAV",   elig_sotp,           compute_sotp),
]


# ============================================================
#  ORKESTRACIJA + RECONCILIATION  (raskorak metoda = signal)
#  >>> NEPROMIJENJENO <<<
# ============================================================
def value_company(c: Ctx) -> dict:
    results, skipped = {}, {}
    for m in REGISTRY:
        ok, reason = m.eligible(c)
        if ok:
            results[m.key] = {"label": m.label, "range": m.compute(c)}
        else:
            skipped[m.key] = reason          # zašto NE — ide na sajt ("SOTP n/p: ...")
    return {
        "ran": results,
        "skipped": skipped,
        "reconciliation": reconcile(results),
    }

def reconcile(results: dict) -> dict:
    """
    NE bira pobjednika. Grupira baze, mjeri disperziju, OZNAČAVA raskorak.
    Naraciju raskoraka generira model (jedina prosudba) uz STROG prompt:
    'Objasni ZAŠTO se metode razilaze koristeći SAMO brojke iz konteksta;
     ne preporučuj kupnju/prodaju.' (MAR-safe: prikaz metoda + objašnjenje, bez rejtinga.)
    """
    bases = [r["range"].base for r in results.values() if r["range"].base]
    if not bases:
        return {"status": "no_value"}
    lo, hi = min(bases), max(bases)
    spread = (hi - lo) / hi if hi else 0
    return {
        "method_bases": {k: r["range"].base for k, r in results.items()},
        "zone_low": lo, "zone_high": hi,
        "dispersion": spread,
        "divergent": spread > 0.30,          # >30% raspon -> traži naraciju raskoraka
        # primjer ADRS: justified_pb_roe ~55–74 vs sotp ~95–120 -> divergent=True
        #   -> model objasni: čisti P/B podcjenjuje jer ne hvata trž. vrijednost uvrštenih udjela
    }


# ============================================================
#  CTX IZ BAZE  (glue: v_financials_current / v_sotp_inputs / v_shares_canonical)
# ============================================================
def build_ctx(conn, ticker: str, params: Optional[Params] = None) -> Ctx:
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

    return Ctx(
        ticker=ticker, sector=sector, is_group=is_group,
        holdings=holdings, has_segments=has_segments, data=data,
        shares_ex_treasury=shares_of(company_id), price=latest_price(company_id),
        own_market_cap=market_cap_of(company_id),
        market_cap_of=market_cap_of, segment_ebitda_of=segment_ebitda_of, params=params,
    )


# ============================================================
#  CLI
# ============================================================
def _fmt(x):
    return "—" if x is None else f"{x:,.2f}"


def _print_company(ticker: str, out: dict) -> None:
    print(f"\n================  {ticker}  ================")
    print("POKRENUTE METODE (vrijednost €/dionica: low / base / high):")
    if not out["ran"]:
        print("  (nijedna)")
    for key, r in out["ran"].items():
        vr = r["range"]
        flag = "  [bez vrijednosti — vidi 'missing']" if not vr.base else ""
        print(f"  • {r['label']:26} {_fmt(vr.low)} / {_fmt(vr.base)} / {_fmt(vr.high)}  (conf {vr.confidence}){flag}")
        keys = {k: v for k, v in vr.assumptions.items() if k in
                ("peer_pe", "peer_pb", "peer_ev_ebitda", "r", "g", "wacc", "roe", "dps", "missing",
                 "holding_discount_range")}
        if keys:
            print(f"      pretpostavke: {keys}")
        if key == "sotp_nav" and vr.assumptions.get("parts"):
            a = vr.assumptions
            print("      SOTP BREAKDOWN (EUR):")
            for part in a["parts"]:
                ph = "PLACEHOLDER multipla" if part["placeholder"] else "tržišno"
                print(f"        {part['name']:20} {part['value_eur']:>15,.0f}   "
                      f"[{ph}]  {part['basis']}")
            nc = a.get("net_cash")
            if nc:
                print(f"        {'Neto novac':20} {nc['value_eur']:>15,.0f}   "
                      f"[{nc['basis']}]")
                print(f"          ({a.get('net_cash_note', '')})")
            if a.get("nav_total_eur") is not None:
                print(f"        {'NAV (prije diskonta)':20} {a['nav_total_eur']:>15,.0f}")
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
    print("\nRECONCILIATION:")
    if rec.get("status") == "no_value":
        print("  zona: nema brojčanih vrijednosti (metode pokrenute ali bez dovoljno ulaza)")
    else:
        print(f"  zona €/dionica: {_fmt(rec['zone_low'])} – {_fmt(rec['zone_high'])}  "
              f"(disperzija {rec['dispersion']*100:.0f}%, divergent={rec['divergent']})")
        print(f"  baze po metodi: { {k: round(v,2) for k,v in rec['method_bases'].items()} }")


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
            _print_company(t, value_company(ctx))
            if sensitivity:
                _print_sensitivity(t, conn, params)
    print("\nNAPOMENA: r i g su kalibrirani (CAPM; izvori uz svaku metodu). Peer multipli: "
          "ADRS iz baze (medijan), CROS placeholder (nema usporedivog osiguratelja na ZSE). "
          "Beta=1,0, holding diskont i multiple neuvrštenih ostaju OZNAČENE pretpostavke.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
