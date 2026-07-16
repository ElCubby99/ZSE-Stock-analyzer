"""Kalibrirani Params (M3, v3 FAZA K): r (CAPM raspis), g, peer multipli IZ
BAZE, holding diskont.

Svaka komponenta nosi IZVOR/OBRAZLOŽENJE (ide u assumptions -> na sajt).
Pravilo: bez izvora -> ostaje placeholder (i niži confidence), ne izmišlja se.

Komponente (v3 FAZA K, stanje 2026-07-16) — r = rf + β×ERP + CRP + nelikv.:
  rf   = 2,70%  — 10g njemački Bund (EUR bezrizični). IZBOR (dokumentiran):
         Bund umjesto HR 10g krivulje, jer HR 10g (~3,6%) nosi hrvatski
         spread — rizik zemlje mora živjeti SAMO u CRP-u (do FAZE K bio je
         naplaćen dvaput: u rf i u ERP-u; docs/forenzika_v3_faza_d.md §5).
         Ručni unos s datumom, rf_exact_unverified.
  ERP  = 4,23%  — Damodaranov ZRELI ERP (siječanj 2026), BEZ premije zemlje.
         erp_exact_unverified (egress blokiran).
  CRP  = 1,2 p.b. — zasebna, MALA premija zemlje primjerena 'A-'/A3
         investment-grade eurozoni (strop metodologije v3: ≤1,5 p.b.);
         dodaje se ravno na r, ne množi se betom. crp_exact_unverified.
  beta — po Z1 disciplini (regresija+Blume iznad praga likvidnosti,
         sektorska ispod; clamp [0,7, 1,8]).
  r(β=1) = 2,70 + 4,23 + 1,2 = 8,13% (prije: 9,31% s dvostrukim countom).
  g    = 2,0%   — ECB-ov inflacijski cilj (HR u eurozoni od 2023) kao
         konzervativna donja granica dugoročnog NOMINALNOG rasta; realno
         hrvatski nominalni BDP raste brže, ali perpetuitet ne smije
         ekstrapolirati ciklus. g < r zadovoljeno.
  peer multipli — MEDIJAN IZ BAZE (src/peer_multiples.py, ništa prepisano):
         ADRS skup {ATGR, PODR, RIVP, PLAG, ARNT} (docs/peers.md; nijedan
         isključen — svi profitabilni, konzumeri+turizam pokrivaju ADRS-ov
         konglomeratski profil). CROS: na ZSE NEMA usporedivog osiguratelja
         (docs/peers.md) -> peer multipli za CROS OSTAJU placeholder.
  holding diskont 15–25% — pretpostavka + TRŽIŠNA USPOREDBA koju compute_sotp
         upisuje u assumptions (market_check: vlastita trž.kap vs NAV);
         povijesni diskont neizvediv iz baze (2 dana cijena).
"""
from __future__ import annotations

from .valuation_methods import Params

# --- v3 FAZA K: r = rf + β×ERP(zreli) + CRP + nelikvidnost -----------------
# Rizik zemlje živi ISKLJUČIVO u CRP-u (jedan put, vidljivo). Do FAZE K je
# bio naplaćen dvaput: u rf (HR 10g nosi HR spread) i u ERP-u (5,7% = zreli
# 4,23% + A3 CRP) — vidi docs/forenzika_v3_faza_d.md §5.
RF = 0.0270
RF_SRC = ("rf=2,70%: 10g njemački Bund (EUR bezrizični), ručni unos "
          "16.07.2026 — rf_exact_unverified=true (tržišni izvori nedostupni "
          "iz build okruženja; ista praksa kao ERP). IZBOR Bunda umjesto HR "
          "10g krivulje (v3 FAZA K): HR 10g (~3,6% sredinom 2026.) nosi "
          "hrvatski spread naspram Bunda — taj rizik zemlje sada eksplicitno "
          "i SAMO JEDNOM živi u zasebnom CRP-u, ne u rf-u")

