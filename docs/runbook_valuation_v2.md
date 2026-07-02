# Runbook — Valuacijski motor v2 (nastavak)

Stanje i točni koraci za nastavak u **novoj sesiji** (nova sesija ne pamti chat).
Grana: `claude/valuation-v2`.

## Što je VEĆ gotovo (na ovoj grani)
- `db/zse_schema_v2.sql` — share_classes (+isin), holdings (vlasnički graf),
  segment_financials, view-ovi `v_shares_canonical` / `v_sotp_inputs`. Idempotentno.
  Seed: ADRS/CROS/MAIS + ADRS vlasnički graf (% iz izvora; ISIN NULL — ne izmišljati).
- `src/valuation_methods.py` — eligibility/value_company/reconcile **NEPROMIJENJENI**;
  implementirani svi `compute_*` (multiples, EV/EBITDA, DCF, DDM, opravdani P/B, SOTP)
  s parametriziranim **PLACEHOLDER** pretpostavkama (`Params`) i graceful degradacijom
  (`assumptions["missing"]`). `build_ctx` iz baze + CLI.
- Provjera (radi odmah): `python -m src.valuation_methods ADRS CROS KOEI`
  → KOEI daje 4 metode + reconciliation; ADRS/CROS pokazuju gating (skip+razlog).

## ŠTO BLOKIRA prave brojeve (zato treba nova sesija s domenama)
Cijene, ISIN-ovi, dividende nemaju dosegljiv izvor u trenutnoj politici:
- `www.zse.hr` / `zse.hr` / `adris.hr` → **403** (blokirano)
- `rest.zse.hr` → 200 ali **401** (ZSE REST API traži ključ)
- `eho.zse.hr` → 200 (PDF objave, ali URL iza JS tražilice)

## KORAK 1 — dodaj domene u allowlist (Edit environment → Network access: Custom)
```
www.zse.hr
zse.hr
adris.hr
```
(zadrži postojeće: *.anthropic.com, koncar.hr, *.koncar.hr, *.zse.hr; "Also include
default list of common package managers"). Vrijedi tek u NOVOJ sesiji (rebuild cachea).

> Alternativa cijenama/ISIN-u: ZSE REST API ključ kao env var `ZSE_API_KEY`
> (rest.zse.hr je dosegljiv, samo traži auth) — tada se preskače scraping ZSE stranica.

## STANJE KORAKA 2 (ažurirano 2026-07-02) — vidi `docs/adrs_cros_sources.md`
- **Dosegljiv izvor:** `eho.zse.hr` JSON feed (NE zse.hr/adris.hr). Dohvat izvješća:
  `scripts/fetch_eho_reports.sh ADRS CROS`. Dnevno osvježavanje: `scripts/daily_update.sh`.
- **2A (financije):** izvješća 2025 preuzeta + sliceovi spremni (stranice locirane);
  čeka SAMO API ekstrakciju (vidi blokere). v2 shema + seed primijenjeni.
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
- **2B cijene — BLOKIRANO:** ZSE-ov vlastiti EOD nedosegljiv: `zse.hr`/`www.zse.hr` 403
  (i kroz WebFetch), `mojedionice.com` 403 (nije u allowlistu), `rest.zse.hr` 401 bez
  `ZSE_API_KEY`, EHO nema cijene. `src/prices.py` ima CSV uvoz + zse-rest skeleton.
- **2C peer skupovi ODLUČENI** (korisnik delegirao modelu) — `docs/peers.md`:
  ADRS={ATGR, PODR, RIVP, PLAG, ARNT}, CROS=regionalni osiguratelji (nedohvatljivi
  zasad → placeholder ostaje). Mehanika: `src/peer_multiples.py` (medijani iz baze).
- **BLOKERI:**
  1. `ANTHROPIC_API_KEY` **nije u okruženju** (nakon resuma 2026-07-02 env var više ne
     postoji; usage limit se resetirao 01.07., ali bez ključa `ingest extract` ne radi).
  2. Cijene: vidi gore — treba ili `zse.hr` u allowlistu (novi session/rebuild) ili
     `ZSE_API_KEY` ili `mojedionice.com` u allowlistu.
  3. Peer multipli se IZVODE iz cijena+financija peera → čekaju 1 i 2.

## KORAK 2 — što napraviti u novoj sesiji (redom: "oboje redom")
A. **Financije ADRS i CROS** (kao točka 4, dvije firme): naći konsolidirana godišnja
   izvješća (Adris grupa, Croatia osiguranje) — preko adris.hr/zse.hr ili eho.zse.hr —
   `pdf_extract` → `ingest extract` (API → load → validate). + **ADRS segmenti** iz
   bilješki (IFRS 8) u `segment_financials`.
B. **Cijene** → `prices_eod` (po share_class gdje treba: ADRS vs ADRS2) i **dividende**
   (dps) — sa ZSE stranica ili REST API-ja. ISIN-ovi → `companies.isin` / `share_classes.isin`.
C. **Peer multiplikatori "izvedi iz tickera"** — KORISNIK MORA NAVESTI peer skup
   (tickere usporedivih firmi za ADRS i za CROS). Iz njihovih cijena+financija izvesti
   P/E, P/B, EV/EBITDA i unijeti u `Params` (zamijeniti placeholdere).
D. Pokrenuti `python -m src.valuation_methods ADRS CROS` i ispisati pokrenute/
   preskočene+zašto/reconciliation — sad s pravim brojevima.

## OTVORENO PITANJE za korisnika (potrebno za korak 2C)
Navedi **peer tickere** za ADRS (holding) i za CROS (osiguratelj). Bez popisa se peer
multiplikatori ne mogu izvesti ni s otključanim cijenama.

## Napomene
- Ne izmišljati brojke (ISIN, cijene, pretpostavke) — radije prazno/placeholder s oznakom.
- Eligibility logiku NE mijenjati.
- Stara branch-higijena (preimenovanje defaulta u `main`, brisanje suvišnih grana)
  ostaje otvorena — vidi raniji dogovor.
