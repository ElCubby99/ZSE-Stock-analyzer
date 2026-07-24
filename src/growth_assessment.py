"""M47: procjena ODRŽIVOG rasta po firmi — bez slijepog capa na 10%.

Zamjenjuje raniji "medijan tri signala pa cap 10%" principijelnom procjenom
koja za SVAKU firmu iz objavljenih brojki utvrdi je li rast STRUKTURNO
ODRŽIV ili djelomično jednokratan, i to obrazloži.

Ulazi (svi iz baze — ništa izmišljeno):
  series      — [(fy, revenue_eur)] godišnje, uzlazno (≥2 točke);
  g_sust      — kapacitet samofinanciranja = ROE × (1 − payout) (ili None);
  g_terminal  — dugoročno sidro (nominalni BDP ~4%) prema kojem se fadea;
  r           — trošak kapitala (za sanity, NE za slijepi cap);
  backlog     — {"g": stopa, "src": izvor} kad je knjiga narudžbi objavljena
                tvrda brojka koja potkrjepljuje near-term rast (ili None);
  ni_series   — [(fy, net_income_parent)] za detekciju jednokratne zarade;
  margins     — [(fy, ebit_margin)] za signal kvalitete (rastuće marže =
                strukturni rast, ne cjenovni jednokratni skok).

Načelo:
  - REPREZENTATIVNI opaženi rast = MEDIJAN godišnjih YoY stopa (otporan na
    jednu iznimnu godinu), a ne endpoint-CAGR (koji jedna bazna/vršna godina
    iskrivi). Ako CAGR >> medijan -> jednokratni outlier, imenuje se godina.
  - ODRŽIVOST: rast je održiv kad ga firma može SAMOFINANCIRATI (opaženi ≈
    g_sust) i/ili ga potkrepljuje objavljena knjiga narudžbi. Kad opaženi
    bitno premašuje kapacitet samofinanciranja bez backloga -> sidrimo prema
    g_sust (fundabilna stopa) i to kažemo.
  - USPORAVANJE: kad je zadnja godina bitno ispod medijana, near-term se
    pomiče prema zadnjoj (recentniji signal).
  - NEMA slijepog capa 10%; postoji SAMO sanity strop 25% (5-god. rast iznad
    toga je neplauzibilan) i zahtjev g_terminal < r (inače terminal puca).
  - g1 = procijenjena održiva near-term stopa; kroz 5 g LINEARNO fadea prema
    g_terminal (reversion to mean).

Vraća (g1, meta) gdje meta nosi: signale, verdikt (kod + hrvatski narativ),
badgeove za UI. g1=None kad nema nijednog signala.
"""
from __future__ import annotations

from statistics import median
from typing import Optional

SANITY_MAX = 0.25          # 5-god. rast iznad 25% je neplauzibilan (nije 10% cap!)
ONE_OFF_MULT = 2.5         # YoY > 2,5× medijan (i pozitivan medijan) => outlier
CONVERGE_BAND = 0.05       # |opaženi − g_sust| ≤ 5 p.b. => "poklapaju se"
DECEL_BAND = 0.06          # zadnja YoY < medijan − 6 p.b. => usporavanje


def _yoy(series: list) -> list:
    """[(fy, val)] uzlazno -> [(fy, yoy_rate)] za uzastopne godine s val>0."""
    out = []
    for (y0, v0), (y1, v1) in zip(series, series[1:]):
        if v0 and v1 and float(v0) > 0 and float(v1) > 0 and y1 == y0 + 1:
            out.append((y1, float(v1) / float(v0) - 1))
    return out


def _cagr(series: list) -> Optional[float]:
    if len(series) < 2:
        return None
    (y0, v0), (y1, v1) = series[0], series[-1]
    if v0 and v1 and float(v0) > 0 and float(v1) > 0 and y1 > y0:
        return (float(v1) / float(v0)) ** (1 / (y1 - y0)) - 1
    return None


