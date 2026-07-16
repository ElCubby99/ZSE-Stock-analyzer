# Forenzika fer-zona — FAZA D (Metodologija v3)

*Interni dijagnostički dokument · generirano 2026-07-16 · zadnje cijene 15.07.2026 · motor: tekući kod (v2.3) i tekuća baza — U OVOJ FAZI NIŠTA NIJE MIJENJANO (ni kod izračuna, ni parametri, ni baza).*

Reproducira se s: `python scripts/forenzika_v3.py && python scripts/forenzika_v3_report.py`. Brojke u tablicama dolaze izravno iz `docs/forenzika_v3_faza_d.json`.

## 0. Sažetak nalaza

Od 15 najprometnijih dionica njih **7/15 (47%) ima |raskorak| > 30%** naspram sredine fer-zone — prag distribucijskog alarma iz FAZE P (>40% top imena) danas bi se aktivirao. ZABA (kontrola) je u zoni. Problem je potvrđen kao SUSTAVAN i ima tri uzroka koja se međusobno POJAČAVAJU:

1. **r-stack naplaćuje Hrvatsku dvaput** (FAZA K). rf = 3,61% je prinos HR 10g obveznice — on VEĆ SADRŽI hrvatski spread naspram njemačkog Bunda. ERP = 5,7% je Damodaranov zreli ERP 4,23% + CRP za Moody's A3 (~1,5 p.b.) — rizik zemlje je time u r-u ugrađen DVA puta, a CRP je uz to skriven unutar ERP-a (nije zasebna, vidljiva komponenta). Uz β=1 to daje r=9,31%; konzistentan stack (EUR bezrizični + zreli ERP + JEDAN mali CRP primjeren 'A-' eurozoni) bio bi ~8,3–8,4% (2,6–2,7 + 4,23 + ≤1,5).
2. **Trailing godišnje bez TTM-a i bez rasta u kapitalnim metodama** (FAZA G). Sva imena vrednujemo iz zadnjeg GODIŠNJEG izvješća (FY2025), iako u bazi za 65 firmi postoje kvartali (zadnji: Q1 FY2026, s dobiti, prihodom i kapitalom). Opravdani P/B i RI — sidro za 7/17 analiziranih — povrh toga NEMAJU fazu rasta: trailing ROE i trajni g=2,5% kažnjavaju svaku firmu čija dobit raste.
3. **Dogma jednog sidra** (FAZA A). Zona = raspon JEDNE metode po hijerarhiji arhetipa (fallback min–max svih pozitivnih baza postoji, ali samo kad NIJEDNO sidro ne kvalificira — redovni režim je jedno sidro). Potvrdne metode koje konvergiraju prema tržištu vidljive su, ali zonu ne pomiču (HT: DCF 61,1 € vs sidro 22,8 €; CROS: DDM 2.396 / RI 1.939 / comps 3.038 vs sidro 1.349). Za HT/CROS/SPAN/HPB/ZABA/INA comps je uz to placeholder (conf 0,3 — nema peer skupa) pa po postojećim pravilima ništa ne može 'preglasati' sidro.

**Reverse-r potvrđuje Borisovu hipotezu, uz jednu poštenu ogradu**: kod 6 imena s pozitivnim raskorakom > 30% i r-ovisnim sidrom, implicirani r sidrene metode (onaj koji izjednačava našu projekciju s tržišnom cijenom) je **5.5–6.8%**, dok mi tim istim imenima računamo znatno više (naš r po svih 17 imena: 7.8–12.5%). Puni raspon implied r po SVIM imenima je širi (do 14,6% kod KOEI — protuprimjeri u §2). Dio tog klina je r-stack (FAZA K), ali dio je i to što je 'naša projekcija' trailing godišnja bez TTM-a i bez rasta — pa se klin dijeli između K i G. Cilj v3 NIJE zatvoriti raskorak prema tržištu, nego ukloniti dokazane metodološke greške; preostala razlika je činjenica koju prikazujemo.

## 1. Zbirna tablica — top 15 po prometu (+ CROS i INA iz naloga)

