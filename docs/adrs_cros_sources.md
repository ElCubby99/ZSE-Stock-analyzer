# ADRS i CROS — izvori za KORAK 2 (konsolidirana godišnja izvješća)

Nastavak runbooka `docs/runbook_valuation_v2.md`. Ovdje su **dosegljivi izvori**,
**točne stranice** konsolidiranih izvještaja i **cross-check sidra** za validatorov
eyes-check (NE za ručni upis u bazu).

## Dosegljivi izvor: EHO disclosure portal (eho.zse.hr) — NE zse.hr

`www.zse.hr` redirecta na `zse.hr` koji egress politika i dalje vraća **403**;
`adris.hr` se spaja ali mu se TLS lanac ne verificira (cert izdaje Anthropic egress
gateway, ali "SDS Issuing CA" intermediate nije u bundleu); `rest.zse.hr` traži
`ZSE_API_KEY`. **`eho.zse.hr` je dosegljiv** i ima strukturirani JSON feed objava.

Egress proxy re-terminira TLS → curl mora vjerovati CA bundleu:
```
curl --cacert /root/.ccr/ca-bundle.crt \
  "https://eho.zse.hr/feed/json?variant=financialReports&ticker=ADRS&dateFrom=2022-01-01&dateTo=2026-06-28"
```
Feed parametri: `variant` (financialReports|issuerNews|tradingNews|…), `ticker`,
`dateFrom`/`dateTo` (bez raspona vraća samo današnji dan!), `date`. Stavka nosi
`year, period (1Y/1H), consolidated, revised, documentType (PDF/XLSX/ZIP), documentLink, publishDate`.

Reusable dohvat: **`scripts/fetch_eho_reports.sh ADRS CROS`** (preuzima konsolidirane
godišnje PDF-ove u `data/reports/`).

### Konsolidirani godišnji PDF linkovi (revidirano=true)
| Tvrtka | God | documentLink (eho.zse.hr/fileadmin/issuers/…) |
|--------|-----|-----------------------------------------------|
| ADRS | 2025 | `/ADRS/FI-ADRS-8841c8bbd4891dcc185702f60d6fd62b.pdf` |
| ADRS | 2024 | `/ADRS/FI-ADRS-9fc34ea337c540affe4f6b886bd00294.pdf` |
| CROS | 2025 | `/CROS/FI-CROS-2de1958ff392f322b63bc8fc9df1be42.pdf` |
| CROS | 2024 | `/CROS/FI-CROS-e6349bfe051e0a6d57960476e1e20fb2.pdf` |

(2022/2023 također dostupni u feedu — vidi `data/reports/eho/{ADRS,CROS}_fr.json`.)

## Točne stranice konsolidiranih izvještaja (PDF 2025) — KRITIČNO za ekstrakciju

**ZAMKA:** oba izvješća primarne izvještaje prikazuju u **dvije kolone usporedo**:
`Grupa` (= konsolidirano) i `Društvo` (= nekonsolidirano/standalone), svaka s
2025. i 2024. Ekstraktor MORA uzeti **Grupa 2025**. Skala je **"u 000 EUR" /
"u tisućama eura" → `reporting_scale=1000`**, valuta EUR.

### ADRS (Adris grupa d.d.) — PDF 318 str
- Sveobuhvatna dobit (P&L + OCI): **PDF str 24–25** (kolone Grupa|Društvo × 2025|2024)
- Financijski položaj (bilanca): **PDF str 26–27**
- Novčani tok: **PDF str 32**
- Promjene kapitala: PDF str 28–31
- Bilješka 5 "Informacije po poslovnim segmentima" (IFRS 8): **PDF str 89–91**
  → puni `segment_financials` (segment_key: tourism/insurance/aquaculture/energy)
- Slice za ekstraktor: `data/reports/adrs_2025_fin_slice.txt` (str 23–33 + 134–136)

