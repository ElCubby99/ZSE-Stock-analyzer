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

## KORAK 2 — stanje (A/B/D provedeni 2026-07-02)
A. **GOTOVO (FY2025):** ekstrakcija konsolidiranih izvješća ADRS+CROS u bazu
   (filinzi validirani uz NEEDS_REVIEW na sporednim stavkama). OSTALO: **ADRS
   segmenti** (IFRS 8, PDF str 89–91) u `segment_financials` — treba proširenje
   ekstraktora (canonical shema nema segmente); bez toga SOTP nema segment EBITDA.
B. **GOTOVO:** cijene po klasi u `prices_eod` (zse-json) + dividende/ISIN-ovi (EHO).
C. **OTVORENO — peer multiplikatori:** skupovi odlučeni (`docs/peers.md`), ali
   peeri (ATGR, PODR, RIVP, PLAG, ARNT) nemaju financije u bazi → treba ih
   dodati u `companies` + ekstrahirati njihova izvješća (ista EHO+ingest ruta),
   cijene već idu kroz zse-json. Tek tada `src/peer_multiples.py` daje medijane
   za `Params` (zamjena placeholdera).
D. **PROVEDENO** s pravim financijama/dividendama/cijenama, ali pretpostavke
   (r, g, peer multipli) su i dalje PLACEHOLDER → brojke su mehanika, ne
   valuacija. ADRS: 4 metode (SOTP bez vrijednosti — fali trž.kap MAIS-a jer
   nema broja dionica, i segment EBITDA); CROS: 3 metode; preskoci po dizajnu
   (EV/EBITDA i DCF gateovi). Reconciliation: ADRS divergencija 54 %
   (multiples 99,33 € vs DDM 45,46 € vs opravdani P/B 45,76 €), CROS 34 %.

## OTVORENO PITANJE za korisnika (potrebno za korak 2C)
Navedi **peer tickere** za ADRS (holding) i za CROS (osiguratelj). Bez popisa se peer
multiplikatori ne mogu izvesti ni s otključanim cijenama.

## Napomene
- Ne izmišljati brojke (ISIN, cijene, pretpostavke) — radije prazno/placeholder s oznakom.
- Eligibility logiku NE mijenjati.
- Stara branch-higijena (preimenovanje defaulta u `main`, brisanje suvišnih grana)
  ostaje otvorena — vidi raniji dogovor.