| # | Dionica | Arhetip | Sidro | Fer-zona € | Cijena € | Raskorak vs sredina | r | β (porijeklo) | nelikv. | g1 | ROE (FY) |
|--:|---------|---------|-------|-----------:|---------:|--------------------:|----:|--------------|--------:|-----|---------:|
| 1 | **KOEI** | holding_operating | sotp_nav | 880–925 | 1,040.00 | +15.2% | 12.54% | 1.57 (regresija) | +0.0 p.b. | 20.0%F | 23.3% (FY2025) |
| 2 | **KODT** | industrial_forward | dcf_fcf | 3,833–4,869 | 4,480.00 | +3.0% | 12.10% | 1.49 (regresija) | +0.0 p.b. | 9.5%F | 41.4% (FY2025) |
| 3 | **ADRS** | holding_passive | sotp_nav | 96–101 | 160.00 | +62.6% | 9.40% | 1.01 (regresija) | +0.0 p.b. | 9.4%H | 5.5% (FY2025) |
| 4 | **DLKV** | industrial_forward | dcf_fcf | 5–6 | 17.15 | +197.4% | 11.94% | 1.46 (regresija) | +0.0 p.b. | 8.0%F | 14.1% (FY2025) |
| 5 | **ADPL** | industrial_forward | dcf_fcf | 21–31 | 30.70 | +18.1% | 11.07% | 1.31 (regresija) | +0.0 p.b. | 5.0%F | 12.5% (FY2025) |
| 6 | **HT** | industrial_noforward | justified_pb_roe | 20–28 | 41.00 | +74.2% | 8.34% | 0.83 (regresija) | +0.0 p.b. | — | 8.8% (FY2025) |
| 7 | **ZABA** | bank | justified_pb_roe | 19–26 | 22.60 | -0.1% | 9.50% | 1.03 (regresija) | +0.0 p.b. | 3.0%F | 19.3% (FY2025) |
| 8 | **RIVP** | tourism | comps | 4–6 | 8.60 | +73.7% | 8.08% | 0.79 (regresija) | +0.0 p.b. | — | 13.8% (FY2025) |
| 9 | **PODR** | industrial_forward | comps | 246–333 | 160.00 | -44.8% | 7.96% | 0.76 (regresija) | +0.0 p.b. | 8.0%F | 18.6% (FY2025) |
| 10 | **ZITO** | industrial_noforward | comps | 17–23 | 18.60 | -9.0% | 7.83% | 0.74 (regresija) | +0.0 p.b. | — | 9.6% (FY2025) |
| 11 | **IG** | industrial_noforward | comps | 56–75 | 75.40 | +15.3% | 8.49% | 0.86 (regresija) | +0.0 p.b. | — | 80.0% (FY2024) |
| 12 | **ERNT** | industrial_noforward | justified_pb_roe | 147–195 | 202.00 | +18.3% | 9.67% | 1.06 (sektorska (nema serije)) | +0.0 p.b. | — | 25.4% (FY2025) |
| 13 | **SPAN** | industrial_noforward | justified_pb_roe | 32–43 | 56.60 | +52.3% | 9.26% | 0.99 (regresija) | +0.0 p.b. | — | 15.3% (FY2025) |
| 14 | **HPB** | bank | justified_pb_roe | 310–432 | 334.00 | -9.9% | 8.57% | 0.87 (regresija) | +0.0 p.b. | — | 10.2% (FY2025) |
| 15 | **ATGR** | cyclical | justified_pb_roe | 22–31 | 50.50 | +90.0% | 8.42% | 0.84 (regresija) | +0.0 p.b. | — | 6.8% (FY2025) |
| 16 | **CROS** *(iz naloga)* | insurance | justified_pb_roe | 1,191–1,556 | 3,320.00 | +141.7% | 10.02% | 0.95 (sektorska (nelikvidno)) | +1.0 p.b. | 12.9%H | 7.5% (FY2025) |
| 17 | **INA** *(iz naloga)* | cyclical | dcf_fcf | 81–127 | 505.00 | +386.3% | 10.99% | 1.12 (sektorska (nema serije)) | +1.0 p.b. | — | 10.9% (FY2025) |

*g1: F = forward procjena iz izvješća (growth_estimates), H = povijesni 3g CAGR, — = nema serije (bez faze rasta). ROE: trailing iz zadnjeg godišnjeg (NE TTM). Raskorak = cijena / sredina zone − 1.*

**Napomena o PODR-u**: na živom webu Boris je vidio +200,4% — to je bila zona 14–53 € iz builda PRIJE v2.3 (degenerirano DCF sidro). Tekući kod daje comps sidro 246–333 € i raskorak **−44,8%** (cijena ISPOD zone; napomena o formuli: +200,4% s weba je cijena vs GORNJI rub zone — 160/53,26−1 — dok ovaj izvještaj računa vs SREDINU zone). Ista dionica je u dva uzastopna builda bila 'duboko iznad' pa 'duboko ispod' zone — nestabilnost izbora jednog sidra je sama po sebi nalaz za FAZU A (medijan kvalificiranih metoda).

## 2. Dijagnostika 1 — reverse-r (koji bi r izjednačio projekciju s cijenom)

Bisekcija po r za svaku r-ovisnu metodu s pozitivnom bazom (comps i SOTP ne ovise o r pa reverse-r nemaju). 'n/p' = cijena je izvan raspona koji metoda može dati za r ∈ (g, 40%] — ni ekstremni r ne premošćuje raskorak (tada uzrok NIJE r nego projekcija).

| Dionica | naš r | implied r (po metodi) | klin naš−implied (sidrena/najbliža r-ovisna) |
|---------|------:|-----------------------|---------------------------------------------:|
| KOEI | 12.54% | DCF (FCF): 14.61% | -2.1 p.b. (dcf_fcf) |
| KODT | 12.10% | DCF (FCF): 11.74% | +0.4 p.b. (dcf_fcf) |
| ADRS | 9.40% | (nema r-ovisne metode s bazom) | — |
| DLKV | 11.94% | DCF (FCF): 6.56% | +5.4 p.b. (dcf_fcf) |
| ADPL | 11.07% | DCF (FCF): 10.05% | +1.0 p.b. (dcf_fcf) |
| HT | 8.34% | DCF (FCF): 10.53%; Opravdani P/B: 5.75% | +2.6 p.b. (justified_pb_roe) |
| ZABA | 9.50% | DDM: 9.71%; Opravdani P/B: 9.37%; Rezidualni dohodak: n/p | +0.1 p.b. (justified_pb_roe) |
| RIVP | 8.08% | DCF (FCF): n/p | — |
| PODR | 7.96% | DCF (FCF): 5.41% | +2.6 p.b. (dcf_fcf) |
| ZITO | 7.83% | Opravdani P/B: 7.94% | -0.1 p.b. (justified_pb_roe) |
| IG | 8.49% | Opravdani P/B: 7.92% | +0.6 p.b. (justified_pb_roe) |
| ERNT | 9.67% | DCF (FCF): 9.81%; Opravdani P/B: 8.45% | +1.2 p.b. (justified_pb_roe) |
| SPAN | 9.26% | Opravdani P/B: 6.84% | +2.4 p.b. (justified_pb_roe) |
| HPB | 8.57% | DDM: 10.80%; Opravdani P/B: 9.06%; Rezidualni dohodak: n/p | -0.5 p.b. (justified_pb_roe) |
| ATGR | 8.42% | DCF (FCF): n/p; Opravdani P/B: 5.53% | +2.9 p.b. (justified_pb_roe) |
| CROS | 10.02% | DDM: 8.36%; Opravdani P/B: 5.56%; Rezidualni dohodak: n/p | +4.5 p.b. (justified_pb_roe) |
| INA | 10.99% | DCF (FCF): 5.97%; Opravdani P/B: 5.23% | +5.0 p.b. (dcf_fcf) |

