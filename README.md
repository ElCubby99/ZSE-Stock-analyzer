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
- [x] **4. Ingest 3 Končarova konsolidirana godišnja izvješća (2023–2025)** —
      učitana stvarna Grupa KONČAR (KOEI) izvješća; brojke provjerene protiv
      sidara iz `docs/koei_sources.md`. Napomena o entitetu niže.
- [x] **5. Usporedna tablica** — `src/report.py` + `python -m src.ingest report`
      (testirano na sintetičkim podacima; čeka stvarne brojke iz točke 4)

### Runbook za točku 4 (čeka whitelist domena)

Dohvat izvješća je blokiran dok se u **mrežnoj politici okruženja** (Claude Code
on the web → Edit environment → **Network access: Custom**) ne dopuste domene:

```
koncar.hr
*.koncar.hr
*.zse.hr
```

Označi i "Also include default list of common package managers". Promjena
allowlist-a rebuilda cache okruženja, pa **vrijedi tek u NOVOJ sesiji** (tekuća
zadržava staru politiku). URL-ovi i cross-check sidra: `docs/koei_sources.md`.

> **Napomena o entitetu (2024.):** koncar.hr datoteka
> `2025-04/Revidirano konsolidirano 2024.pdf` je izvješće **Grupe KONČAR – D&ST**
> (ticker KODT, prihodi ~467,5 mil EUR) — KRIVI entitet za KOEI. Za 2024. koristi
> EHO/KOEI prijavu (ispravna Grupa KONČAR, ~1.066 mil EUR poslovnih prihoda).
> Izvori i točni URL-ovi su ažurirani u `docs/koei_sources.md` i u fetch skripti.

Kad su domene dopuštene (nova sesija):

```bash
. .venv/bin/activate                       # ili: pip install -r requirements.txt
bash scripts/fetch_koncar_reports.sh       # PDF-ovi -> data/reports/
for y in 2023 2024 2025; do
  python -m src.pdf_extract data/reports/koei_${y}_consolidated.pdf \
      data/reports/koei_${y}_consolidated.txt
done
```

Zatim ekstrakcija → load → validate. S API ključem (`ANTHROPIC_API_KEY`):

```bash
python -m src.ingest extract --text data/reports/koei_2024_consolidated.txt \
    --source-url <URL> --published 2025-04-15
```

Bez ključa: pročitaj točne brojke iz `*.txt`, složi extraction JSON po shemi iz
`docs/koei_extraction_prompt.md`, pa:

```bash
python -m src.ingest load --json data/reports/koei_2024.json --source-url <URL>
```

Na kraju usporedna tablica (Boris provjerava očima protiv sidara iz
`docs/koei_sources.md`):

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
  └─ src/extract.py     Anthropic API (Opus 4.8): structured outputs + adaptive thinking + streaming → JSON
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

---

## Ručni koraci za Borisa (GTM / SEO / deploy — M25)

### Google Tag Manager (container GTM-WP4FWCDZ)
1. **Google Tag (GA4, G-4JC3VCE07N)**: Tags → New → Google Tag; Tag ID
   `G-4JC3VCE07N`; Triggering = **Initialization – All Pages**. U tag
   postavkama uključi consent provjeru (Advanced → Consent Settings →
   *Require additional consent: analytics_storage* nije potrebno — Consent
   Mode v2 signali su već na stranici, tagovi ih poštuju automatski).
   NE dodavati gtag.js snippet direktno na stranicu — Google Tag živi
   ISKLJUČIVO u GTM-u (inače se page_view broji duplo).
2. **SPA pageviews**: stranica je SPA — promjene rute šalju
   `dataLayer` event **`spa_page_view`** (s `page_path` i `page_title`).
   U GTM-u: Trigger → Custom Event `spa_page_view`; Tag → GA4 Event,
   event name `page_view`, parametri `page_path`/`page_title` iz
   dataLayer varijabli. (Alternativa: GA4 Enhanced measurement →
   "Page changes based on browser history" — tada ovaj tag preskoči da
   ne bude duplo.)
3. **Konverzijski eventi** (već se pushaju u dataLayer): `sign_up`,
   `login`, `portfolio_created`, `stock_view` (parametar `ticker`),
   `engaged_reader` (3+ različite dionice u sesiji), `consent_updated`.
   Za svaki napravi Custom Event trigger + GA4 Event tag po potrebi;
   u GA4 Admin → Events označi `sign_up` i `portfolio_created` kao
   key events (konverzije).
4. **Publish** container i provjeri Preview modeom: prije pristanka
   Google zahtjevi nose `gcs=G100`, nakon "Prihvati sve" `gcs=G111`.

### Google Search Console
1. Dodaj property `burzovnilist.com` (Domain — DNS TXT verifikacija na
   Cloudflareu).
2. Submitaj sitemap: `https://burzovnilist.com/sitemap.xml`
   (generira se pri svakom buildu, lastmod = zadnji EOD).

### GA4 / Google Ads
- GA4 Admin → Product links → poveži budući Google Ads račun.
- Konverzije mapiraj iz eventa (`sign_up`, `portfolio_created`).
- Marketinška consent kategorija je pripremljena u kodu ali SKRIVENA —
  prije uključivanja Ads/remarketing tagova javi da se aktivira
  (nova verzija politike kolačića → ponovni pristanak).

### Vercel deploy hook (dnevni SEO build)
1. Vercel → Project → Settings → Git → Deploy Hooks → kreiraj hook.
2. Na stroju koji vrti noćni pipeline postavi env varijablu
   `VERCEL_DEPLOY_HOOK_URL=<hook url>` — `src/daily.py` ga okida nakon
   regeneracije exporta (bez env varijable korak se preskače i logira).

## Ručni koraci za Borisa (Auth v2 — M26)

1. Supabase SQL Editor: pokreni `supabase/migration_authv2.sql` (jednom).
2. Konfiguriraj Google + Facebook OAuth providere i redirect URL-ove —
   detaljne upute: `docs/supabase_setup.md` (sekcija Auth v2).
3. Deploy Edge Functiona: `supabase functions deploy delete-account`.
4. Apple: tek nakon Apple Developer Programa —
   `VITE_AUTH_APPLE_ENABLED=true` u Vercelu + provider u Supabaseu.
