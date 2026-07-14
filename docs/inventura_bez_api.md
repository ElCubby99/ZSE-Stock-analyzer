# Inventura pokrivenosti — bez ijednog API poziva

**Punih analiza: 65** | market_only: 5

## Pune analize (godišnje financije u bazi, valuacija v2.1 + pokazatelji)

| Ticker | Sektor | Zadnji FY | Interim perioda | Napomena |
|---|---|---|---|---|
| ACI | n/p | 2025 | 9 |  |
| ADPL | industrial | 2025 | 9 |  |
| ADRS | holding | 2025 | 9 |  |
| ARNT | tourism | 2025 | 9 |  |
| ATGR | consumer | 2025 | 8 |  |
| AUHR | n/p | 2025 | 9 |  |
| CIAK | n/p | 2025 | 9 |  |
| CKML | consumer | 2025 | 9 |  |
| CRAL | n/p | 2025 | 9 |  |
| CROS | insurance | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| CTKS | industrial | 2025 | 7 |  |
| DDJH | n/p | 2025 | 9 |  |
| DLKV | industrial | 2025 | 9 |  |
| DLPR | n/p | 2025 | 9 |  |
| ERNT | industrial | 2025 | 9 |  |
| GARB | holding | 2025 | 9 |  |
| GRNL | consumer | 2025 | 9 |  |
| HEFA | tourism | 2025 | 9 |  |
| HIMR | tourism | 2025 | 9 |  |
| HPB | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| HT | telecom | 2025 | 9 |  |
| IG | industrial | 2025 | 5 |  |
| IGH | n/p | 2025 | 8 |  |
| IKBA | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| ILRA | tourism | 2025 | 9 |  |
| INA | industrial | 2025 | 9 |  |
| INGR | n/p | 2025 | 9 |  |
| JDGT | industrial | 2025 | 9 |  |
| JDPL | shipping | 2025 | 9 |  |
| JDRN | tourism | 2025 | 9 |  |
| KBZ | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| KODT | industrial | 2025 | 9 |  |
| KOEI | holding | 2025 | 9 |  |
| KRAS | consumer | 2025 | 9 |  |
| KTJV | consumer | 2025 | 9 |  |
| LKPC | industrial | 2025 | 9 |  |
| LKRI | industrial | 2025 | 9 |  |
| LPLH | shipping | 2025 | 9 |  |
| LRH | tourism | 2025 | 9 |  |
| MAIS | tourism | 2025 | 9 |  |
| MDSP | tourism | 2025 | 9 |  |
| MONP | tourism | 2025 | 9 |  |
| MRSK | consumer | 2025 | 9 |  |
| PDBA | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| PLAG | tourism | 2025 | 9 |  |
| PODR | consumer | 2025 | 8 |  |
| QTLG | n/p | 2025 | 9 |  |
| RIVP | tourism | 2025 | 9 |  |
| SNBA | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| SPAN | technology | 2025 | 9 |  |
| STJD | n/p | 2025 | 9 |  |
| THNK | industrial | 2025 | 9 |  |
| TKPR | consumer | 2025 | 9 |  |
| TOK | consumer | 2025 | 2 |  |
| TRFM | n/p | 2025 | 9 |  |
| ULPL | shipping | 2024 | 9 |  |
| VDZG | industrial | 2025 | 9 |  |
| VIDU | tourism | 2025 | 9 |  |
| VIS | tourism | 2025 | 9 |  |
| VJSN | n/p | 2025 | 9 |  |
| VLEN | shipping | 2025 | 9 |  |
| ZABA | bank | 2025 | 0 | nadzorni obrazac — interim (FINREP layout) traži zaseban parser; TTM = n/p, FY s oznakom |
| ZB | other | 2025 | 9 |  |
| ZITO | consumer | 2025 | 4 |  |
| ZPKL | consumer | 2025 | 10 |  |

## market_only — što TOČNO fali (za odluku isplati li se API)

| Ticker | Ime | Što fali |
|---|---|---|
| BRIN | ZAIF Breza d.d. | ZAIF obrazac (invest. fond) — XLSX postoji, ali fond-forma (Ulaganja/NAV) traži zaseban parser + P/NAV pristup; nije industrijska taksonomija. API ne pomaže bez tog pristupa. |
| BSQR | BSQR | NEMA nijednog financijskog izvješća na EHO feedu (ni PDF ni XLSX) — ne vrijedi trošiti API; čekati prvu objavu. |
| INSP | INSPIRIO ZAIF d.d. | ZAIF — nema XLSX/PDF financijskih izvješća na EHO feedu. |
| JNAF | JANAF, d.d. | SAMO PDF izvješća na EHO (nema TFI XLSX) — kandidat za API ekstrakciju (FY2025 godišnje PDF postoji). |
| UCG | UniCredit S.p.A. (Milano) | Strani izdavatelj (UniCredit, Milano) — ne objavljuje TFI/EHO obrasce; izvješća su talijanska/engleska PDF na vlastitim stranicama. Kandidat za API ekstrakciju iz PDF-a. |

Napomena: sve gore ekstrahirano je deterministički iz EHO XLSX obrazaca (TFI-POD, nadzorni bankovni, financijsko-uslužna varijanta) kroz validate gate — 0 API poziva. Skenirani PDF-ovi (bivši CTKS/KTJV problem) više nisu blokada jer izdavatelji od FY2025 objavljuju XLSX.
