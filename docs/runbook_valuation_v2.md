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