ERP = 0.0423
ERP_SRC = ("ERP=4,23%: Damodaranov ZRELI (mature-market implied) ERP, "
           "tablica siječanj 2026 (pages.stern.nyu.edu); BEZ premije zemlje "
           "— CRP je zasebna komponenta (v3 FAZA K, zabranjen dvostruki "
           "count). TOČAN REDAK NEPROVJEREN (egress 403) — "
           "erp_exact_unverified=true")

CRP = 0.012
CRP_SRC = ("CRP=1,2 p.b.: hrvatska premija rizika zemlje kao ZASEBNA, mala "
           "komponenta primjerena investment-grade eurozoni — Moody's A3 "
           "(stabilno, 11/2024), S&P/Fitch 'A-'; Damodaranov rejting-band za "
           "A3/A- ~1,2–1,5 p.b., uzet donji dio banda uz strop ≤1,5 p.b. iz "
           "metodologije v3; ručni unos 16.07.2026 — "
           "crp_exact_unverified=true. Dodaje se ravno na r (ne množi se "
           "betom); stari CRP-ovi za pred-eurozonsku Hrvatsku ne vrijede")

BETA = 1.0
BETA_SRC = ("beta=1,0: PRETPOSTAVKA — za ovu firmu nema kalibrirane bete "
            "(serija prekratka/nelikvidna ili kalibracija nije pokrenuta); "
            "korištena je neutralna tržišna beta")


def _calibration(key: str):
    """Učitaj kalibraciju iz baze (M10); bez baze/retka -> None (fallback)."""
    try:
        from .db import get_conn
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT value FROM calibrations WHERE key=%s", (key,))
            r = cur.fetchone()
            return r[0] if r else None
    except Exception:  # noqa: BLE001 — kalibracija je opcionalna nadogradnja
        return None

G = 0.025
G_TERMINAL = 0.04
G_SRC = ("M11 dvorazinski g: TERMINAL g=4,0% za DCF/DDM (nominalni BDP proxy: "
         "realni ~2% + inflacija ~2%) uz EKSPLICITNU fazu rasta g1 iz 3g CAGR-a "
         "prihoda IZ BAZE (cap 0-20%, fade 5 g); kapitalni g=2,5% za opravdani "
         "P/B i RI (konzervativniji — kapital ne smije perpetuirati ciklus); "
         "g<r zadovoljeno (min r ~6,9% uz β=0,7 po v3 K-stacku)")

DISCOUNT_SRC = ("holding diskont 15–25%: empirijski raspon za europske holdinge "
                "(nelikvidnost, dvostruko oporezivanje, trošak centra); "
                "OSTAJE PRETPOSTAVKA — postupak kalibracije opisan u Metodologiji")

ADRS_PEERS = ["ATGR", "PODR", "RIVP", "PLAG", "ARNT"]

# Korak 1 audita (M13): sektorski peer skupovi UNUTAR praćenog univerzuma
# (kriteriji i obrazloženje: docs/peers.md — bez cirkularnosti: društva pod
# kontrolom subjekta vrednovanja nisu peeri; KODT i DLKV su obje KOEI-jeve
# kćeri ali NE kontroliraju jedna drugu pa su međusobno dopuštene).
# Tickeri BEZ skupa (CROS, HT, SPAN, ZABA, KOEI...) ostaju placeholder,
# a multipl-metode tada nose NISKU pouzdanost (vidi _peer_confidence).
PEER_SETS = {
    "ADRS": ADRS_PEERS,
    # konzumeri
    "ATGR": ["PODR", "ZITO", "TOK"],
    "PODR": ["ATGR", "ZITO", "TOK"],
    "ZITO": ["ATGR", "PODR", "TOK"],
    "TOK": ["ATGR", "PODR", "ZITO"],
    # industrija
    "KOEI": ["ADPL", "IG"],  # bez KODT/DLKV (cirkularnost: njegove kćeri); uski skup
    "KODT": ["ADPL", "DLKV", "IG"],
    "ADPL": ["KODT", "DLKV", "IG"],
    "DLKV": ["KODT", "ADPL", "IG"],
    "IG": ["KODT", "ADPL", "DLKV"],
    # turizam (MAIS uključen otkad ima validirane financije, M14)
    "RIVP": ["PLAG", "ARNT", "MAIS"],
    "PLAG": ["RIVP", "ARNT", "MAIS"],
    "ARNT": ["RIVP", "PLAG", "MAIS"],
    "MAIS": ["RIVP", "PLAG", "ARNT"],
}