**Čitanje**: kod imena s velikim pozitivnim raskorakom implied r sidrene metode iznosi DLKV 6.6%, HT 5.8%, SPAN 6.8%, ATGR 5.5%, CROS 5.6%, INA 6.0%. Grupiranje je na 5.5–6.8% — dok tim istim imenima računamo 8.3–11.9%. To je smjer koji je Boris predvidio. Ograda: implied r je izračunat nad TRAILING projekcijom (bez TTM-a, kapitalne metode bez rasta), pa 'pravi' klin r-a nakon FAZE G bude manji — dio klina pripada podcijenjenoj projekciji, ne r-u.

Suprotan smjer postoji i dokazuje da se ne radi o univerzalnom 'r je prevelik': KOEI implied 14,6% > naš 12,5% (tržište KOEI vrednuje KONZERVATIVNIJE od nas), KODT implied 11,7% ≈ naš 12,1%, ZABA implied 9,4–9,7% ≈ naš 9,5% (u zoni). Problem je sustavan kod imena sidrenih na kapitalne metode bez rasta i s dvostrukim CRP-om.

## 3. Dijagnostika 2 — metode konvergiraju, sidro divergira

Po STROGOM kriteriju iz naloga (par metoda unutar ±20%, sidro >30% od njihove sredine) tablica je **prazna** — i to je nalaz, a ne 'sve u redu'. Razlozi zašto potvrde danas ne mogu preglasati sidro:

- **DDM je gate-an samo na banke/osiguranje** (v2 §1/§2) — kod industrijskih imena DDM-a nema, pa par 'DDM+comps' ne može ni nastati.
- **Comps je placeholder (conf 0,3) baš tamo gdje je najpotrebniji**: HT, CROS, SPAN, HPB, ZABA, INA nemaju peer skup na ZSE → comps im postoji, ali s multiplima P/E 12 / P/B 1,5 koji nisu podatak.
- **RI ≈ opravdani P/B po konstrukciji** (jednostupanjski RI je matematički identičan opravdanom P/B-u; razlika je samo fade) — pa 'par koji konvergira' najčešće uključuje samo sidrovu blizanku.

Najbliži slučajevi (par unutar ±30%), koji pokazuju ISTI obrazac koji je Boris uočio kod CROS-a:

- **ZABA**: Peer usporedba 14 € i Rezidualni dohodak 11 € (razmak 28%) — sidro Opravdani P/B je +80% od njihove sredine.
- **CROS**: Peer usporedba 3,038 € i DDM 2,396 € (razmak 27%) — sidro Opravdani P/B je -50% od njihove sredine.
- **CROS**: DDM 2,396 € i Rezidualni dohodak 1,939 € (razmak 24%) — sidro Opravdani P/B je -38% od njihove sredine.

**CROS detaljno (slučaj iz naloga)**: DDM 2.396 € (conf 0,7; dvofazni, DPS 114,14 € izglasan 2026., g1 12,9% iz 3g CAGR-a), RI 1.939 € (conf 0,7), comps 3.038 € (conf 0,3, placeholder) — tržište 3.320 €. Sidro opravdani P/B: 1.349 € (trailing ROE 7,5% FY2025, bez rasta, r=10,02% koji uključuje +1 p.b. nelikvidnosti). Model se doista ne slaže sam sa sobom i uvijek sidri na najkonzervativniju polovicu. Napomena: Borisov citat 'DDM 3.670' je sa starije builde (drugačiji DPS ulaz); obrazac je isti, brojka danas 2.396 €.

## 4. Dijagnostika 3 — TTM pokrivenost (kvartali POSTOJE, vrednujemo godišnje)

U bazi **65 firmi ima interim filinge** (M18/M20), a `data()` u `build_ctx` čita `period_type='annual'` — ROE, dobit, prihod, kapital i CF se dakle vrednuju iz zadnjeg GODIŠNJEG. (Jedina iznimka od annual-only pravila: DPS ima fallback na tablicu `dividends` — zadnja IZGLASANA isplata, bez godišnjeg filtra — pa DDM barem koristi svježu dividendu; to je ujedno ulaz koji FAZA DIV zamjenjuje s D_sust.) Za top imena stanje interima:

