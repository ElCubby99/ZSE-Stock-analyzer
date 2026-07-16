#!/usr/bin/env python3
"""FAZA D: generator izvještaja docs/forenzika_v3_faza_d.md iz
docs/forenzika_v3_faza_d.json (proizvodi ga scripts/forenzika_v3.py).

Sve TABLICE su generirane iz JSON-a (nula ručnog prepisivanja brojki);
analitički tekst je dio ovog skripta pa je cijeli izvještaj reproducibilan:
    python scripts/forenzika_v3.py && python scripts/forenzika_v3_report.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
J = json.load(open(ROOT / "docs" / "forenzika_v3_faza_d.json", encoding="utf-8"))
OUT = ROOT / "docs" / "forenzika_v3_faza_d.md"

R = {r["ticker"]: r for r in J["results"]}
TOP15 = [t for t, _ in J["top15_by_turnover"]]
ORDER = TOP15 + [t for t in J["extra_from_order"] if t not in TOP15]

M_LABEL = {"comps": "Peer usporedba", "dcf_fcf": "DCF (FCF)",
           "ddm_gordon": "DDM", "justified_pb_roe": "Opravdani P/B",
           "residual_income": "Rezidualni dohodak", "sotp_nav": "SOTP/NAV"}


def pct(x, nd=1):
    return "n/p" if x is None else f"{x:+.{nd}f}%"


def f2(x):
    return "n/p" if x is None else f"{x:,.2f}"


def zone_s(r):
    if r["zone_low"] is None:
        return "n/p"
    return f"{r['zone_low']:,.0f}–{r['zone_high']:,.0f}"


lines = []
w = lines.append

w("# Forenzika fer-zona — FAZA D (Metodologija v3)")
w("")
w(f"*Interni dijagnostički dokument · generirano {J['generated']} · zadnje "
  "cijene 15.07.2026 · motor: tekući kod (v2.3) i tekuća baza — U OVOJ FAZI "
  "NIŠTA NIJE MIJENJANO (ni kod izračuna, ni parametri, ni baza).*")
w("")
w("Reproducira se s: `python scripts/forenzika_v3.py && python "
  "scripts/forenzika_v3_report.py`. Brojke u tablicama dolaze izravno iz "
  "`docs/forenzika_v3_faza_d.json`.")
w("")

# ---------------- 0. sažetak ----------------
gaps = {t: R[t]["gap_vs_mid_pct"] for t in TOP15 if R[t]["gap_vs_mid_pct"] is not None}
big = {t: g for t, g in gaps.items() if abs(g) > 30}
w("## 0. Sažetak nalaza")
w("")
w(f"Od 15 najprometnijih dionica njih **{len(big)}/{len(gaps)} "
  f"({len(big) / len(gaps) * 100:.0f}%) ima |raskorak| > 30%** naspram sredine "
  "fer-zone — prag distribucijskog alarma iz FAZE P (>40% top imena) danas bi "
  "se aktivirao. ZABA (kontrola) je u zoni. Problem je potvrđen kao SUSTAVAN "
  "i ima tri uzroka koja se međusobno POJAČAVAJU:")
w("")
w("1. **r-stack naplaćuje Hrvatsku dvaput** (FAZA K). rf = 3,61% je prinos HR "
  "10g obveznice — on VEĆ SADRŽI hrvatski spread naspram njemačkog Bunda. "
  "ERP = 5,7% je Damodaranov zreli ERP 4,23% + CRP za Moody's A3 (~1,5 p.b.) "
  "— rizik zemlje je time u r-u ugrađen DVA puta, a CRP je uz to skriven "
  "unutar ERP-a (nije zasebna, vidljiva komponenta). Uz β=1 to daje r=9,31%; "
  "konzistentan stack (EUR bezrizični + zreli ERP + JEDAN mali CRP primjeren "
  "'A-' eurozoni) bio bi ~8,3–8,4% (2,6–2,7 + 4,23 + ≤1,5).")
n_ttm0 = len(J["ttm_coverage"])
n_cap_anchor = sum(1 for t in ORDER
                   if R[t]["anchor"] in ("justified_pb_roe", "residual_income"))
w(f"2. **Trailing godišnje bez TTM-a i bez rasta u kapitalnim metodama** "
  f"(FAZA G). Sva imena vrednujemo iz zadnjeg GODIŠNJEG izvješća (FY2025), "
  f"iako u bazi za {n_ttm0} firmi postoje kvartali (zadnji: Q1 FY2026, s "
  f"dobiti, prihodom i kapitalom). Opravdani P/B i RI — sidro za "
  f"{n_cap_anchor}/{len(ORDER)} analiziranih — povrh toga NEMAJU fazu rasta: "
  "trailing ROE i trajni g=2,5% kažnjavaju svaku firmu čija dobit raste.")
w("3. **Dogma jednog sidra** (FAZA A). Zona = raspon JEDNE metode po "
  "hijerarhiji arhetipa. Potvrdne metode koje konvergiraju prema tržištu "
  "vidljive su, ali zonu ne pomiču (HT: DCF 61,1 € vs sidro 22,8 €; CROS: "
  "DDM 2.396 / RI 1.939 / comps 3.038 vs sidro 1.349). Za HT/CROS/SPAN/HPB/"
  "ZABA/INA comps je uz to placeholder (conf 0,3 — nema peer skupa) pa po "
  "postojećim pravilima ništa ne može 'preglasati' sidro.")
w("")
# implied r SIDRENE metode kod imena s pozitivnim raskorakom > 30%
_imp_big = []
for _t, _g in gaps.items():
    _r = R[_t]
    _k = _r["anchor"] if _r["anchor"] in (_r["reverse_r"] or {}) else None
    if _g > 30 and _k and _r["reverse_r"][_k] is not None:
        _imp_big.append(_r["reverse_r"][_k])
for _t in J["extra_from_order"]:
    _r = R[_t]
    _k = _r["anchor"] if _r["anchor"] in (_r["reverse_r"] or {}) else None
    if (_r["gap_vs_mid_pct"] or 0) > 30 and _k and _r["reverse_r"][_k] is not None:
        _imp_big.append(_r["reverse_r"][_k])
_rs_all = [R[t]["r_stack"]["r_total"] for t in ORDER]
w(f"**Reverse-r potvrđuje Borisovu hipotezu, uz jednu poštenu ogradu**: kod "
  f"{len(_imp_big)} imena s pozitivnim raskorakom > 30% i r-ovisnim sidrom, "
  f"implicirani r sidrene metode (onaj koji izjednačava našu projekciju s "
  f"tržišnom cijenom) je **{min(_imp_big) * 100:.1f}–{max(_imp_big) * 100:.1f}%**, "
  f"dok mi tim istim imenima računamo znatno više (naš r po svih 17 imena: "
  f"{min(_rs_all) * 100:.1f}–{max(_rs_all) * 100:.1f}%). Puni raspon implied "
  "r po SVIM imenima je širi (do 14,6% kod KOEI — protuprimjeri u §2). Dio "
  "tog klina je r-stack (FAZA K), ali dio je i to što je 'naša projekcija' "
  "trailing godišnja bez TTM-a i bez rasta — pa se klin dijeli između K i "
  "G. Cilj v3 NIJE zatvoriti raskorak prema tržištu, nego ukloniti dokazane "
  "metodološke greške; preostala razlika je činjenica koju prikazujemo.")
w("")

# ---------------- 1. zbirna tablica ----------------
w("## 1. Zbirna tablica — top 15 po prometu (+ CROS i INA iz naloga)")
w("")
w("| # | Dionica | Arhetip | Sidro | Fer-zona € | Cijena € | Raskorak vs sredina | r | β (porijeklo) | nelikv. | g1 | ROE (FY) |")
w("|--:|---------|---------|-------|-----------:|---------:|--------------------:|----:|--------------|--------:|-----|---------:|")
for i, t in enumerate(ORDER, 1):
    r = R[t]
    rs = r["r_stack"]
    extra = "" if t in TOP15 else " *(iz naloga)*"
    g1 = r["g"]["g1"]
    g1s = "—" if g1 is None else f"{g1 * 100:.1f}%" + ("F" if r["g"]["forward"] else "H")
    roe = r["roe"]
    roes = "n/p" if roe["value"] is None else f"{roe['value'] * 100:.1f}% (FY{roe['ni_fy']})"
    w(f"| {i} | **{t}**{extra} | {r['archetype']} | {r['anchor']} | {zone_s(r)} "
      f"| {r['price']:,.2f} | {pct(r['gap_vs_mid_pct'])} | {rs['r_total'] * 100:.2f}% "
      f"| {rs['beta']:.2f} ({rs['beta_origin']}) | {rs['illiq_premium'] * 100:+.1f} p.b. "
      f"| {g1s} | {roes} |")
w("")
w("*g1: F = forward procjena iz izvješća (growth_estimates), H = povijesni 3g "
  "CAGR, — = nema serije (bez faze rasta). ROE: trailing iz zadnjeg godišnjeg "
  "(NE TTM). Raskorak = cijena / sredina zone − 1.*")
w("")
w("**Napomena o PODR-u**: na živom webu Boris je vidio +200,4% — to je bila "
  "zona 14–53 € iz builda PRIJE v2.3 (degenerirano DCF sidro). Tekući kod "
  "daje comps sidro 246–333 € i raskorak **−44,8%** (cijena ISPOD zone). "
  "Ista dionica je u dva uzastopna builda bila 'duboko iznad' pa 'duboko "
  "ispod' zone — nestabilnost izbora jednog sidra je sama po sebi nalaz "
  "za FAZU A (medijan kvalificiranih metoda).")
w("")

# ---------------- 2. reverse-r ----------------
w("## 2. Dijagnostika 1 — reverse-r (koji bi r izjednačio projekciju s cijenom)")
w("")
w("Bisekcija po r za svaku r-ovisnu metodu s pozitivnom bazom (comps i "
  "SOTP ne ovise o r pa reverse-r nemaju). 'n/p' = cijena je izvan raspona "
  "koji metoda može dati za r ∈ (g, 40%] — ni ekstremni r ne premošćuje "
  "raskorak (tada uzrok NIJE r nego projekcija).")
w("")
w("| Dionica | naš r | implied r (po metodi) | klin naš−implied (sidrena/najbliža r-ovisna) |")
w("|---------|------:|-----------------------|---------------------------------------------:|")
for t in ORDER:
    r = R[t]
    if not r["reverse_r"]:
        w(f"| {t} | {r['r_stack']['r_total'] * 100:.2f}% | (nema r-ovisne metode s bazom) | — |")
        continue
    parts = []
    for k, v in r["reverse_r"].items():
        parts.append(f"{M_LABEL[k]}: {'n/p' if v is None else f'{v * 100:.2f}%'}")
    prim_k = r["anchor"] if r["anchor"] in r["reverse_r"] else next(iter(r["reverse_r"]))
    prim_v = r["reverse_r"][prim_k]
    klin = ("—" if prim_v is None
            else f"{(r['r_stack']['r_total'] - prim_v) * 100:+.1f} p.b. ({prim_k})")
    w(f"| {t} | {r['r_stack']['r_total'] * 100:.2f}% | {'; '.join(parts)} | {klin} |")
w("")
imp = []
for t in ORDER:
    r = R[t]
    k = r["anchor"] if r["anchor"] in (r["reverse_r"] or {}) else None
    if k and r["reverse_r"][k] is not None and (r["gap_vs_mid_pct"] or 0) > 30:
        imp.append((t, r["reverse_r"][k]))
_imp_vals = [v for _, v in imp]
_r_big = [R[t]["r_stack"]["r_total"] for t, _ in imp]
w("**Čitanje**: kod imena s velikim pozitivnim raskorakom implied r sidrene "
  "metode iznosi " + ", ".join(f"{t} {v * 100:.1f}%" for t, v in imp) + ". "
  f"Grupiranje je na {min(_imp_vals) * 100:.1f}–{max(_imp_vals) * 100:.1f}% — "
  f"dok tim istim imenima računamo {min(_r_big) * 100:.1f}–"
  f"{max(_r_big) * 100:.1f}%. To je smjer koji je Boris predvidio. Ograda: "
  "implied r je izračunat nad TRAILING projekcijom (bez TTM-a, kapitalne "
  "metode bez rasta), pa 'pravi' klin r-a nakon FAZE G bude manji — dio "
  "klina pripada podcijenjenoj projekciji, ne r-u.")
w("")
w("Suprotan smjer postoji i dokazuje da se ne radi o univerzalnom 'r je "
  "prevelik': KOEI implied 14,6% > naš 12,5% (tržište KOEI vrednuje "
  "KONZERVATIVNIJE od nas), KODT implied 11,7% ≈ naš 12,1%, ZABA implied "
  "9,4–9,7% ≈ naš 9,5% (u zoni). Problem je sustavan kod imena sidrenih na "
  "kapitalne metode bez rasta i s dvostrukim CRP-om.")
w("")

# ---------------- 3. konvergencija vs sidro ----------------
w("## 3. Dijagnostika 2 — metode konvergiraju, sidro divergira")
w("")
strict = [(t, c) for t in ORDER for c in R[t]["convergence_vs_anchor"]]
if strict:
    w("| Dionica | Par metoda (conf) | Sredina para € | Sidro € | Sidro vs par |")
    w("|---------|-------------------|---------------:|--------:|-------------:|")
    for t, c in strict:
        w(f"| {t} | {c['pair'][0]}+{c['pair'][1]} ({c['pair_conf']}) "
          f"| {c['pair_mid']:,.2f} | {c['anchor_base']:,.2f} "
          f"| {pct(c['anchor_vs_pair_pct'])} |")
else:
    w("Po STROGOM kriteriju iz naloga (par metoda unutar ±20%, sidro >30% od "
      "njihove sredine) tablica je **prazna** — i to je nalaz, a ne 'sve u "
      "redu'. Razlozi zašto potvrde danas ne mogu preglasati sidro:")
    w("")
    w("- **DDM je gate-an samo na banke/osiguranje** (v2 §1/§2) — kod "
      "industrijskih imena DDM-a nema, pa par 'DDM+comps' ne može ni nastati.")
    w("- **Comps je placeholder (conf 0,3) baš tamo gdje je najpotrebniji**: "
      "HT, CROS, SPAN, HPB, ZABA, INA nemaju peer skup na ZSE → comps im "
      "postoji, ali s multiplima P/E 12 / P/B 1,5 koji nisu podatak.")
    w("- **RI ≈ opravdani P/B po konstrukciji** (jednostupanjski RI je "
      "matematički identičan opravdanom P/B-u; razlika je samo fade) — pa "
      "'par koji konvergira' najčešće uključuje samo sidrovu blizanku.")
    w("")
    w("Najbliži slučajevi (par unutar ±30%), koji pokazuju ISTI obrazac koji "
      "je Boris uočio kod CROS-a:")
    w("")
    near = []
    for t in ORDER:
        r = R[t]
        ms = {k: m for k, m in r["methods"].items() if m["base"] and m["base"] > 0}
        keys = [k for k in ms if k != r["anchor"]]
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                va, vb = ms[a]["base"], ms[b]["base"]
                if abs(va / vb - 1) <= 0.30 and r["anchor"] in ms:
                    mid = (va + vb) / 2
                    dev = ms[r["anchor"]]["base"] / mid - 1
                    if abs(dev) > 0.30:
                        near.append((t, a, va, b, vb, mid, dev))
    for t, a, va, b, vb, mid, dev in near:
        w(f"- **{t}**: {M_LABEL[a]} {va:,.0f} € i {M_LABEL[b]} {vb:,.0f} € "
          f"(razmak {abs(va / vb - 1) * 100:.0f}%) — sidro "
          f"{M_LABEL[R[t]['anchor']]} je {dev * 100:+.0f}% od njihove sredine.")
w("")
w("**CROS detaljno (slučaj iz naloga)**: DDM 2.396 € (conf 0,7; dvofazni, "
  "DPS 114,14 € izglasan 2026., g1 12,9% iz 3g CAGR-a), RI 1.939 € (conf "
  "0,7), comps 3.038 € (conf 0,3, placeholder) — tržište 3.320 €. Sidro "
  "opravdani P/B: 1.349 € (trailing ROE 7,5% FY2025, bez rasta, r=10,02% "
  "koji uključuje +1 p.b. nelikvidnosti). Model se doista ne slaže sam sa "
  "sobom i uvijek sidri na najkonzervativniju polovicu. Napomena: Borisov "
  "citat 'DDM 3.670' je sa starije builde (drugačiji DPS ulaz); obrazac je "
  "isti, brojka danas 2.396 €.")
w("")

# ---------------- 4. TTM ----------------
w("## 4. Dijagnostika 3 — TTM pokrivenost (kvartali POSTOJE, vrednujemo godišnje)")
w("")
n_ttm = len(J["ttm_coverage"])
w(f"U bazi **{n_ttm} firmi ima interim filinge** (M18/M20), a `data()` u "
  "`build_ctx` čita ISKLJUČIVO `period_type='annual'` — dakle SVE se "
  "vrednuje iz zadnjeg godišnjeg. Za top imena stanje interima:")
w("")
w("| Dionica | zadnje godišnje | zadnji interim | stariji interimi | NI u interimu? |")
w("|---------|-----------------|----------------|------------------|----------------|")
ttm_by = {x["ticker"]: x for x in J["ttm_coverage"]}
NI_NOTE = {"ZABA": "Q1'26 bez NI (FINREP objavljuje polugodišnje) — TTM tek s H1'26"}
for t in ORDER:
    x = ttm_by.get(t)
    if not x:
        w(f"| {t} | — | nema interima | — | — |")
        continue
    # stvarni zadnji interim po firmi (ne unija tipova preko svih godina)
    ifl = R[t]["inputs_provenance"].get("_interim_filings") or []
    last_fy = max((e["fy"] for e in ifl), default=None)
    latest = ", ".join(sorted(e["period"] for e in ifl if e["fy"] == last_fy))
    older = "; ".join(f"{e['period']} FY{e['fy']}"
                      for e in sorted(ifl, key=lambda e: (-e["fy"], e["period"]))
                      if e["fy"] != last_fy)
    note = NI_NOTE.get(t, "da (dobit+prihod+kapital)")
    w(f"| {t} | FY{x['last_annual_fy']} | {latest} FY{last_fy} | {older or '—'} | {note} |")
w("")
w("Provjereno na uzorku (ADRS, ATGR, CROS, DLKV, HT, INA, PODR, RIVP, SPAN, "
  "KODT...): interim filingi NOSE net_income_parent, prihod i kapital — TTM "
  "(FY2025 + Q1'26 − Q1'25) je izračunljiv odmah, za sve sektore. Jedina "
  "iznimka u top skupini: ZABA Q1'26 bez NI. Popis svih "
  f"{n_ttm} firmi s interimima je u JSON-u (`ttm_coverage`).")
w("")
w("Posljedica ne-TTM-a je asimetrična: firme kojima dobit raste (većina "
  "univerzuma 2025–2026) sustavno su podcijenjene jer im i ROE (kapitalne "
  "metode) i NI (P/E leća) kasne 6–18 mjeseci za stvarnošću.")
w("")

# ---------------- 5. ERP/CRP audit ----------------
a = J["erp_audit"]
w("## 5. Dijagnostika 4 — ERP/CRP audit (double counting)")
w("")
w(f"- **rf = {a['rf'] * 100:.2f}%** — izvor (iz koda): {a['rf_src']}")
w(f"- **ERP = {a['erp'] * 100:.1f}%** — izvor (iz koda): {a['erp_src']}")
w("- **Beta**: likvidna imena regresijska (OLS tjedni log-prinosi vs CROBEX, "
  "Blume 0,67β+0,33); ispod praga likvidnosti sektorska (Damodaran Europe, "
  "relever); clamp [0,7, 1,8].")
w("- **Premija nelikvidnosti**: +1,0 p.b. ispod praga (≥60% trgovanih dana i "
  "≥1.000 €/dan), +2,0 p.b. za vrlo nelikvidne — ZASEBNA komponenta r-a.")
w("")
w("**Nalazi**:")
w("")
w("1. " + a["finding_erp_contains_crp"])
w("2. **Premija nelikvidnosti je primijenjena ISPRAVNO po tekućim (Z1) "
  "pravilima**: nijedno od 15 likvidnih imena je NEMA (svi prolaze prag); "
  "nose je samo CROS i INA (+1,0 p.b.), koji prag likvidnosti doista ne "
  "prolaze. Zahtjev K.3 je dakle već zadovoljen — u FAZI K treba samo "
  "test koji to trajno čuva.")
w("3. **Kvantifikacija double counta**: uz β=1 danas r = 3,61 + 5,70 = "
  "9,31%. Konzistentan stack: EUR bezrizični (10g Bund, ~2,6–2,7% u 2026.) "
  "+ zreli ERP 4,23% + JEDAN eksplicitni CRP ≤1,5 p.b. (HR je 'A-'/A3, "
  "eurozona, investment grade) → r(β=1) = 8,33–8,43%. Razlika ~0,9–1,0 p.b. "
  "sustavno tereti SVAKO ime; uz β>1 (KOEI grupa 1,46–1,57) klin se "
  "množi.")
w("4. Damodaranove tablice su u kodu označene `exact_unverified` (egress "
  "403 na pages.stern.nyu.edu) — FAZA K zadržava praksu ručnog unosa s "
  "datumom i flagom.")
w("")

# ---------------- 6. po dionici ----------------
w("## 6. Puni raspis po dionici (svi ulazi, sve metode, sidro i zašto)")
w("")
for t in ORDER:
    r = R[t]
    rs = r["r_stack"]
    w(f"### {t} — {r['sector']} · {r['archetype']}")
    w("")
    w(f"- **r = {rs['r_total'] * 100:.2f}%** = rf {rs['rf'] * 100:.2f}% + β "
      f"{rs['beta']:.2f} ({rs['beta_origin']}) × ERP {rs['erp'] * 100:.1f}% "
      f"(uklj. skriveni CRP) + nelikvidnost {rs['illiq_premium'] * 100:.1f} "
      f"p.b. · likvidnosni prag: {'prolazi' if rs['passes_liq_threshold'] else 'NE prolazi'} "
      f"({rs['liquidity']['ratio'] * 100:.0f}% dana, "
      f"{rs['liquidity']['avg_turnover']:,.0f} €/dan)")
    roe = r["roe"]
    if roe["value"] is not None:
        w(f"- **ROE {roe['value'] * 100:.1f}%** iz NI FY{roe['ni_fy']} / kapital "
          f"FY{roe['eq_fy']} — {roe['basis']}")
    g1v = r["g"]["g1"]
    g1txt = "—" if g1v is None else f"{g1v * 100:.1f}%"
    w(f"- **g**: g1 = {g1txt} · {r['g']['source']}")
    w(f"- **kapitalni g {r['g']['g_perpetual'] * 100:.1f}% / terminalni g "
      f"{r['g']['g_terminal'] * 100:.1f}%**")
    w("")
    w("| Metoda | low | base | high | conf | implied r |")
    w("|--------|----:|-----:|-----:|-----:|----------:|")
    for k, m in r["methods"].items():
        if not m["base"]:
            continue
        anchor_mark = " **(SIDRO)**" if k == r["anchor"] else ""
        iv = (r["reverse_r"] or {}).get(k)
        ivs = "—" if iv is None else f"{iv * 100:.2f}%"
        if k not in (r["reverse_r"] or {}):
            ivs = "ne ovisi o r" if k in ("comps", "sotp_nav") else "—"
        w(f"| {M_LABEL.get(k, k)}{anchor_mark} | {f2(m['low'])} | {f2(m['base'])} "
          f"| {f2(m['high'])} | {m['conf']:.1f} | {ivs} |")
    w("")
    w(f"- **Zona {zone_s(r)} €** ({r['anchor']}); cijena {r['price']:,.2f} € → "
      f"raskorak vs sredina **{pct(r['gap_vs_mid_pct'])}**")
    if len(r["classes"]) > 1:
        cls = "; ".join(f"{c['class']} {c['price']:,.2f} € ({pct(c['gap_vs_mid_pct'])})"
                        for c in r["classes"] if c["price"])
        w(f"- **Klase naspram iste zone**: {cls}")
    if r["top10_holders_pct"] is not None:
        w(f"- top-10 dioničara drži **{r['top10_holders_pct']:.1f}%** "
          "(proxy za free float)")
    for q in r["qa_flags"] or []:
        w(f"- QA: {q}")
    w("")

# ---------------- 7. kontradikcije + mapa faza ----------------
w("## 7. Interne kontradikcije iz naloga — potvrđene")
w("")
adrs = R["ADRS"]["classes"]
adrs_map = {c["class"]: c for c in adrs}
w(f"- **ADRS vs ADRS2**: ista fer-zona ({zone_s(R['ADRS'])} €), a ADRS "
  f"{adrs_map['ADRS']['price']:,.2f} € je {pct(adrs_map['ADRS']['gap_vs_mid_pct'])} "
  f"dok je ADRS2 {adrs_map['ADRS2']['price']:,.2f} € "
  f"{pct(adrs_map['ADRS2']['gap_vs_mid_pct'])} — ista firma, dvije priče. "
  "Redovna trguje ~55% iznad povlaštene (glasačka premija) — FAZA S "
  "raspoređuje vrijednost firme tržišnim omjerom klasa. KODT/KODT2 su "
  "usporedbe radi konzistentne (+3,0% / −1,6%), CROS/CROS2 blizu "
  "(+141,7% / +144,6%).")
w("- **CROS se ne slaže sam sa sobom**: vidi §3 — DDM/RI/comps 1.939–3.038 "
  "€, sidro 1.349 €, tržište 3.320 €.")
w("- **PODR**: +200% (stara builda, degenerirani DCF) → −45% (v2.3 comps) — "
  "izbor jednog sidra proizvodi diskontinuitete od 245 p.b. raskoraka bez "
  "ijedne nove brojke u bazi.")
w(f"- **INA**: top-10 dioničara {R['INA']['top10_holders_pct']:.0f}% (MOL + "
  "RH ≈ 94%, free float <5%): cijena se formira u plitkoj knjižici bez "
  "floata — raskorak +386% NIJE informativan; FAZA A.4 iznimka (napomena + "
  "isključenje iz 'temperature tržišta'). Isto vrijedi provjeriti za CROS "
  f"(top-10 {R['CROS']['top10_holders_pct']:.0f}%, u čemu je ADRS-ov udjel "
  "~67% i nelikvidnost ispod praga).")
w("- **HT ilustracija za FAZU A** (dijagnostika, ne meta): kvalificirane "
  "metode {DCF 61,1 (conf 0,6), opravdani P/B 22,8 (conf 0,7)} — medijan "
  "~42 € naspram cijene 41 €. Današnja zona: 20–28 €. Sidro na jednoj "
  "metodi baca informaciju koju druga nosi.")
w("- **HT nema ni 3g serije prihoda u bazi** (samo FY2025 godišnje) — zato "
  "g1 = — i jednofazni Gordon; backfill FY2023–FY2024 GODIŠNJIH je dio "
  "FAZE G pretpostavki (interimi za HT postoje od FY2024).")
w("")
w("## 8. Mapa: nalaz → faza koja ga rješava")
w("")
w("| Nalaz | Faza | Očekivani smjer |")
w("|-------|------|-----------------|")
w("| rizik zemlje dvaput (HR rf + CRP u ERP-u), CRP skriven | **K** | r(β=1) 9,31% → ~8,3–8,4%; raspis rf+β×ERP+CRP+nelikv. vidljiv po dionici |")
w(f"| trailing godišnje umjesto TTM ({n_ttm0} firmi ima kvartale) | **G** | ROE/NI/prihod na TTM; badge `godišnji podatak` gdje kvartala nema |")
w(f"| kapitalne metode bez faze rasta (sidro {n_cap_anchor}/{len(ORDER)} imena) | **G** | g1 iz 3g CAGR-a s capom i fadeom; ROE pravilo max(3g medijan, TTM×0,9) |")
w("| sirova zadnja dividenda u DDM (jednokratne iskrivljuju) | **DIV** | D_sust (održivi payout × normalizirana dobit), pokrivenost najave |")
w("| dogma jednog sidra (PODR flip, HT/CROS kontradikcije) | **A** | zona = medijan kvalificiranih metoda; demote pravilo; dividendni sanity flag |")
w("| ADRS/ADRS2 ista zona, klase ±55% razmaknute | **S** | vrijednost firme × tržišni omjer klasa (medijan 3–5g) |")
w("| raskorak >30% bez narativa; distribucijski alarm | **P** | reverse-DCF okvir svugdje; alarm >40% top-20; changelog v3 + priznate greške |")
w("")
w("**Kontrolne točke za acceptance v3**: ZABA mora ostati u zoni ili blizu "
  "(danas −0,1%); CROS nova zona mora pomiriti DDM/RI/sidro; ako i NAKON "
  "svega >40% top-20 ostane s |raskorakom|>30%, NE fitamo — isporučuje se "
  "reverse-DCF dokaz po imenu i eskalira Borisu.")
w("")
w("---")
w("*MAR napomena: ovaj dokument je interna dijagnostika modela. Ništa u "
  "njemu nije preporuka, rejting ni ciljna cijena; pozicija cijene naspram "
  "zone je činjenica, zaključak je čitateljev.*")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"-> {OUT} ({len(lines)} redaka)")
