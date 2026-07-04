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
BETA_SRC = ("beta=1,0: PRETPOSTAVKA — u bazi 2 dana cijena, procjena bete "
            "traži povijesnu seriju; nije tržišno utvrđena")

G = 0.02
G_SRC = ("g=2,0%: ECB inflacijski cilj (HR u eurozoni) kao konzervativan "
         "perpetualni nominalni rast; namjerno ispod povijesnog nominalnog "
         "rasta BDP-a; g<r zadovoljeno")

DISCOUNT_SRC = ("holding diskont 15–25%: empirijski raspon za europske holdinge "
                "(nelikvidnost, dvostruko oporezivanje, trošak centra); "
                "PRETPOSTAVKA — povijesni ADRS diskont neizvediv iz baze "
                "(2 dana cijena); tekuća usporedba cijena↔NAV u "
                "assumptions.market_check SOTP-a")

ADRS_PEERS = ["ATGR", "PODR", "RIVP", "PLAG", "ARNT"]


def build_params(ticker: str) -> Params:
    """Params s kalibriranim r/g za sve; peer multipli iz baze samo gdje skup postoji."""
    r = RF + BETA * ERP
    sources = {
        "r": f"r={r:.4f} (CAPM: rf+beta×ERP). {RF_SRC}. {ERP_SRC}. {BETA_SRC}",
        "g": G_SRC,
        "wacc": ("wacc≈r (pretpostavka strukture bez duga na razini metode; "
                 "DCF ionako gate-an za ADRS/CROS)"),
        "holding_discount": DISCOUNT_SRC,
    }
    p = Params(cost_of_equity=r, perpetual_growth=G, wacc=r)
    p.rates_calibrated = True
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