| Dionica | zadnje godišnje | zadnji interim | stariji interimi | NI u interimu? |
|---------|-----------------|----------------|------------------|----------------|
| KOEI | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| KODT | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ADRS | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| DLKV | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ADPL | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| HT | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ZABA | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | Q1'26 bez NI (FINREP objavljuje polugodišnje) — TTM tek s H1'26 |
| RIVP | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| PODR | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ZITO | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| IG | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ERNT | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| SPAN | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| HPB | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| ATGR | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2024 | da (dobit+prihod+kapital) |
| CROS | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |
| INA | FY2025 | q1 FY2026 | 9m FY2025; h1 FY2025; q4 FY2025 | da (dobit+prihod+kapital) |

Provjereno na uzorku (ADRS, ATGR, CROS, DLKV, HT, INA, PODR, RIVP, SPAN, KODT...): interim filingi NOSE net_income_parent, prihod i kapital — TTM (FY2025 + Q1'26 − Q1'25) je izračunljiv odmah, za sve sektore. Jedina iznimka u top skupini: ZABA Q1'26 bez NI. Popis svih 65 firmi s interimima je u JSON-u (`ttm_coverage`).

Posljedica ne-TTM-a je asimetrična: firme kojima dobit raste (većina univerzuma 2025–2026) sustavno su podcijenjene jer im i ROE (kapitalne metode) i NI (P/E leća) kasne 6–18 mjeseci za stvarnošću.

## 5. Dijagnostika 4 — ERP/CRP audit (double counting)

- **rf = 3.61%** — izvor (iz koda): rf=3,61%: HR 10g državna obveznica, TradingEconomics (tradingeconomics.com/croatia/government-bond-yield, sredina 2026); cross-check ZSE RHMF-O-357A YTM~2,94% @ close 100,50 (zadnja trgovina 02.01.2026 — nelikvidno, starije od rasta prinosa)
- **ERP = 5.7%** — izvor (iz koda): ERP=5,7%: Damodaran (pages.stern.nyu.edu, tablica siječanj 2026): zreli ERP 4,23% + CRP za Moody's A3 (HR A3 stabilno, Moody's 11/2024); A3 EU zemlje (Portugal) u bandi 5,0–5,8% (germanpedia.com/eu-equity-risk-premiums). TOČAN HR REDAK NEPROVJEREN (egress 403) — erp_exact_unverified=true
- **Beta**: likvidna imena regresijska (OLS tjedni log-prinosi vs CROBEX, Blume 0,67β+0,33); ispod praga likvidnosti sektorska (Damodaran Europe, relever); clamp [0,7, 1,8].
- **Premija nelikvidnosti**: +1,0 p.b. ispod praga (≥60% trgovanih dana i ≥1.000 €/dan), +2,0 p.b. za vrlo nelikvidne — ZASEBNA komponenta r-a.

**Nalazi**:

1. ERP=5,7% = zreli 4,23% + CRP za Moody's A3 (~1,47 p.b.) — CRP je SKRIVEN u ERP-u, nije zasebna komponenta. Nelikvidnosna premija se dodaje ZASEBNO (samo ispod Z1 praga) pa formalnog double counta CRP+CRP nema, ali: (a) CRP nije vidljiv u raspisu; (b) rf je HR 10g (3,61%) koji VEĆ NOSI hrvatski spread naspram Bunda — zemlja se naplaćuje i u rf i u ERP-u = DOUBLE COUNT rizika zemlje; (c) A3/A- eurozona 2026. ne opravdava CRP iz starijih tablica.
2. **Premija nelikvidnosti je primijenjena ISPRAVNO po tekućim (Z1) pravilima**: nijedno od 15 likvidnih imena je NEMA (svi prolaze prag); nose je samo CROS i INA (+1,0 p.b.), koji prag likvidnosti doista ne prolaze. Zahtjev K.3 je dakle već zadovoljen — u FAZI K treba samo test koji to trajno čuva.
3. **Kvantifikacija double counta**: uz β=1 danas r = 3,61 + 5,70 = 9,31%. Konzistentan stack: EUR bezrizični (10g Bund, ~2,6–2,7% u 2026.) + zreli ERP 4,23% + JEDAN eksplicitni CRP ≤1,5 p.b. (HR je 'A-'/A3, eurozona, investment grade) → r(β=1) = 8,33–8,43%. Razlika ~0,9–1,0 p.b. sustavno tereti SVAKO ime; uz β>1 (KOEI grupa 1,46–1,57) klin se množi.
4. Damodaranove tablice su u kodu označene `exact_unverified` (egress 403 na pages.stern.nyu.edu) — FAZA K zadržava praksu ručnog unosa s datumom i flagom.

## 6. Puni raspis po dionici (svi ulazi, sve metode, sidro i zašto)

### KOEI — holding · holding_operating

- **r = 12.54%** = rf 3.61% + β 1.57 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (97% dana, 905,595 €/dan)
- **ROE 23.3%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 20.0% · g1=20.0%: FORWARD procjena iz GI FY2025 (pravilo R1; backlog 2,7 mlrd € (+31,1% g/g), book-to-bill 1,5, prodaja +25,2%). g1=20% = min(ostvareni rast prodaje +25,2%, rast backloga +31,1%, CAP 20%) — R1: backlog pokriva ~2
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 693.52 | 815.91 | 938.30 | 0.6 | ne ovisi o r |
| DCF (FCF) | 1,152.03 | 1,282.23 | 1,447.04 | 0.7 | 14.61% |
| SOTP/NAV **(SIDRO)** | 879.68 | 902.83 | 925.98 | 0.6 | ne ovisi o r |

