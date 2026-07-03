# Runbook — Valuacijski motor v2 (nastavak)

Stanje i točni koraci za nastavak u **novoj sesiji** (nova sesija ne pamti chat).
Grana: `claude/valuation-v2-setup-ymjeg7`.

## Što je VEĆ gotovo (na ovoj grani)
- `db/zse_schema_v2.sql` — share_classes (+isin), holdings (vlasnički graf),
  segment_financials, view-ovi `v_shares_canonical` / `v_sotp_inputs`. Idempotentno.
  Seed: ADRS/CROS/MAIS + ADRS vlasnički graf (% iz izvora; ISIN NULL — ne izmišljati).
- `src/valuation_methods.py` — eligibility/value_company/reconcile **NEPROMIJENJENI**;
  implementirani svi `compute_*` (multiples, EV/EBITDA, DCF, DDM, opravdani P/B, SOTP)
  s parametriziranim **PLACEHOLDER** pretpostavkama (`Params`) i graceful degradacijom
  (`assumptions["missing"]`). `build_ctx` iz baze + CLI.
- Provjera: `python -m src.valuation_methods ADRS CROS` → obje firme daju metode
  s pravim ulazima (nakon obnove baze — vidi KORAK 1). PAŽNJA: KOEI-jeve financije
  živjele su samo u bazi starog containera (PDF/DB se ne commitaju) — u svježem
  containeru KOEI nema filinga dok se ne ponovi njegov ingest.

## KORAK 1 — RIJEŠENO 2026-07-02: allowlist primijenjen, ključ vraćen
- `zse.hr` → 200 (cijene rade, vidi dolje); `www.zse.hr` → 301 na zse.hr;
  `eho.zse.hr` → 200; `mojedionice.com` → 301 (dosegljiv fallback);
  `adris.hr` → TLS greška NJIHOVOG lanca (nepotreban — izvješća idu preko EHO-a).
- `ANTHROPIC_API_KEY` vraćen u environment konfiguraciju. **Zamka za svježu
  sesiju:** zna postojati u env-u glavnog `claude` procesa, ali ne i u tool
  shellu — tada ga prepiši u gitignorani `.env` (dotenv ga učitava).
- **Svježi container NEMA v2 stanje baze!** SessionStart hook primjenjuje samo
  v1 shemu. Obnova (idempotentno, redom):
  1. `psql ... -f db/zse_schema_v2.sql` pa `-f db/seed_verified_2025.sql`
  2. `scripts/fetch_eho_reports.sh ADRS CROS` (PDF-ovi su gitignorani)
  3. `python -m src.dividends ADRS CROS --from 2024-01-01`
  4. sliceovi + `ingest extract` (vidi 2A) i `python -m src.prices zse-json ...`

## STANJE KORAKA 2 (ažurirano 2026-07-02 navečer) — vidi `docs/adrs_cros_sources.md`
- **Izvori:** izvješća+dividende `eho.zse.hr` feed; cijene `zse.hr` službena
  tečajnica (JSON). Dnevno osvježavanje: `scripts/daily_update.sh`.
- **2A GOTOVO za FY2025 (obje firme):** sliceovi
  (`python -m src.pdf_extract <pdf> <txt> --pages 23-33,134-136` za ADRS;
  `--pages 125-133` za CROS) → `python -m src.ingest extract` → filinzi u bazi,
  sva cross-check sidra pogođena (dobit matice ADRS 80.106k / CROS 65.389k itd.).
  Status NEEDS_REVIEW samo zbog niskog confidencea na sporednim stavkama.
  Otvoreno iz 2A: `segment_financials` (IFRS 8, ADRS PDF str 89–91) za SOTP.
- **2B cijene GOTOVO:** `python -m src.prices zse-json ADRS ADRS2 CROS CROS2 MAIS KOEI`
  → `prices_eod` po KLASI (službeni close, CT/CTLL; ISIN provjera). Detalji
  endpointa u `docs/adrs_cros_sources.md`.