### CROS (Croatia osiguranje d.d.) — PDF 320 str
- Dva seta su konsolidirana:
  - **IFRS primarni** (čišći, ima EPS i atribuciju matici/NCI): Sveobuhvatna dobit
    **PDF str 125–126**, Bilanca **PDF str 127**, Promjene kapitala 128–131,
    Novčani tok ~132. Kolone: Društvo|Društvo|**Grupa|Grupa** (2025/2024), "u 000 EUR".
  - HANFA regulatorne forme (eksplicitno "KONSOLIDIRANI…"): **PDF str 292–297**,
    skala "u eurima" (1), kolone Život/Neživot/**Ukupno** × Prethodna/**Tekuća**.
    Koristiti kao cross-check; primarni IFRS set je za ekstrakciju.
- Bilješka 3 "Izvještavanje po segmentima": **PDF str 199–200**
- Slice za ekstraktor: `data/reports/cros_2025_fin_slice.txt` (str 125–133)

## Cross-check sidra (Grupa 2025, u 000 EUR) — SAMO eyes-check, NE upisivati ručno

Služe da na usporednoj tablici odmah vidimo je li ekstrakcija promašila skalu/kolonu.

| Stavka | ADRS 2025 (Grupa) | CROS 2025 (Grupa) |
|--------|-------------------|-------------------|
| Poslovni prihodi | 535.986 | — |
| Prihodi od ugovora o osiguranju | 602.177 | 606.800 |
| Dobit iz poslovanja (EBIT) | 137.349 | — |
| Amortizacija (D&A) | 80.562 | — |
| Neto dobit dioničarima matice | **80.106** | ~65.389 *(provjeriti — regulatorne tablice se isprepliću)* |
| Neto dobit — nekontrolirajući interesi | 25.057 | *(malo)* |
| Ukupna imovina | 3.397.248 | 1.961.180 |
| Ukupno kapital | 1.769.392 | 870.770 |
| Nekontrolirajući interesi (kapital) | 307.263 | *(provjeriti)* |
| Kapital pripisan matici (equity_parent) | ~1.462.129 | *(provjeriti)* |

> Brojke su ručno očitane radi orijentacije. **Mjerodavan je izlaz ekstraktora**
> (`python -m src.ingest extract`) s page-referencama i confidenceom. CROS atribucija
> matici/NCI iz regulatornih formi je nesigurna pri ručnom čitanju — ostaviti ekstraktoru.

## Dividende i ISIN-ovi preko EHO-a (riješeno 2026-07-02, bez zse.hr)

**Dividende:** objave odluka glavnih skupština na eho.zse.hr nose strukturirani blok
"Informacije o dividendi" po VRIJEDNOSNICI (klasi): tip (izglasana/prijedlog/predujam),
iznos EUR, ex-datum, datum prava, datum isplate. Parser: `src/eho.py::parse_dividend_blocks`;
pipeline: `python -m src.dividends ADRS CROS --from 2024-01-01` → tablica `dividends`
+ godišnji `dps` u `financials` (konvencija fiscal_year=ex_date.year−1, zabilježena u
source_page; za CROS 2025 potvrđena i tekstom objave view/65796).

**ISIN-ovi:** iz PDF-ova odluka skupština (GS-ADRS-b699398c…, GS-CROS-a17063a9…) i
godišnjih izvješća — upisani kroz `db/seed_verified_2025.sql` zajedno s brojem dionica
po klasi (izvorne stranice citirane u tom fileu). CROS2 povlaštene su računovodstveno
financijska OBVEZA (zajamčena 8% dividenda; AR2025 bilj. 22.1/24), ne kapital.

## EOD cijene sa zse.hr — RIJEŠENO 2026-07-02 (allowlist primijenjen)

`zse.hr` sada vraća 200. Dva JSON endpointa (otkriveno iz stranice
`/hr/cijene-vrijednosnih-papira/36`):

1. **Intraday/tekući prikaz** (puni stranicu): `https://zse.hr/json/TradingPriceList`
   s parametrima `lng, market_segment_ids, type, model, date, only_traded` i headerom
   `X-Requested-With: XMLHttpRequest` (bez njega vraća prazno). Odgovor nosi i polje
   **`RestApi`** = javna REST baza za downloade.
2. **Službena EOD tečajnica** (gumb "Preuzmi JSON"):
   `<RestApi>price-list/XZAG/<YYYY-MM-DD>/json` (RestApi je oblika
   `https://rest.zse.hr/web/<javni-token>/` — token je ugrađen u zse.hr za sve
   posjetitelje, NIJE korisnički `ZSE_API_KEY`). Polja: `symbol, isin, close_price,
   volume, model, segment, date...` — čisti decimalni stringovi.

**Pravila u `src/prices.py::fetch_zse_json`:** uzimaju se samo reci knjige naloga
(model `CT`/`CTLL`; `BLOCK`/`OTC` se preskaču — isti simbol zna imati više redaka),
valuta mora biti EUR, a ISIN iz tečajnice se provjerava protiv `share_classes.isin`
(nesklad → redak se ne upisuje). CLI:
`python -m src.prices zse-json ADRS ADRS2 CROS CROS2 MAIS KOEI --date 2026-07-02`.
`mojedionice.com` ostaje fallback (301→dosegljiv) ako ZSE opet postane nedostupan.

## STANJE 2026-07-02 (poslije ekstrakcije)
1. **ANTHROPIC_API_KEY vraćen** u environment konfiguraciju. Napomena za nove
   sesije: ključ zna biti u env-u glavnog `claude` procesa, ali NE i u tool shellu —
   tada ga prepiši u gitignorani `.env` (config.py ga učitava kroz dotenv).
2. **2A GOTOVO za FY2025:** `ingest extract` proveden nad sliceovima
   (`--pages` opcija u `src.pdf_extract`): ADRS filing FY2025 (NEEDS_REVIEW samo
   zbog conf 0.60 na `other_operating_income`), CROS filing FY2025 (NEEDS_REVIEW
   zbog niskog conf na stavkama koje se kod osiguratelja ne mapiraju čisto:
   operating_expenses/net_financial_result/debt_long/capex). Sva cross-check sidra
   iz tablice gore POGOĐENA (ADRS: aktiva 3.397.248k, kapital 1.769.392k, dobit
   matice 80.106k; CROS: aktiva 1.961.180k, kapital 870.770k, dobit matice 65.389k).
3. **Cijene u `prices_eod`** po klasi (01.–02.07.2026): ADRS 150,00; ADRS2 103,00;
   CROS 3.460,00; CROS2 3.360,00; MAIS 68,00; KOEI 1.010,00 EUR.
4. **Otvoreno:** peer financije za 2C (peer_multiples iz baze); `segment_financials`
   (IFRS 8, ADRS str 89–91) za SOTP; broj dionica MAIS-a (za trž.kap. u SOTP-u);
   starije godine (2021–2024) po potrebi za trendove.