def build_params(ticker: str) -> Params:
    """Params s kalibriranim r/g za sve; beta kroz DISCIPLINU (Z1):
    prag likvidnosti -> regresija+Blume ILI sektorska (relevered), clamp
    [0,7, 1,8], premija nelikvidnosti kao zasebna komponenta r-a."""
    beta, beta_src, beta_cal = BETA, BETA_SRC, False
    beta_origin, illiq_premium, illiq_src = "pretpostavka", 0.0, None
    try:
        from .beta_discipline import resolve_beta
        from .db import get_conn
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT sector FROM companies WHERE ticker=%s", (ticker,))
            row = cur.fetchone()
            bd = resolve_beta(conn, ticker, row[0] if row else None)
        beta, beta_src, beta_origin = bd["beta"], bd["src"], bd["origin"]
        beta_cal = bd["origin"] == "regresija"
        illiq_premium, illiq_src = bd["illiq_premium"], bd["illiq_src"]
    except Exception:  # noqa: BLE001 — bez baze: stari fallback (β=1, bez premije)
        pass
    # v3 FAZA K: rizik zemlje SAMO u CRP-u (rf je EUR bezrizični, ERP zreli)
    r = RF + beta * ERP + CRP + illiq_premium

    disc_src = DISCOUNT_SRC
    dc = _calibration("holding_discount:ADRS") if ticker == "ADRS" else None
    pnav_measured = None
    if dc:
        # doktrina v2 §4: IZMJERENI vlastiti P/NAV zamjenjuje default;
        # serija (M10): diskont d = 1 − cijena/NAV proxy -> P/NAV = 1 − d.
        # Negativan d (premija) se u diskontu KLAMPA na 0 (premija se ne
        # ugrađuje u fer — konzervativno), uz punu oznaku ograničenja proxyja.
        pnav_measured = {
            "median": round(1 - dc["median"], 3),
            "p25": round(1 - dc["p75"], 3),   # veći diskont -> niži P/NAV
            "p75": round(1 - dc["p25"], 3),
            "note": (f"serija M10 ({dc['period']}, n={dc['n_days']} d) na "
                     f"KONZERVATIVNOM NAV proxyju (neuvršteni dijelovi na "
                     f"placeholder multiplama, grupni neto dug konstantan); "
                     f"opažena PREMIJA se klampa na diskont 0 — premija se ne "
                     f"ugrađuje u fer (v2 §4)"),
        }
        disc_src = (
            f"IZMJERENI vlastiti P/NAV (v2 §4): medijan {pnav_measured['median']:.2f} "
            f"(p25 {pnav_measured['p25']:.2f}, p75 {pnav_measured['p75']:.2f}), "
            f"zadnje {1 - dc['latest']:.2f} ({dc['latest_date']}). "
            f"{pnav_measured['note']}")

    sources = {
        "r": (f"r={r:.4f} = rf {RF:.2%} + β {beta:.2f}×ERP {ERP:.2%} + CRP "
              f"{CRP * 100:.1f} p.b."
              + (f" + premija nelikvidnosti {illiq_premium * 100:.1f} p.b."
                 if illiq_premium else "")
              + f" (v3 FAZA K raspis). {RF_SRC}. {ERP_SRC}. {CRP_SRC}. {beta_src}"
              + (f" {illiq_src}" if illiq_src else "")),
        "rf": RF_SRC,
        "erp": ERP_SRC,
        "crp": CRP_SRC,
        "g": G_SRC,
        "wacc": ("wacc≈r (pretpostavka strukture bez duga na razini metode; "
                 "DCF ionako gate-an za ADRS/CROS)"),
        "holding_discount": disc_src,
    }
    p = Params(cost_of_equity=r, perpetual_growth=G, wacc=r,
               terminal_growth=G_TERMINAL)
    p.rates_calibrated = True
    p.beta_calibrated = beta_cal
    p.beta = beta  # numerički, samo za prikaz (for-dummies kartica pretpostavki)
    p.beta_origin = beta_origin      # Z1: badge porijekla (regresija/sektorska/clamp)
    p.illiq_premium = illiq_premium  # Z1: zasebna komponenta r-a
    p.illiq_src = illiq_src
    # v3 FAZA K: komponente r-a za raspis u UI (rf + β×ERP + CRP + nelikv.)
    p.rf = RF
    p.erp = ERP
    p.crp = CRP
    if pnav_measured:
        p.pnav_measured = pnav_measured  # v2 §4: izmjereni P/NAV za SOTP diskont
    p.sources = sources

    p.peers_narrow = False
    peer_set = PEER_SETS.get(ticker)
    if peer_set:
        from .peer_multiples import derive  # medijan IZ BAZE, ne prepisan
        res = derive(peer_set)
        m = res["median"]
        rows = "; ".join(
            f"{x['ticker']} P/E={x.get('pe') and round(x['pe'], 2)} "
            f"P/B={x.get('pb') and round(x['pb'], 2)}"
            for x in res["rows"] if not x.get("skip"))
        if m["pe"] and m["pe_n"] >= 2 and m["pb"] and m["pb_n"] >= 2:
            p.peer_pe = round(m["pe"], 2)
            p.peer_pb = round(m["pb"], 2)
            if m["ev_ebitda"] and m["ev_ebitda_n"] >= 2:
                p.peer_ev_ebitda = round(m["ev_ebitda"], 2)
            p.peers_calibrated = True
            p.peers_narrow = min(m["pe_n"], m["pb_n"]) < 3
            # ROE peera: P/B leća se skalira omjerom ROE (P/B je funkcija ROE)
            if m.get("roe"):
                p.peer_roe = round(m["roe"], 4)
            if m.get("ev_ebit") and m["ev_ebit_n"] >= 2:
                p.peer_ev_ebit = round(m["ev_ebit"], 2)  # doktrina v2: EV/EBIT leća
            narrow_note = (" USKI SKUP (n=2) -> snižena pouzdanost multipl-metoda."
                           if p.peers_narrow else "")
            sources["peers"] = (
                f"peer multipli = MEDIJAN iz baze (zadnje cijene + zadnje godišnje "
                f"kons. financije): P/E={p.peer_pe} (n={m['pe_n']}), P/B={p.peer_pb} "
                f"(n={m['pb_n']}), EV/EBITDA={p.peer_ev_ebitda} "
                f"(n={m['ev_ebitda_n']}). Skup {peer_set} (kriteriji odabira u "
                f"Metodologiji; sektorski skup unutar praćenog univerzuma, "
                f"bez cirkularnosti)."
                f"{narrow_note} Po peeru: {rows}")
        else:
            sources["peers"] = (f"peer skup {peer_set} nedovoljno pokriven "
                                f"(P/E n={m['pe_n']}, P/B n={m['pb_n']}; treba n>=2) "
                                "-> multipli OSTAJU placeholder, multipl-metode "
                                "NISKE pouzdanosti")
    else:
        sources["peers"] = (f"{ticker}: peer skup nije kalibriran — na ZSE nema "
                            "dovoljno usporedivih firmi u sektoru (kriteriji "
                            "odabira peera opisani u Metodologiji; regionalni "
                            "peeri se ne koriste) -> peer multipli OSTAJU "
                            "placeholder (P/E 12, P/B 1,5), a multipl-metode "
                            "nose NISKU pouzdanost (0,3)")

    # master flag: placeholder samo ako su i stope i peeri placeholder
    p.placeholder = not (p.rates_calibrated and p.peers_calibrated)
    return p