- **2B GOTOVO — dividende i ISIN-ovi (bez zse.hr!):**
  - `src/eho.py` + `src/dividends.py`: strukturirani blokovi "Informacije o dividendi"
    s EHO objava skupština → tablica `dividends` (po klasi) + godišnji `dps` u
    financials. Stvarno u bazi: ADRS FY23/24/25 = 2,57/3,00/3,12 €;
    CROS FY23/24/25 = 267,64 (dvije isplate!)/106,52/114,14 €.
  - ISIN-ovi (iz GS PDF-ova i AR-a, vidi `db/seed_verified_2025.sql`):
    ADRS=HRADRSRA0007, ADRS2=HRADRSPA0009, CROS=HRCROSRA0002, CROS2=HRCROSPA0004,
    MAIS=HRMAISRA0007. Broj dionica po klasi također verificiran i upisan
    (ADRS 9.615.900/tr.130.779; ADRS2 6.784.100/tr.390.916; CROS 420.947; CROS2 8.750
    — povlaštene CROS2 su računovodstveno OBVEZA, vidi AR2025 bilj. 22.1/24).
  - `prices_eod` PK popravljen na (company, date, klasa) — ADRS i ADRS2 isti dan.
  - DDM sada radi sa stvarnim dps (r/g još placeholder).
- **2C peer skupovi ODLUČENI** (korisnik delegirao modelu) — `docs/peers.md`:
  ADRS={ATGR, PODR, RIVP, PLAG, ARNT}, CROS=regionalni osiguratelji (nedohvatljivi
  zasad → placeholder ostaje). Mehanika: `src/peer_multiples.py` (medijani iz baze).

## KORAK 2 — stanje (A/B/D provedeni 2026-07-02; SOTP dovršen isti dan navečer)
A. **GOTOVO (FY2025):** ekstrakcija konsolidiranih izvješća ADRS+CROS u bazu
   (filinzi uz NEEDS_REVIEW na sporednim stavkama). **Segmenti GOTOVI:**
   `src/segments.py` + `extract_segments` (extract.py) — IFRS 8 iz bilj. 5
   (slice str 5–7 + 88–91; uprava dopuštena SAMO za metrike koje bilješka ne
   objavljuje). U bazi: tourism 111M EBITDA (bilj. 5), aquaculture 11,3M (uprava
   str 7 — bilješka daje samo EBIT), energy 12M, insurance NULL (nije smisleno).
   Σ segment EBITDA 134,3M vs grupna 217,9M → plug 38,4% > 15% → needs_review
   (očekivano: osiguranje bez EBITDA + eliminacije).
B. **GOTOVO:** cijene po klasi u `prices_eod` (zse-json) + dividende/ISIN-ovi (EHO).
C. **GOTOVO za ADRS (M3, 2026-07-03):** svih 5 peera ingestano (FY2025) +
   cijene → medijani IZ BAZE: P/E 13,69, P/B 1,53, EV/EBITDA 8,45 (n=5/5/4;
   tablica po peeru u `docs/peers.md`). `src/params_calibrated.py` gradi
   Params po firmi: r=9,31% (CAPM: rf 3,61% TradingEconomics HR 10g +
   beta 1,0 [PRETPOSTAVKA] × ERP 5,7% [Damodaran A3, točan HR redak
   neprovjeren — egress 403]), g=2,0% (ECB cilj, konzervativno), peer
   multipli za ADRS iz baze, CROS peeri OSTAJU placeholder (nema usporedivog
   osiguratelja na ZSE). Confidence po metodi sada ovisi o kalibraciji
   NJEZINIH ulaza (rates_calibrated / peers_calibrated); izvori se ispisuju
   uz svaku metodu (assumptions["sources"]). SOTP: conf 0,6 (85% NAV-a
   tržišno) + market_check (trž.kap vs NAV; 02.07.: cijena +13,7% IZNAD
   konzervativnog NAV-a — povijesni diskont neizvediv iz 2 dana cijena).
   CLI: `python -m src.valuation_methods ADRS CROS --sensitivity` (r ±1%).
