# Kalibracija parametara iz tržišnih serija (M10)

Zaseban korak nakon backfilla ~2 godine povijesti cijena (zse.hr
securityHistory + indexHistory, službene javne serije). Pokreće se s
`python -m src.calibrate --all`; rezultati su u tablici `calibrations`
i `params_calibrated` ih čita pri svakoj valuaciji.

## 1. Beta (CAPM ulaz za r = rf + β×ERP)

**Metoda:** OLS nagib tjednih log-prinosa klase prema CROBEX-u
(ISIN HRZB00ICBEX6). Tjedan = zadnji close u ISO tjednu; prinosi SAMO preko
susjednih tjedana (rupe u nelikvidnim serijama ne postaju višetjedni
"prinosi"). Prag kalibracije: ≥ 40 tjednih parova.

**Rezultati (2024-07 → 2026-07, 105 tjedana gdje je serija puna):**

| firma | β | R² | n tj. | firma | β | R² | n tj. |
|---|---|---|---|---|---|---|---|
| ADRS (kl. ADRS2) | 1.023 | 0.38 | 105 | KOEI | 1.851 | 0.36 | 105 |
| ZABA | 1.052 | 0.22 | 105 | KODT | 1.728 | 0.43 | 105 |
| HT | 0.746 | 0.19 | 105 | DLKV | 1.678 | 0.24 | 105 |
| HPB | 0.807 | 0.14 | 105 | ADPL | 1.455 | 0.14 | 105 |
| PODR | 0.645 | 0.10 | 105 | SPAN | 0.986 | 0.19 | 105 |
| RIVP | 0.682 | 0.18 | 105 | ATGR | 0.768 | 0.15 | 105 |
| CROS | 0.759 | 0.06 | 70 | ARNT | 0.548 | 0.11 | 103 |
| IG | 0.796 | 0.24 | 69 | ZITO | 0.625 | 0.10 | 49 |

- **TOK: NEKALIBRIRANO** (33 tjedna < 40 — uvršten krajem 2025.) → β ostaje
  označena pretpostavka 1,0.
- **Ograde:** R² je nizak za većinu (0,06–0,43) — normalno za nelikvidne
  dionice; β je procjena sa širokim intervalom pouzdanosti, ne konstanta.
  Izvor parametra to eksplicitno kaže. CROS β počiva na samo 70 tjedana
  s trgovinom (nelikvidan).
- Učinak na r (rf 3,61% + β×5,7%): npr. ADRS r=9,44%, PODR r=7,29%,
  KOEI r=14,16% — r sada varira po firmi umjesto uniformnih 9,31%.

## 2. Povijesni ADRS holding diskont — NALAZ: premija, ne diskont

**Metoda:** dnevna serija `1 − mcap(ADRS+ADRS2) / NAV_proxy(t)`,
NAV_proxy(t) = 0,6747×mcap(CROS+CROS2) + 0,9354×mcap(MAIS) + 301,9M
(neuvršteni segmenti po FY2025 placeholder multiplama) − 170,7M (neto dug
FY2025). Nelikvidni zadnji close prenosi se najviše 60 dana; n=489 dana
(2024-07-17 → 2026-07-10). MAIS serija backfillana za ovu svrhu.

**Rezultat:** medijan **−12,1%** (p25 −16,4%, p75 −5,3%; min −33,2%,
max +5,5%; zadnje −25,5% na 10.07.2026.) — negativno = tržišna
kapitalizacija ADRS-a je IZNAD proxyja. Tržište kroz gotovo cijeli prozor
cijeni ADRS uz **premiju** na ovaj konzervativni NAV, ne uz diskont.

**Zašto raspon 15–25% NIJE zamijenjen opaženim:** proxy sustavno
podcjenjuje NAV — (a) neuvršteni dijelovi (HUP, Cromaris, Energetika) stoje
na placeholder multiplama, (b) odbija se GRUPNI neto dug koji uključuje i
dug članica već vrednovanih tržišno (dvostruko brojanje), (c) konstante su
zamrznute na FY2025 kroz cijeli prozor. Serija je zato **tržišna usporedba
kroz vrijeme** (proširenje SOTP market_checka), a ne mjera čistog holding
diskonta. Holding diskont 15–25% ostaje OZNAČENA pretpostavka; izvor
parametra sada citira opaženu seriju umjesto starog "neizvedivo iz baze".

## Održavanje

- Re-kalibracija: `python -m src.calibrate --all` (idempotentno; upsert po
  ključu). Preporuka: nakon svakog većeg backfilla ili kvartalno.
- TOK i buduća nova uvrštenja automatski se kalibriraju kad serija dosegne
  40 tjednih parova.
- Fer poboljšanje diskont-serije (kasnije): NAV_proxy s tržišnim multiplama
  za neuvrštene i dug matice umjesto grupnog agregata.
