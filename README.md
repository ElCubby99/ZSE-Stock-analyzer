# ZSE Fundamental Analytics — MVP (Končar)

Pipeline koji iz financijskih izvješća hrvatskih izdavatelja (počevši s Končarom)
puni `financials` tablicu, validira brojke determinističkim provjerama i izlaže ih
analitici. Dizajn i specifikacija: `docs/koei_extraction_prompt.md`.

Entitet: Končar je grupa. Za valuaciju grupe koristi **konsolidirano**; standalone
ingestaj zasebno i NIKAD ne miješaj u istom izračunu.

## Status sesije (TIJEK PRVE SESIJE)

- [x] **1. Shema na lokalnom Postgresu** — `db/zse_schema.sql` + `db/setup_db.sh`
- [ ] 2. Loader (tekst → API → JSON → normalizacija → insert u `financials`)
- [ ] 3. Validator (7 determinističkih pravila)
- [ ] 4. Ingest 3 Končarova konsolidirana godišnja izvješća (2023–2025)
- [ ] 5. Usporedna tablica za 3 godine (ručna provjera)

## Točka 1 — postavljanje baze

Zahtijeva PostgreSQL 16. Idempotentno:

```bash
bash db/setup_db.sh            # kreira rolu+bazu, primijeni shemu
ZSE_RESET=1 bash db/setup_db.sh   # čist start (dropa public shemu prvo)
```

Defaulti: baza `zse`, korisnik `zse`/`zse` na `localhost:5432`. Override preko
env varijabli (vidi `.env.example`).

Provjera:

```bash
PGPASSWORD=zse psql -h localhost -U zse -d zse -c "\dt"
```

Očekivano: 7 tablica (`companies`, `filings`, `financials`, `prices_eod`,
`ratios`, `valuations`, `announcements`), view `v_financials_current` i seed red
za KOEI.

## Struktura

```
db/      zse_schema.sql, setup_db.sh
src/     loader / validator (točke 2–3)
tests/   testovi validatora
data/    lokalni izvori izvješća (ne commitaju se)
docs/    specifikacija ekstrakcije i validacije
```