D. **PROVEDENO — sve 4 ADRS metode sada daju vrijednost.** SOTP end-to-end:
   86,43 / 92,19 / 97,96 €/dionici (NAV 1.829,9M − diskont 15–25%). Breakdown:
   CROS 1.002,5M (tržišno, po klasi), Maistra 696,1M (tržišno; MAIS dionice
   verificirane), HUP 169,5M (rezidual 22,6M × 7,5), Cromaris 90,4M (11,3M × 8),
   Energetika 42,0M (12M × 7 × **0,50** — udjel ispravljen po AR str 33),
   neto novac −170,7M (−net_debt). Reconciliation ADRS: zona 45,46–99,33 €,
   disperzija 54% (P/B leća ~46 vs SOTP ~92 = holding diskont priča iz decka).
   Pretpostavke (multiple 7,5/8/7, diskont, r/g, peer multipli) su PLACEHOLDER.

## SOTP — odluke i izvedene brojke (2026-07-02)
- **HUP-Zagreb:** izravno 100% Adrisov (AR2025 str 4/33/113), NIJE pod Maistrom,
  ali turistički segment (111M EBITDA) = "Maistra grupa + HUP" (str 184) →
  tržišna Maistra + 111M×7,5 za HUP bi DVOSTRUKO brojala. Rješenje: holding
  pokazuje na izvedeni ključ `tourism_hup` = 111,0M − 88,4M (MAIS AR2025 str 9,
  kons. EBITDA) = **22,6M** (conf 0,70; jedina izvedena brojka, aritmetika
  citirana u `db/seed_verified_2025.sql`). Ograda: segmentne brojke uključuju
  unutargrupne odnose → rezidual nosi tu nepreciznost.
- **Energetika:** sva energetska društva (ZELOVO/VRTAČA/ENCRO VOŠTANE/BABINDUB)
  su **50%** (AR str 33) → ownership_pct ispravljen 1,00 → 0,50.
- **MAIS:** 10.944.339 redovnih dionica, bez vlastitih (MAIS AR2025 str 149 i
  224); Adris 10.236.872 = 93,54% ✓ poklapa se s grafom.
- **Neto novac:** compute_sotp koristi −net_debt (= dug − novac, izvedeno iz
  ekstrakcije; za ADRS −170,7M) umjesto bruto novca; flagovi
  `net_cash_excludes_insurance_portfolio` i grupno-agregatna ograda u assumptions.
- **Trž. kapitalizacija po klasi:** market_cap_of zbraja zadnji close × dionice
  PO KLASI (CROS 3.460 × 420.947 + CROS2 3.360 × 8.750); latest_price preferira
  primarnu liniju kod izjednačenog datuma. Redoslijed obnove u svježem
  containeru: ingest extract → segments extract → **ponovno** seed_verified
  (tourism_hup red ovisi o postojanju filinga).

## OTVORENO PITANJE za korisnika (potrebno za korak 2C)
Navedi **peer tickere** za ADRS (holding) i za CROS (osiguratelj). Bez popisa se peer
multiplikatori ne mogu izvesti ni s otključanim cijenama.

## Napomene
- Ne izmišljati brojke (ISIN, cijene, pretpostavke) — radije prazno/placeholder s oznakom.
- Eligibility logiku NE mijenjati.
- Stara branch-higijena (preimenovanje defaulta u `main`, brisanje suvišnih grana)
  ostaje otvorena — vidi raniji dogovor.

## M4 — frontend (grana `claude/frontend-m4`, 2026-07-03)
- **Backend:** `src/stock_json.py` (JSON za stranicu: fundamenti s izvorima,
  cijene po klasi, metode low/base/high/confidence + assumptions/sources,
  preskočene metode s razlogom, reconciliation, SOTP breakdown s placeholder
  zastavama) + `src/webapi.py` (stdlib server: `/api/dionica/<TICKER>` +
  servira `frontend/dist`, SPA fallback). Frontend samo ČITA — eligibility i
  valuation logika netaknuti.
- **Frontend:** `frontend/` Vite+React, ruta `/dionica/:ticker` (ADRS, CROS).
  Raspored po mockupu; pretpostavke su READ-ONLY vrijednosti s izvorom (bez
  slidera na javnom prikazu); oznake `pretpostavka` na β, holding diskontu,
  SOTP multiplama, CROS peerima; CROS bez SOTP reda (metoda gate-ana);
  podatak kojeg nema u bazi -> prazno + oznaka. MAR: bez preporuka.
- **Pokretanje:** `python -m src.webapi` (port 8001) pa ili
  `cd frontend && npm install && npm run dev` (proxy /api) ili
  `npm run build` pa sve na 8001.
