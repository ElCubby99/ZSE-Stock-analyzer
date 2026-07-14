# Inventura pokazatelja (KORAK 1a) — stanje 14.07.2026.

Razvrstavanje ciljnog seta (≥ investiramo.com) prema onome što baza DANAS ima.
Ništa se ne ekstrahira dok Boris ne odobri obuhvat (KORAK 1b tablica:
docs/kvartalna_inventura.md).

## A. IZVEDIVO ODMAH iz baze (FY nazivnici; TTM čim kvartali uđu)

| Grupa | Pokazatelji | Napomena |
|---|---|---|
| Izvedba dionice | povrat 1M/3M/6M/YTD/1G; 52-tj max/min + datumi | prices_eod (2 g povijesti); najbliži trgovani dan; ilikvidne s flagom. **3G povrat = n/p** — serija počinje 07/2024 (proširivo besplatno: securityHistory dublje) |
| Valuacija | trž.kap., P/E, earnings yield, P/S, P/B, P/CF, P/FCF, EV/Prihod, EV/EBITDA, EV/EBIT | EV zasad = trž.kap + dug − novac + manjinski; **kratkoročna fin. imovina fali** (vidi B) |
| Profitabilnost | EBITDA/EBIT/neto marža, ROE, ROA | ✓ |
| Bilanca | imovina, novac, BVPS, kapital, kratkoročni/dugoročni dug; ukupne obveze (izvedeno: imovina − kapital) | ✓ |
| Novčani tok | OCF, capex, FCF | ✓ |
| Solventnost | dug/kapital, neto dug/EBITDA | ✓ |
| Dividende | DPS, prinos, payout, zadnja isplata, sljedeći ex-datum | ✓ (kalendar sa ZSE stranica papira) |
| Učinkovitost | obrtaj imovine | ✓ |

## B. TREBA PROŠIRENJE TAKSONOMIJE + re-parse TFI XLSX — **0 kredita**

Sve stavke ispod POSTOJE u standardiziranom TFI XLSX obrascu (provjereno na
INA obrascu) — treba samo proširiti parser i ponovno provući iste datoteke:

| Nova stavka | Gdje u obrascu | Omogućuje |
|---|---|---|
| employees | Opći podaci: "Broj zaposlenih (krajem razdoblja)" — INA: 9.319 ✓ | prihod/dobit po zaposlenom |
| interest_expense | RDG: retci kamata unutar IV. FINANCIJSKI RASHODI | pokriće kamata |
| current_assets | Bilanca AOP 037 (C. KRATKOTRAJNA IMOVINA) ✓ | tekući omjer, Altman, radni kapital |
| current_liabilities | Bilanca AOP 109 (D. KRATKOROČNE OBVEZE) ✓ | tekući omjer, Altman, novčani jaz |
| short_term_fin_assets | Bilanca AOP 053 ✓ | točan EV (odbitak uz novac) |
| retained_earnings | Bilanca AOP 084 ✓ | Altman Z |
| inventories | Bilanca AOP 038 (ZALIHE) ✓ | DIO |
| trade_receivables | Bilanca: kratkotrajna potraživanja od kupaca | DSO |
| trade_payables | Bilanca: obveze prema dobavljačima (kratkoročne) | DPO |
| investing_cf / financing_cf | NT_I: B) i C) neto tokovi ✓ | CF kartica u cijelosti |

Vrijedi za sve firme s TFI obrascem (ne-banke). **Banke/osiguratelji**:
kvartalni XLSX postoji na EHO-u, ali NADZORNI obrazac (drugi AOP-ovi) —
traži zaseban parser (dio Koraka 2 po odobrenju), ne API.

## C. STRUKTURNO n/p po sektoru (guard, s razlogom na stranici)

- **Banka/osiguranje**: EV/Prihod, EV/EBITDA, EV/EBIT, EBITDA marža, neto
  dug/EBITDA, tekući omjer, DSO/DIO/DPO, Altman Z → "n/p — financijska firma:
  dug i EBITDA nemaju operativno značenje / obrtni ciklus nije primjenjiv".
- **Holding (pasivni)**: DSO/DIO/DPO → n/p (nema robno-novčani ciklus).

## D. Kvartalna inventura — sažetak (puna tablica: docs/kvartalna_inventura.md)

- **TTM minimum (zadnji FY + 26Q1 + 25Q1) iz besplatnog XLSX-a: 56/58 firmi.**
- **Iznimke (2)**: TOK (objave tek od 25Q4 — prije nije objavljivao kvartale na
  EHO), ZITO (od 25Q3). Za njih TTM = n/p dok ne prođe još kvartala; FY s
  oznakom.
- Punih 8+ kvartala u XLSX-u: **40 firmi**; 15 firmi ima 1–4 rupe (tipično
  24Q2 ili neobjavljeni 2Q — polugodišnja objava umjesto kvartalne); IG samo
  5 (godišnji ritam + rijetki kvartali).
- Sve je XLSX — **API NIJE POTREBAN ni za jedan interim backfill** (banke
  trebaju samo novi parser, ne kredite).

## Prijedlog obuhvata backfilla (čeka OK)

1. Svih 58 živih firmi × dostupni kvartali 2024Q2–2026Q1 (XLSX, kroz
   validate gate s period_type + cumulative) — procjena ~450 filinga, 0 kredita.
2. Proširenje taksonomije (tablica B) + re-parse FY-eva svih firmi istim
   prolazom.
3. Bankovni/osigurateljski interim parser (nadzorni obrazac) — druga faza
   istog prolaza.
4. (Opcija) backfill cijena do 2021. za 3G povrat — besplatno, securityHistory.