- **Zona 880–925 €** (sotp_nav); cijena 1,040.00 € → raskorak vs sredina **+15.2%**
- top-10 dioničara drži **71.4%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: dcf_fcf +42% vs primarno sidro — uskladi pretpostavke, ne širi zonu

### KODT — industrial · industrial_forward

- **r = 12.10%** = rf 3.61% + β 1.49 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (96% dana, 111,631 €/dan)
- **ROE 41.4%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 9.5% · g1=9.5%: FORWARD procjena iz GI FY2025 (pravilo R1; backlog 987,5 M€ (+20,1% g/g), book-to-bill 1,33, prodaja +9,5%). g1=9,5% = min(ostvareni rast prodaje +9,5%, rast backloga +20,1%, cap 20%) — R1: kapacitet je ograniče
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 11,075.68 | 13,030.21 | 14,984.74 | 0.7 | ne ovisi o r |
| DCF (FCF) **(SIDRO)** | 3,833.32 | 4,286.95 | 4,868.52 | 0.7 | 11.74% |

- **Zona 3,833–4,869 €** (dcf_fcf); cijena 4,480.00 € → raskorak vs sredina **+3.0%**
- **Klase naspram iste zone**: KODT 4,480.00 € (+3.0%); KODT2 4,280.00 € (-1.6%)
- top-10 dioničara drži **84.2%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: comps +199% vs primarno sidro — uskladi pretpostavke, ne širi zonu
- QA: metode se međusobno razilaze 67% (sve metode) — provjeri ulaze/pretpostavke

### ADRS — holding · holding_passive

- **r = 9.40%** = rf 3.61% + β 1.01 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (77% dana, 19,229 €/dan)
- **ROE 5.5%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 9.4% · g1=9.4%: CAGR prihoda FY2023->FY2025 iz baze (cap 0-20%) — POVIJESNI proxy jer forward procjena (backlog/guidance) još nije ekstrahirana; eksplicitna faza 5 g s fadeom prema terminalnom g
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 57.51 | 67.66 | 77.80 | 0.7 | ne ovisi o r |
| SOTP/NAV **(SIDRO)** | 95.90 | 98.42 | 100.95 | 0.6 | ne ovisi o r |

- **Zona 96–101 €** (sotp_nav); cijena 160.00 € → raskorak vs sredina **+62.6%**
- **Klase naspram iste zone**: ADRS 160.00 € (+62.6%); ADRS2 103.50 € (+5.2%)
- top-10 dioničara drži **66.0%** (proxy za free float)
- QA: fer-zona odstupa +63% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### DLKV — industrial · industrial_forward

- **r = 11.94%** = rf 3.61% + β 1.46 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (97% dana, 131,622 €/dan)
- **ROE 14.1%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 8.0% · g1=8.0%: FORWARD procjena iz GI FY2025 (pravilo R2; bez brojčanog backloga; prihodi Grupe +43%, uprava očekuje 'značajnu konjunkturu' (zelena tranzicija)). g1=8% = min(ostvareni rast prihoda Grupe +43% / 2, cap 8%) — R2:
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 3.98 | 4.68 | 5.38 | 0.7 | ne ovisi o r |
| DCF (FCF) **(SIDRO)** | 5.07 | 5.68 | 6.47 | 0.7 | 6.56% |

- **Zona 5–6 €** (dcf_fcf); cijena 17.15 € → raskorak vs sredina **+197.4%**
- top-10 dioničara drži **92.8%** (proxy za free float)
- QA: fer-zona odstupa +197% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### ADPL — industrial · industrial_forward

- **r = 11.07%** = rf 3.61% + β 1.31 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (96% dana, 123,865 €/dan)
- **ROE 12.5%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 5.0% · g1=5.0%: FORWARD procjena iz GI FY2025 (pravilo R0; BROJČANI guidance uprave: rast prihoda 5% godišnje kroz 3 g, EBITDA marža 13%, CAPEX 8 M€/g). g1=5% = izravni guidance uprave (R0): 'U narednom trogodišnjem razdoblju o
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 42.98 | 50.57 | 58.15 | 0.7 | ne ovisi o r |
| DCF (FCF) **(SIDRO)** | 21.42 | 25.35 | 30.58 | 0.7 | 10.05% |

- **Zona 21–31 €** (dcf_fcf); cijena 30.70 € → raskorak vs sredina **+18.1%**
- top-10 dioničara drži **54.1%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: comps +94% vs primarno sidro — uskladi pretpostavke, ne širi zonu

### HT — telecom · industrial_noforward

- **r = 8.34%** = rf 3.61% + β 0.83 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (97% dana, 120,834 €/dan)
- **ROE 8.8%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 19.05 | 22.41 | 25.77 | 0.3 | ne ovisi o r |
| DCF (FCF) | 49.88 | 61.10 | 79.05 | 0.6 | 10.53% |
| Opravdani P/B **(SIDRO)** | 19.51 | 22.85 | 27.57 | 0.7 | 5.75% |

- **Zona 20–28 €** (justified_pb_roe); cijena 41.00 € → raskorak vs sredina **+74.2%**
- top-10 dioničara drži **79.7%** (proxy za free float)
- QA: metode se međusobno razilaze 63% (sve metode) — provjeri ulaze/pretpostavke
- QA: fer-zona odstupa +74% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### ZABA — bank · bank