def assess_growth(series, g_sust, g_terminal, r, *, backlog=None,
                  ni_series=None, margins=None, item="prihoda"):
    yoy = _yoy(series or [])
    cagr = _cagr(series or [])
    # prudencija (zadržana iz v3.1): JEDNA godišnja usporedba nije stopa rasta
    # — opaženi rast traži ≥2 YoY (tj. ≥3 godišnja izvješća). Ispod toga se
    # oslanja na kapacitet samofinanciranja (g_sust).
    g_med = median([g for _, g in yoy]) if len(yoy) >= 2 else None
    g_recent = yoy[-1][1] if yoy else None
    marg_rising = None
    if margins and len(margins) >= 3:
        ms = [m for _, m in margins if m is not None]
        marg_rising = len(ms) >= 3 and ms[-1] > ms[0]

    # --- nema nijednog rast-signala: prepusti g_sust/terminal (kratka serija)
    if g_med is None and g_sust is None:
        return None, {"verdict": "nema_signala", "badges": ["nema signala rasta"],
                      "narrative": "Nema ≥2 godišnja izvješća ni kapaciteta "
                                   "samofinanciranja — rast se ne procjenjuje.",
                      "signals": {"g_median": None, "g_cagr": None,
                                  "g_sust": g_sust, "g_recent": None,
                                  "g_terminal": g_terminal, "backlog": None}}

    # --- jednokratni outlier: godina čiji je YoY >> medijan ---
    one_off = None
    if yoy and g_med is not None and g_med > 0:
        y_out, g_out = max(yoy, key=lambda t: t[1])
        if g_out > ONE_OFF_MULT * g_med:
            one_off = (y_out, g_out)

    g_repr = g_med  # reprezentativni opaženi rast = medijan (otporan na outlier)

    badges, narr = [], []
    # === procjena održivosti ===
    if g_repr is None:
        # samo g_sust postoji (kratka serija): koristi ga kao proxy, oprez
        g1 = g_sust
        verdict = "samofinanciranje_bez_serije"
        narr.append(f"Kratka serija (nema ≥2 godine) — rast procijenjen iz "
                    f"kapaciteta samofinanciranja (ROE × zadržano) {g_sust:+.1%}.")
    else:
        fundable = g_sust if g_sust is not None else None
        if fundable is not None and g_repr > fundable + CONVERGE_BAND and backlog is None:
            # opaženi bitno iznad kapaciteta samofinanciranja, bez backloga
            g1 = (g_repr + fundable) / 2  # sidri prema fundabilnoj stopi
            verdict = "iznad_samofinanciranja"
            narr.append(
                f"Opaženi rast ({item}) {g_repr:+.1%} PREMAŠUJE kapacitet "
                f"samofinanciranja {fundable:+.1%} (ROE × zadržana dobit) — "
                f"dio rasta traži vanjsko financiranje ili je ciklički; bez "
                f"objavljene knjige narudžbi sidrimo prema fundabilnoj stopi "
                f"({g1:+.1%}).")
        elif fundable is not None and abs(g_repr - fundable) <= CONVERGE_BAND:
            g1 = (g_repr + fundable) / 2
            verdict = "odrziv_samofinanciran"
            narr.append(
                f"Opaženi rast {g_repr:+.1%} POKLAPA SE s kapacitetom "
                f"samofinanciranja {fundable:+.1%} (ROE × zadržana dobit) — "
                f"rast je financiran iz vlastite dobiti, dakle strukturno "
                f"održiv (a ne jednokratan).")
            if marg_rising:
                narr.append("Marže rastu kroz razdoblje — rast nosi i veća "
                            "profitabilnost, ne samo obujam (potvrda kvalitete).")
        else:
            g1 = g_repr
            verdict = "odrziv_serija"
            narr.append(f"Rast {g_repr:+.1%} (medijan godišnjih stopa) iz "
                        f"dosljedne serije.")

    # --- jednokratni efekt: imenuj godinu i skini je iz reprezentativnog ---
    if one_off:
        y_out, g_out = one_off
        badges.append(f"jednokratni skok FY{y_out} (+{g_out:.0%}) izuzet iz stope")
        narr.append(
            f"FY{y_out} je iznimna godina (+{g_out:.0%} vs medijan {g_med:+.1%}) "
            f"— vjerojatno jednokratni efekt (akvizicija/jednokratni prihod); "
            f"reprezentativni rast uzima MEDIJAN godišnjih stopa, ne CAGR "
            f"(koji bi ta godina napuhala na {cagr:+.1%}).")

    # --- usporavanje: zadnja godina bitno ispod medijana ---
    decel = (g_recent is not None and g_med is not None
             and g_recent < g_med - DECEL_BAND and verdict.startswith("odrziv"))
    if decel:
        g1 = (g1 + g_recent) / 2
        badges.append(f"usporavanje (zadnja YoY {g_recent:+.0%})")
        narr.append(
            f"Zadnja godina ({g_recent:+.1%}) bitno je ispod medijana "
            f"({g_med:+.1%}) — rast usporava; near-term pomaknut prema "
            f"recentnijem signalu na {g1:+.1%}.")

    # --- backlog: OBJAVLJENA knjiga narudžbi je forward vidljivost i djeluje
    #     NAKON usporavanja — ako je zadnja godina prihoda usporila zbog odgode
    #     priznavanja na dugim ugovorima, backlog to pobija (narudžbe su
    #     ugovorene). Backlog je POD na near-term rast: g1 se ne spušta ispod
    #     backlog-implicirane stope; iznad trailing rasta blenda pola-pola
    #     (oprez), a sanity strop hvata pretjerane tvrdnje. ---
    if backlog and backlog.get("g") is not None:
        gb = min(backlog["g"], SANITY_MAX)
        src = backlog.get("src", "objavljeno")
        if gb > g1:
            new_g1 = (g1 + gb) / 2 if not decel else max(g1, gb)
            # kod usporavanja backlog je POD (ugovorene narudžbe), ne polovica
            verdict = "odrziv_backlog"
            if decel:
                narr.append(
                    f"ALI knjiga narudžbi (+{gb:.1%}, {src}) pobija usporavanje: "
                    f"pad prihoda zadnje godine je odgoda priznavanja na dugim "
                    f"ugovorima, ne pad potražnje — ugovorene narudžbe su POD na "
                    f"near-term rast, pa je g1 vraćen na {new_g1:+.1%}.")
            else:
                narr.append(
                    f"Knjiga narudžbi potkrepljuje veći near-term rast ~{gb:+.1%} "
                    f"({src}) — objavljena tvrda brojka, ne procjena; near-term "
                    f"stopa podignuta (blend s trailing rastom radi opreza) na "
                    f"{new_g1:+.1%}.")
            g1 = new_g1
        else:
            narr.append(f"Knjiga narudžbi ({gb:+.1%}, {src}) ne nadmašuje "
                        f"procijenjeni rast — bez korekcije naviše.")

    # --- skupljanje: negativan rast dopušten samo uz ≥3g dokaz ---
    if g1 is not None and g1 < 0:
        if len(yoy) >= 2 and g_med is not None and g_med < 0:
            badges.append("negativan rast — višegodišnje skupljanje dokazano")
            narr.append("Serija pokazuje višegodišnje skupljanje — negativan "
                        "rast se ne 'popravlja' na nulu.")
        else:
            g1 = 0.0
            badges.append("donja granica 0 (bez ≥3g dokaza skupljanja)")

    # --- sanity strop/pod (NE 10% cap): |5-god. rast| > 25% nije plauzibilan;
    #     jednako vrijedi za skupljanje — pad od 40–60%/god. 5 g je jednokratni
    #     kolaps (izgubljen ugovor), ne trajna stopa ---
    if g1 is not None and g1 > SANITY_MAX:
        badges.append(f"sanity strop {SANITY_MAX:.0%} (5-god. rast iznad toga "
                      f"nije plauzibilan)")
        narr.append(f"Procijenjeni {g1:+.1%} premašuje sanity strop "
                    f"{SANITY_MAX:.0%} — ni najbrže firme ne održe to 5 godina; "
                    f"ograničeno na {SANITY_MAX:.0%}.")
        g1 = SANITY_MAX
    elif g1 is not None and g1 < -SANITY_MAX:
        badges.append(f"sanity pod −{SANITY_MAX:.0%} (5-god. pad ispod toga je "
                      f"jednokratni kolaps, ne trajna stopa)")
        narr.append(f"Procijenjeni {g1:+.1%} probija sanity pod −{SANITY_MAX:.0%} "
                    f"— pad te dubine 5 g zaredom je jednokratni kolaps, a ne "
                    f"održiva stopa; ograničeno na −{SANITY_MAX:.0%}.")
        g1 = -SANITY_MAX

    # --- terminal mora biti < r (inače Gordon puca); g1 SMIJE biti blizu/iznad
    #     r jer eksplicitna faza ne dijeli s (r−g1), samo terminal s (r−gT) ---
    if g1 is not None:
        g1 = round(g1, 4)

    meta = {
        "verdict": verdict,
        "signals": {"g_median": _r(g_med), "g_cagr": _r(cagr),
                    "g_sust": _r(g_sust), "g_recent": _r(g_recent),
                    "g_terminal": _r(g_terminal),
                    "backlog": (_r(backlog["g"]) if backlog and backlog.get("g")
                                is not None else None)},
        "one_off": (f"FY{one_off[0]}" if one_off else None),
        "margins_rising": marg_rising,
        "badges": badges,
        "narrative": " ".join(narr),
    }
    return g1, meta


def _r(v):
    return round(v, 4) if v is not None else None
