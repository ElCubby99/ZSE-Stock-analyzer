"""Kalibrirani Params (M3): r (CAPM), g, peer multipli IZ BAZE, holding diskont.

Svaka komponenta nosi IZVOR/OBRAZLOŽENJE (ide u assumptions -> na sajt).
Pravilo: bez izvora -> ostaje placeholder (i niži confidence), ne izmišlja se.

Komponente (stanje 2026-07-03):
  rf   = 3,61%  — prinos HR 10g državne obveznice, TradingEconomics (sredina
         2026, "najviše od prosinca 2023", +47bp y/y). Cross-check sa ZSE:
         RHMF-O-357A (kupon 3,00%, dosp. 04.07.2035) zadnji close 100,50 na
         02.01.2026 -> YTM ~2,94% — konzistentno starije (prinosi otad rasli);
         ZSE obveznice su preslabo likvidne za primarni izvor.
  ERP  = 5,7%   — Damodaranova metodologija, tablica siječanj 2026: zreli ERP
         4,23% + CRP za Moody's A3 (Hrvatska A3 stabilno od 11/2024, potvrđeno
         2026). A3 EU zemlje (Portugal) u bandi 5,0–5,8%. Točan HR redak
         NEPROVJEREN (stern.nyu.edu blokiran egress politikom) -> vrijednost
         označena erp_exact_unverified.
  beta = 1,0    — PRETPOSTAVKA (nema pouzdane procjene: u bazi su 2 dana
         cijena; beta traži povijesnu seriju). Eksplicitno označeno.
  r    = rf + beta×ERP = 9,31% (ADRS i CROS — ista beta pretpostavka).
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

RF = 0.0361
RF_SRC = ("rf=3,61%: HR 10g državna obveznica, TradingEconomics "
          "(tradingeconomics.com/croatia/government-bond-yield, sredina 2026); "
          "cross-check ZSE RHMF-O-357A YTM~2,94% @ close 100,50 (zadnja trgovina "
          "02.01.2026 — nelikvidno, starije od rasta prinosa)")

ERP = 0.057
ERP_SRC = ("ERP=5,7%: Damodaran (pages.stern.nyu.edu, tablica siječanj 2026): "
           "zreli ERP 4,23% + CRP za Moody's A3 (HR A3 stabilno, Moody's 11/2024); "
           "A3 EU zemlje (Portugal) u bandi 5,0–5,8% (germanpedia.com/eu-equity-"
           "risk-premiums). TOČAN HR REDAK NEPROVJEREN (egress 403) — "
           "erp_exact_unverified=true")

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
         "g<r zadovoljeno (min r ~7,2%)")

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
    r = RF + beta * ERP + illiq_premium

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
        "r": (f"r={r:.4f} (CAPM: rf + beta×ERP"
              + (f" + premija nelikvidnosti {illiq_premium * 100:.1f} p.b."
                 if illiq_premium else "")
              + f"). {RF_SRC}. {ERP_SRC}. {beta_src}"
              + (f" {illiq_src}" if illiq_src else "")),
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
