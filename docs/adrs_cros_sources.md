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

## BLOKERI (stanje 2026-06-28) — vidi runbook
1. **ANTHROPIC_API_KEY je na usage limitu — pristup se vraća 2026-07-01 00:00 UTC.**
   Dok traje, `src.extract`/`ingest extract` (API ekstrakcija) ne rade. PDF-ovi su
   preuzeti i izrezani; ekstrakcija se pokreće čim limit padne.
2. `zse.hr`/`www.adris.hr` → 403; `adris.hr` → TLS lanac neverificiran;
   `rest.zse.hr` → traži `ZSE_API_KEY` (nije postavljen). ⇒ **cijene, dividende (dps),
   ISIN-ovi (KORAK 2B)** nemaju dosegljiv izvor osim ako se postavi `ZSE_API_KEY`.
   (Napomena: dps i ISIN možda se mogu pročitati iz samih izvješća kao alternativa.)
3. **Peer tickeri (KORAK 2C)** za ADRS i CROS — čeka se korisnikov popis.