- **r = 9.50%** = rf 3.61% + β 1.03 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (97% dana, 111,931 €/dan)
- **ROE 19.3%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 3.0% · g1=3.0%: FORWARD procjena iz GI FY2025 (pravilo R3; banka bez guidance-a: dobit +2,9% uz krediti +16,1% — rast dobiti ograničen maržom, ne volumenom). g1=3% ≈ ostvareni rast neto dobiti +2,9% (FY2025) — R3: uprava ne daj
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 11.78 | 13.86 | 15.94 | 0.3 | ne ovisi o r |
| DDM | 19.85 | 23.45 | 28.66 | 0.7 | 9.71% |
| Opravdani P/B **(SIDRO)** | 19.39 | 22.16 | 25.85 | 0.7 | 9.37% |
| Rezidualni dohodak | 10.61 | 10.79 | 10.98 | 0.7 | — |

- **Zona 19–26 €** (justified_pb_roe); cijena 22.60 € → raskorak vs sredina **-0.1%**
- top-10 dioničara drži **97.3%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: residual_income -52% vs primarno sidro — uskladi pretpostavke, ne širi zonu

### RIVP — tourism · tourism

- **r = 8.08%** = rf 3.61% + β 0.79 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (97% dana, 109,903 €/dan)
- **ROE 13.8%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba **(SIDRO)** | 4.21 | 4.95 | 5.69 | 0.7 | ne ovisi o r |
| DCF (FCF) | -9.15 | -10.71 | -13.30 | 0.6 | — |

- **Zona 4–6 €** (comps); cijena 8.60 € → raskorak vs sredina **+73.7%**
- top-10 dioničara drži **61.5%** (proxy za free float)
- QA: metode se međusobno razilaze 316% (sve metode) — provjeri ulaze/pretpostavke
- QA: fer-zona odstupa +74% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### PODR — consumer · industrial_forward

