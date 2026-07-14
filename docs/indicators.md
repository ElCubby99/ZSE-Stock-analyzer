# Pokazatelji — derivacijski sloj (M18)

Sve izvedenice računa **deterministički kod** (`src/indicators.py`), NE LLM.
Svaki pokazatelj nosi `{v, unit, basis, formula}`; kad se ne može izračunati →
`{v: null, np_reason}` (**n/p, nikad 0**).

## Kvartalni sloj i TTM

Sustav trajno vuče i kvartalna (interim) izvješća s EHO-a kao standardizirani
TFI-POD XLSX (0 kredita; `scripts/backfill_interim.py`, ubuduće automatski preko
watchera). IFRS interim je **kumulativan (YTD)** pa se periodi normaliziraju:

| EHO | period_type | značenje |
|---|---|---|
| 1Q | `q1` | 1.1.–31.3. (kumulativ) |
| 2Q | `h1` | 1.1.–30.6. |
| 3Q | `9m` | 1.1.–30.9. |
| 4Q | `q4` | 1.1.–31.12. (= FY kumulativ, nerevidiran) |
| 1Y | `annual` | godišnje (kurirano; valuacija čita OVO) |

**Hijerarhija nazivnika (KORAK 4):** `TTM` > `FY s oznakom` > `—`.
**FY se NIKAD ne prikazuje kao TTM.**

- **TTM (samo tokovne stavke — P&L, CF):**
  `TTM = FY_prošla + YTD_tekuća − YTD_lanjska_isti_period`
  (npr. `TTM_do_31.03.2026 = FY2025 + 1Q2026 − 1Q2025`). Ako bilo koji član
  nedostaje → padni na `FY s oznakom`.
- **Bilanca (stanje):** zadnje objavljeno stanje, oznaka `Kvartalno (dd.mm.gggg.)`
  ili `FYgggg`. Nikad se ne zbraja.
- **Diskretni kvartali:** `Q1 = 1Q`, `Q2 = H1 − 1Q`, `Q3 = 9M − H1`,
  `Q4 = FY − 9M`. Negativan izvedeni kvartal tokovne stavke koja ne može biti
  negativna (prihod) → **needs_review oznaka + isključenje** (restatement se ne
  prikazuje tiho).
- **YoY:** ISKLJUČIVO isti-na-isti period (`2026Q1 vs 2025Q1`) — sezonalnost
  (turizam!) inače laže.

## Sektorski guardovi (n/p s razlogom)

- **Banka / osiguranje:** EV i sve EV-multiple, EBITDA/EBIT marža, neto
  dug/EBITDA, tekući omjer, pokriće kamata, Altman Z', DSO/DIO/DPO, obrtaj
  imovine, P/S → **n/p** (dug i EBITDA nemaju operativno značenje; obrtni ciklus
  nije primjenjiv). Prihod = `total_operating_income` (P/TOI umjesto P/S).
- **Pasivni holding:** DSO/DIO/DPO/obrtaj → **n/p** (nema robno-novčani ciklus).

## Grupe i formule

### 1. Izvedba dionice
Povrat 1M/3M/6M/YTD/1G/3G = `close_zadnji / close_najbliži_ciljnom_danu − 1`
(najbliži **trgovani** dan ≤ ciljni; binarno pretraživanje). 52-tj max/min s
datumima (prozor 365 d). **3G = n/p** dok je serija cijena kraća od 3 g.
Ilikvidne klase nose oznaku „indikativno”.

### 2. Valuacija
- **EV** = `trž.kap + ukupni_dug − novac − kratkoročna_fin_imovina + manjinski_interes`
  (zadnja bilanca). Kratkoročna fin. imovina se odbija uz novac (v2 doktrina).
- EV/Prihod, EV/EBITDA, EV/EBIT (nazivnik TTM/FY tokovni).
- P/E, P/S, P/CF, P/FCF = `trž.kap / {neto dobit matici, prihod, OCF, FCF}`.
- Earnings yield = `neto dobit matici / trž.kap`. P/B = `trž.kap / knjiga matici`.
- Svi omjeri samo kad je nazivnik > 0 (inače n/p).

### 3. Rast
Prihod/EPS YoY (diskretni kvartal, isti-na-isti). Prihod/EBITDA (TTM/FY).

### 4. Profitabilnost
EBITDA/EBIT/neto marža = `{ebitda, ebit, ni_matici} / prihod`.
ROE = `ni_matici / knjiga_matici`. ROA = `ni / ukupna_imovina`.

### 5. Bilanca (zadnje stanje)
Ukupna imovina, novac, BVPS = `knjiga_matici / dionice_ex_trezor`, ukupne obveze
= `imovina − kapital`, kratkoročni/dugoročni dug, ukupni kapital.

### 6. Novčani tok
OCF, capex, FCF = `OCF − capex`, investicijski CF (NT B), financijski CF (NT C).

### 7. Likvidnost i solventnost
- Tekući omjer = `kratkotrajna imovina / kratkoročne obveze`.
- Dug/kapital = `kamatonosni dug / knjiga`.
- Neto dug/EBITDA = `(dug − novac) / EBITDA`.
- Pokriće kamata = `EBIT / rashodi od kamata`.
- **Altman Z' (privatna varijanta, ne izvorni Z):**
  `Z' = 0,717·(WC/TA) + 0,847·(RE/TA) + 3,107·(EBIT/TA) + 0,420·(BVE/TL) + 0,998·(S/TA)`
  gdje WC = tekuća imovina − tekuće obveze, RE = zadržana dobit, BVE = knjiga
  kapitala, TL = ukupne obveze, S = prihod. Zone (Z' < 1,23 distres / 1,23–2,9
  siva / > 2,9 sigurno) su INFORMATIVNE, ne rejting.

### 8. Učinkovitost
Obrtaj imovine = `prihod / imovina`. DSO = `kupci / prihod × 365`.
DIO = `zalihe / materijalni_troškovi × 365` (materijalni troškovi = COGS proxy).
DPO = `dobavljači / materijalni_troškovi × 365`. Novčani jaz = `DSO + DIO − DPO`.

### 9. Dividende
DPS (zadnja), prinos = `DPS / cijena`, payout = `DPS × dionice / neto dobit`,
zadnja isplata, sljedeći ex-datum (kalendar sa ZSE stranica papira).

### 10. Po zaposlenom
Broj zaposlenih (TFI „Opći podaci”), prihod/zaposlenom, dobit/zaposlenom.

## Napomena o statusu izvješća
Interim se validira (bilanca se zatvara, kapital/dobit konzistentni, EBITDA
sanity). YoY „velika promjena” (>±60%) je WARN — legitimno za interim
(sezonalnost, mala baza), ne znači grešku. Indikatori koriste sva
objavljena razdoblja; osnovica (`basis`) uvijek pokazuje IZ KOJEG razdoblja
broj dolazi.
