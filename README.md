# ZSE Fundamental Analytics — MVP (Končar)

Pipeline koji iz financijskih izvješća hrvatskih izdavatelja (počevši s Končarom)
puni `financials` tablicu, validira brojke determinističkim provjerama i izlaže ih
analitici. Dizajn i specifikacija: `docs/koei_extraction_prompt.md`.

Entitet: Končar je grupa. Za valuaciju grupe koristi **konsolidirano**; standalone
ingestaj zasebno i NIKAD ne miješaj u istom izračunu.

## Status sesije (TIJEK PRVE SESIJE)

- [x] **1. Shema na lokalnom Postgresu** — `db/zse_schema.sql` + `db/setup_db.sh`
- [x] **2. Loader** — `src/extract.py` (API) + `src/normalize.py` + `src/loader.py`
- [x] **3. Validator** — `src/validator.py` (7 determinističkih pravila)
- [ ] **4. Ingest 3 Končarova konsolidirana godišnja izvješća (2023–2025)** —
      ČEKA stvarne dokumente (vidi niže)
- [x] **5. Usporedna tablica** — `src/report.py` + `python -m src.ingest report`
      (testirano na sintetičkim podacima; čeka stvarne brojke iz točke 4)

### Što treba za točku 4
Loader/validator rade, ali trebaju **stvarni tekst** 3 konsolidirana godišnja
izvješća (2023, 2024, 2025). Stavi ih u `data/reports/` (npr.
`koei_2024_consolidated.txt`) i postavi `ANTHROPIC_API_KEY`, pa pokreni:

```bash
python -m src.ingest extract --text data/reports/koei_2024_consolidated.txt \
    --source-url <zse.hr URL> --published 2025-04-15
```

Bez API ključa može se učitati i ručno spremljeni extraction JSON:
```bash
python -m src.ingest load --json data/reports/koei_2024.json --source-url <URL>
```

Na kraju:
```bash
python -m src.ingest report --years 2023 2024 2025
```

## Razvoj i testovi

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python tests/test_normalize.py    # čisti unit testovi
python tests/test_pipeline.py     # integracija (loader+validator vs lokalna baza)
```

## Pipeline (točke 2–3)

```
tekst izvješća
  └─ src/extract.py     Anthropic API (Opus 4.8), system prompt iz specifikacije → JSON
       └─ src/normalize.py   value_eur = value_raw * scale; HRK→EUR; dionice bez skale
            └─ src/loader.py      upsert filing + insert financials + derivacije (is_reported=FALSE)
                 └─ src/validator.py  7 pravila → status 'validated' | 'needs_review'
                      └─ src/report.py     usporedna tablica
```

Derivacije (kod, `is_reported=FALSE`): `ebitda` (ako nije objavljen = ebit+d&a),
`total_debt`, `net_debt`, `free_cash_flow`.

Validacijska pravila: 1 bilanca se zatvara · 2 kapital konzistentan · 3 dobit
konzistentna · 4 EBITDA sanity · 5 scale sanity (WARN) · 6 YoY ±60% (WARN) ·
7 confidence ≥ 0.85. FAIL/WARN ⇒ `needs_review`.

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