- **r = 7.96%** = rf 3.61% + β 0.76 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (96% dana, 86,746 €/dan)
- **ROE 18.6%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 8.0% · g1=8.0%: FORWARD procjena iz GI FY2025 (pravilo R2; završen investicijski ciklus 250 M€ (capex se normalizira), akvizicija Agri segmenta (grupa >1 mlrd € prihoda), Strategija 2030 — bez brojčanog guidance-a). g1=8% (cap 
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba **(SIDRO)** | 246.28 | 289.74 | 333.20 | 0.7 | ne ovisi o r |
| DCF (FCF) | 14.18 | 28.78 | 53.26 | 0.7 | 5.41% |

- **Zona 246–333 €** (comps); cijena 160.00 € → raskorak vs sredina **-44.8%**
- top-10 dioničara drži **78.6%** (proxy za free float)
- QA: metode se međusobno razilaze 90% (sve metode) — provjeri ulaze/pretpostavke

### ZITO — consumer · industrial_noforward

- **r = 7.83%** = rf 3.61% + β 0.74 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (94% dana, 74,241 €/dan)
- **ROE 9.6%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba **(SIDRO)** | 17.37 | 20.43 | 23.50 | 0.7 | ne ovisi o r |
| Opravdani P/B | 15.96 | 18.95 | 23.33 | 0.7 | 7.94% |

- **Zona 17–23 €** (comps); cijena 18.60 € → raskorak vs sredina **-9.0%**
- top-10 dioničara drži **89.2%** (proxy za free float)

### IG — industrial · industrial_noforward

- **r = 8.49%** = rf 3.61% + β 0.86 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (94% dana, 66,809 €/dan)
- **ROE 80.0%** iz NI FY2024 / kapital FY2024 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba **(SIDRO)** | 55.58 | 65.39 | 75.19 | 0.7 | ne ovisi o r |
| Opravdani P/B | 58.39 | 68.12 | 81.76 | 0.7 | 7.92% |

- **Zona 56–75 €** (comps); cijena 75.40 € → raskorak vs sredina **+15.3%**
- top-10 dioničara drži **82.8%** (proxy za free float)

### ERNT — industrial · industrial_noforward

- **r = 9.67%** = rf 3.61% + β 1.06 (sektorska (nema serije)) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (95% dana, 54,801 €/dan)
- **ROE 25.4%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 135.95 | 159.94 | 183.93 | 0.3 | ne ovisi o r |
| DCF (FCF) | 178.46 | 206.45 | 246.43 | 0.6 | 9.81% |
| Opravdani P/B **(SIDRO)** | 147.01 | 167.50 | 194.62 | 0.7 | 8.45% |

- **Zona 147–195 €** (justified_pb_roe); cijena 202.00 € → raskorak vs sredina **+18.3%**
- top-10 dioničara drži **65.5%** (proxy za free float)

### SPAN — technology · industrial_noforward

- **r = 9.26%** = rf 3.61% + β 0.99 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (96% dana, 53,707 €/dan)
- **ROE 15.3%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 27.24 | 32.05 | 36.86 | 0.3 | ne ovisi o r |
| Opravdani P/B **(SIDRO)** | 31.67 | 36.35 | 42.67 | 0.7 | 6.84% |

- **Zona 32–43 €** (justified_pb_roe); cijena 56.60 € → raskorak vs sredina **+52.3%**
- top-10 dioničara drži **61.3%** (proxy za free float)
- QA: fer-zona odstupa +52% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### HPB — bank · bank

- **r = 8.57%** = rf 3.61% + β 0.87 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (91% dana, 50,910 €/dan)
- **ROE 10.2%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 329.33 | 387.44 | 445.56 | 0.3 | ne ovisi o r |
| DDM | 407.25 | 496.28 | 635.11 | 0.7 | 10.80% |
| Opravdani P/B **(SIDRO)** | 309.80 | 360.80 | 431.90 | 0.7 | 9.06% |
| Rezidualni dohodak | 287.45 | 292.46 | 297.65 | 0.7 | — |

- **Zona 310–432 €** (justified_pb_roe); cijena 334.00 € → raskorak vs sredina **-9.9%**
- top-10 dioničara drži **94.4%** (proxy za free float)

### ATGR — consumer · cyclical

- **r = 8.42%** = rf 3.61% + β 0.84 (regresija) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 0.0 p.b. · likvidnosni prag: prolazi (91% dana, 32,648 €/dan)
- **ROE 6.8%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 28.11 | 33.07 | 38.03 | 0.7 | ne ovisi o r |
| DCF (FCF) | -9.56 | -9.14 | -8.48 | 0.6 | — |
| Opravdani P/B **(SIDRO)** | 22.09 | 25.82 | 31.07 | 0.7 | 5.53% |

- **Zona 22–31 €** (justified_pb_roe); cijena 50.50 € → raskorak vs sredina **+90.0%**
- top-10 dioničara drži **89.0%** (proxy za free float)
- QA: metode se međusobno razilaze 128% (sve metode) — provjeri ulaze/pretpostavke
- QA: fer-zona odstupa +90% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### CROS — insurance · insurance

- **r = 10.02%** = rf 3.61% + β 0.95 (sektorska (nelikvidno)) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 1.0 p.b. · likvidnosni prag: NE prolazi (39% dana, 5,068 €/dan)
- **ROE 7.5%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = 12.9% · g1=12.9%: CAGR prihoda FY2023->FY2025 iz baze (cap 0-20%) — POVIJESNI proxy jer forward procjena (backlog/guidance) još nije ekstrahirana; eksplicitna faza 5 g s fadeom prema terminalnom g
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 2,582.24 | 3,037.93 | 3,493.63 | 0.3 | ne ovisi o r |
| DDM | 2,051.99 | 2,396.42 | 2,878.08 | 0.7 | 8.36% |
| Opravdani P/B **(SIDRO)** | 1,191.11 | 1,349.40 | 1,556.21 | 0.7 | 5.56% |
| Rezidualni dohodak | 1,906.65 | 1,938.95 | 1,972.40 | 0.7 | — |

- **Zona 1,191–1,556 €** (justified_pb_roe); cijena 3,320.00 € → raskorak vs sredina **+141.7%**
- **Klase naspram iste zone**: CROS 3,320.00 € (+141.7%); CROS2 3,360.00 € (+144.6%)
- top-10 dioničara drži **99.0%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: residual_income +41% vs primarno sidro — uskladi pretpostavke, ne širi zonu
- QA: fer-zona odstupa +142% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

### INA — industrial · cyclical

- **r = 10.99%** = rf 3.61% + β 1.12 (sektorska (nema serije)) × ERP 5.7% (uklj. skriveni CRP) + nelikvidnost 1.0 p.b. · likvidnosni prag: NE prolazi (48% dana, 3,301 €/dan)
- **ROE 10.9%** iz NI FY2025 / kapital FY2025 — zadnje GODIŠNJE konsolidirano (ne TTM)
- **g**: g1 = — · nema serije — bez faze rasta
- **kapitalni g 2.5% / terminalni g 4.0%**

| Metoda | low | base | high | conf | implied r |
|--------|----:|-----:|-----:|-----:|----------:|
| Peer usporedba | 197.71 | 232.60 | 267.48 | 0.3 | ne ovisi o r |
| DCF (FCF) **(SIDRO)** | 80.72 | 100.53 | 126.95 | 0.6 | 5.97% |
| Opravdani P/B | 145.42 | 162.54 | 184.23 | 0.7 | 5.23% |

- **Zona 81–127 €** (dcf_fcf); cijena 505.00 € → raskorak vs sredina **+386.3%**
- top-10 dioničara drži **99.0%** (proxy za free float)
- QA: ULAZI NEKONZISTENTNI: justified_pb_roe +57% vs primarno sidro — uskladi pretpostavke, ne širi zonu
- QA: fer-zona odstupa +386% od tržišta — mogući propust u pretpostavkama (rast, arhetip, jedinice) ili tržišni raskorak; tretiraj kao pitanje, ne zaključak

## 7. Interne kontradikcije iz naloga — potvrđene

- **ADRS vs ADRS2**: ista fer-zona (96–101 €), a ADRS 160.00 € je +62.6% dok je ADRS2 103.50 € +5.2% — ista firma, dvije priče. Redovna trguje ~55% iznad povlaštene (glasačka premija) — FAZA S raspoređuje vrijednost firme tržišnim omjerom klasa. KODT/KODT2 su usporedbe radi konzistentne (+3,0% / −1,6%), CROS/CROS2 blizu (+141,7% / +144,6%).
- **CROS se ne slaže sam sa sobom**: vidi §3 — DDM/RI/comps 1.939–3.038 €, sidro 1.349 €, tržište 3.320 €.
- **PODR**: +200% (stara builda, degenerirani DCF) → −45% (v2.3 comps) — izbor jednog sidra proizvodi diskontinuitete od 245 p.b. raskoraka bez ijedne nove brojke u bazi.
- **INA**: top-10 dioničara 99% (MOL + RH ≈ 94%, free float <5%): cijena se formira u plitkoj knjižici bez floata — raskorak +386% NIJE informativan; FAZA A.4 iznimka (napomena + isključenje iz 'temperature tržišta'). Isto vrijedi provjeriti za CROS (top-10 99%, u čemu je ADRS-ov udjel ~67% i nelikvidnost ispod praga).
- **HT ilustracija za FAZU A** (dijagnostika, ne meta): kvalificirane metode {DCF 61,1 (conf 0,6), opravdani P/B 22,8 (conf 0,7)} — medijan ~42 € naspram cijene 41 €. Današnja zona: 20–28 €. Sidro na jednoj metodi baca informaciju koju druga nosi.
- **HT nema ni 3g serije prihoda u bazi** (samo FY2025 godišnje) — zato g1 = — i jednofazni Gordon; backfill FY2023–FY2024 GODIŠNJIH je dio FAZE G pretpostavki (interimi za HT postoje od FY2024).

## 8. Mapa: nalaz → faza koja ga rješava

| Nalaz | Faza | Očekivani smjer |
|-------|------|-----------------|
| rizik zemlje dvaput (HR rf + CRP u ERP-u), CRP skriven | **K** | r(β=1) 9,31% → ~8,3–8,4%; raspis rf+β×ERP+CRP+nelikv. vidljiv po dionici |
| trailing godišnje umjesto TTM (65 firmi ima kvartale) | **G** | ROE/NI/prihod na TTM; badge `godišnji podatak` gdje kvartala nema |
| kapitalne metode bez faze rasta (sidro 7/17 imena) | **G** | g1 iz 3g CAGR-a s capom i fadeom; ROE pravilo max(3g medijan, TTM×0,9) |
| sirova zadnja dividenda u DDM (jednokratne iskrivljuju) | **DIV** | D_sust (održivi payout × normalizirana dobit), pokrivenost najave |
| dogma jednog sidra (PODR flip, HT/CROS kontradikcije) | **A** | zona = medijan kvalificiranih metoda; demote pravilo; dividendni sanity flag |
| ADRS/ADRS2 ista zona, klase ±55% razmaknute | **S** | vrijednost firme × tržišni omjer klasa (medijan 3–5g) |
| raskorak >30% bez narativa; distribucijski alarm | **P** | reverse-DCF okvir svugdje; alarm >40% top-20; changelog v3 + priznate greške |

**Kontrolne točke za acceptance v3**: ZABA mora ostati u zoni ili blizu (danas −0,1%); CROS nova zona mora pomiriti DDM/RI/sidro; ako i NAKON svega >40% top-20 ostane s |raskorakom|>30%, NE fitamo — isporučuje se reverse-DCF dokaz po imenu i eskalira Borisu.

---
*MAR napomena: ovaj dokument je interna dijagnostika modela. Ništa u njemu nije preporuka, rejting ni ciljna cijena; pozicija cijene naspram zone je činjenica, zaključak je čitateljev.*

---

## Dodatak (FAZA SOTP, 16.07.2026.) — razdvajanje kaskade za matice

Napomena: brojke ispod su NAKON primjene v3 faza K–S i SOTP pravila
(komponente su već rekalibrirane); u v2 stanju uvezeni dio je bio veći
(CROS zona ~pola tržišta prelijevala se u ADRS kroz fer-procjenu kćeri).
Metoda: zona matice s kćerima po NAŠOJ fer-procjeni naspram zone s
kćerima po TRŽIŠNOJ kapitalizaciji (obje brojke postoje u SOTP raspisu:
`sotp_fair` / `sotp_market`); razlika = uvezeni dio raskoraka.

| Matica | Cijena | Zona-mid (kćeri naša procjena) | Zona-mid (kćeri po tržištu) | Ukupni raskorak | UVEZENI dio | VLASTITI dio (standalone + diskont) |
|--------|-------:|------------------------------:|----------------------------:|----------------:|------------:|------------------------------------:|
| KOEI   | 1.040,00 | 847,0 | 960,5 | +22,8% | **+14,5 p.b.** | +8,3 p.b. |
| ADRS   | 160,00 | 79,4 | 90,1 | +101,6% | **+24,1 p.b.** | +77,5 p.b. |

Čitanje: kod KOEI-ja je ~2/3 raskoraka uvezeno iz raskoraka uvrštenih
kćeri (KODT, DLKV) — potvrda hipoteze o kaskadi. Kod ADRS-a uvezeni dio
postoji (+24 p.b.), ali dominira vlastiti: tržište plaća premiju i na NAV
s kćerima po tržišnim cijenama (holding diskont, multiple neuvrštenih,
premija glasa redovne klase — vidi FAZU S). SOTP komponente sada:
KPT po knjigovodstvenoj vrijednosti iz bilješke 16 (44,2 M€, uz vidljivu
napomenu da JV godišnje donosi ~43,6 M€ udjela u dobiti), KOEI standalone
"u obradi" (nekonsolidirani izvještaj izdan zasebno, nije u bazi — ne
aproksimira se).
