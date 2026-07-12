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
            "vidi src/calibrate.py")


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

G = 0.02
G_SRC = ("g=2,0%: ECB inflacijski cilj (HR u eurozoni) kao konzervativan "
         "perpetualni nominalni rast; namjerno ispod povijesnog nominalnog "
         "rasta BDP-a; g<r zadovoljeno")

DISCOUNT_SRC = ("holding diskont 15–25%: empirijski raspon za europske holdinge "
                "(nelikvidnost, dvostruko oporezivanje, trošak centra); "
                "OSTAJE PRETPOSTAVKA — vidi docs/calibration.md")

ADRS_PEERS = ["ATGR", "PODR", "RIVP", "PLAG", "ARNT"]


def build_params(ticker: str) -> Params:
    """Params s kalibriranim r/g za sve; beta IZ SERIJE gdje je kalibrirana
    (M10, calibrations tablica); peer multipli iz baze samo gdje skup postoji."""
    beta, beta_src, beta_cal = BETA, BETA_SRC, False
    bc = _calibration(f"beta:{ticker}")
    if bc and bc.get("calibrated"):
        beta, beta_cal = float(bc["beta"]), True
        beta_src = (
            f"beta={bc['beta']}: IZMJERENA — OLS tjednih log-prinosa klase "
            f"{bc['class_ticker']} vs CROBEX ({bc['period']}, n={bc['n_weeks']} "
            f"tjedana, R²={bc['r2']}); izvor: zse.hr securityHistory + "
            f"indexHistory (službene serije). NAPOMENA: R²<0,5 znači široku "
            f"pouzdanost nagiba — beta je procjena, ne konstanta")
    r = RF + beta * ERP

    disc_src = DISCOUNT_SRC
    dc = _calibration("holding_discount:ADRS") if ticker == "ADRS" else None
    if dc:
        disc_src = (
            f"holding diskont 15–25%: OSTAJE PRETPOSTAVKA. Povijesna serija "
            f"(M10, {dc['period']}, n={dc['n_days']} d) mjeri cijenu prema "
            f"KONZERVATIVNOM NAV proxyju i pokazuje PREMIJU, ne diskont: "
            f"medijan {dc['median']:+.1%}, p25 {dc['p25']:+.1%}, p75 "
            f"{dc['p75']:+.1%}, zadnje {dc['latest']:+.1%} ({dc['latest_date']}) "
            f"— negativno = cijena IZNAD proxyja. Proxy drži neuvrštene dijelove "
            f"na placeholder multiplama i grupni neto dug konstantnim pa NE "
            f"mjeri čisti holding diskont; raspon se zato NE zamjenjuje "
            f"opaženim (docs/calibration.md)")

    sources = {
        "r": f"r={r:.4f} (CAPM: rf+beta×ERP). {RF_SRC}. {ERP_SRC}. {beta_src}",
        "g": G_SRC,
        "wacc": ("wacc≈r (pretpostavka strukture bez duga na razini metode; "
                 "DCF ionako gate-an za ADRS/CROS)"),
        "holding_discount": disc_src,
    }
    p = Params(cost_of_equity=r, perpetual_growth=G, wacc=r)
    p.rates_calibrated = True
    p.beta_calibrated = beta_cal
    p.sources = sources

    if ticker == "ADRS":
        from .peer_multiples import derive  # medijan IZ BAZE, ne prepisan
        res = derive(ADRS_PEERS)
        m = res["median"]
        rows = "; ".join(
            f"{x['ticker']} P/E={x.get('pe') and round(x['pe'], 2)} "
            f"P/B={x.get('pb') and round(x['pb'], 2)}"
            for x in res["rows"] if not x.get("skip"))
        if m["pe"] and m["pe_n"] >= 3 and m["pb"] and m["pb_n"] >= 3:
            p.peer_pe = round(m["pe"], 2)
            p.peer_pb = round(m["pb"], 2)
            if m["ev_ebitda"] and m["ev_ebitda_n"] >= 3:
                p.peer_ev_ebitda = round(m["ev_ebitda"], 2)
            p.peers_calibrated = True
            sources["peers"] = (
                f"peer multipli = MEDIJAN iz baze (zadnje cijene + FY2025 kons. "
                f"financije): P/E={p.peer_pe} (n={m['pe_n']}), P/B={p.peer_pb} "
                f"(n={m['pb_n']}), EV/EBITDA={p.peer_ev_ebitda} "
                f"(n={m['ev_ebitda_n']}). Skup {ADRS_PEERS} (docs/peers.md; "
                f"nijedan isključen — profitabilni, konzumeri+turizam). "
                f"Po peeru: {rows}")
        else:
            sources["peers"] = ("peer skup nedovoljno pokriven (n<3) -> "
                                "multipli OSTAJU placeholder")
    else:
        sources["peers"] = (f"{ticker}: peer skup nije kalibriran — na ZSE nema "
                            "dovoljno usporedivih firmi u sektoru (odluke i kandidati "
                            "u docs/peers.md; regionalni peeri nedostupni mrežnom "
                            "politikom) -> peer multipli OSTAJU placeholder "
                            "(P/E 12, P/B 1,5) + needs_review")

    # master flag: placeholder samo ako su i stope i peeri placeholder
    p.placeholder = not (p.rates_calibrated and p.peers_calibrated)
    return p
