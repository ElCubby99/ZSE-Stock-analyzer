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
2. Submitaj sitemap: `https://www.burzovnilist.com/sitemap.xml`
   (generira se pri svakom buildu, lastmod = zadnji EOD).
3. **M38 (nakon deploya EN verzije) — RUČNI KORAK**: ponovno submitaj
   sitemap u GSC — sadrži i sve `/en/` rute s hreflang alternates
   parovima (390 URL-ova). Kanonska domena je `www.` varijanta.
4. GA4: dodaj custom dimension `language` (event-scoped, parametar
   `language` s page_view eventa) za čiste izvještaje po jeziku.

### GA4 / Google Ads
- GA4 Admin → Product links → poveži budući Google Ads račun.
- Konverzije mapiraj iz eventa (`sign_up`, `portfolio_created`).
- Marketinška consent kategorija je pripremljena u kodu ali SKRIVENA —
  prije uključivanja Ads/remarketing tagova javi da se aktivira
  (nova verzija politike kolačića → ponovni pristanak).

### Vercel deploy hook (dnevni SEO build)
1. Vercel → Project → Settings → Git → Deploy Hooks → kreiraj hook.
2. URL ide u GitHub Actions secret `VERCEL_DEPLOY_HOOK_URL` (vidi sekciju
   "Dnevni pipeline na GitHub Actions — M32") — workflow ga okida TEK nakon
   što su novi exporti potvrđeni i commitani. Pri lokalnom ručnom pokretanju
   `src/daily.py` isti env radi i dalje (bez varijable korak se preskače).

## Ručni koraci za Borisa (Auth v2 — M26)

1. Supabase SQL Editor: pokreni `supabase/migration_authv2.sql` (jednom).
2. Konfiguriraj Google + Facebook OAuth providere i redirect URL-ove —
   detaljne upute: `docs/supabase_setup.md` (sekcija Auth v2).
3. Deploy Edge Functiona: `supabase functions deploy delete-account`.
4. Apple: tek nakon Apple Developer Programa —
   `VITE_AUTH_APPLE_ENABLED=true` u Vercelu + provider u Supabaseu.

## Ručni koraci za Borisa (Blog CMS — M27)

1. Supabase SQL Editor: pokreni `supabase/migration_blog.sql` (jednom).
2. Postavi SEBE kao prvog admina (jednokratno, NE postoji kroz UI):
   `update public.profiles set is_admin = true where id = '<tvoj auth.users id>';`
   (id nađeš u Authentication → Users)
3. Deploy Edge Functiona:
   `supabase functions deploy blog-publish --no-verify-jwt`
   `supabase functions deploy trigger-deploy`
4. Secreti (Edge Functions → Secrets):
   - `BLOG_API_KEY` = dug nasumični string (npr. `openssl rand -hex 32`);
     ISTI ključ zalijepi u Cowork marketing skill STATE (lokalni Dropbox
     fajl — NIKAD u javni repo ni SKILL.md plaintext)
   - `VERCEL_DEPLOY_HOOK_URL` = postojeći hook (ili odvoji novi "content
     deploy" hook na istom main branchu radi preglednosti u Vercel logovima)
   (SUPABASE_URL/ANON_KEY/SERVICE_ROLE_KEY su automatski dostupni.)
5. Provjera API-ja (agent flow):
   ```
   curl -X POST https://<ref>.supabase.co/functions/v1/blog-publish \
     -H "x-api-key: $BLOG_API_KEY" -H "content-type: application/json" \
     -d '{"slug":"probni-post","title":"Probni","content_md":"# Test","status":"published"}'
   ```
   → `{ ok: true, ..., deploy_triggered: true }`; bez ključa → 401.
6. Vercel: provjeri da su `VITE_SUPABASE_URL` i `VITE_SUPABASE_ANON_KEY`
   u build env (Production + Preview) — SSG build povlači objavljene
   postove iz baze (anon ključ vidi SAMO published, RLS).

## Ručni koraci za Borisa (Vijesti + X — M30)

1. Supabase SQL Editor: pokreni `supabase/migration_news.sql` (jednom,
   NAKON `migration_blog.sql` — koristi `public.is_admin()`).
2. Deploy Edge Functiona (svi koriste postojeći `BLOG_API_KEY` secret):
   `supabase functions deploy news-ingest --no-verify-jwt`
   `supabase functions deploy news-list --no-verify-jwt`
   `supabase functions deploy news-mark-tweeted --no-verify-jwt`
3. Auto-vijesti iz noćnog pipelinea: u okolinu u kojoj se vrti
   `scripts/daily_update.sh` (uz postojeći `.env`) dodaj:
   - `SUPABASE_URL=https://<ref>.supabase.co`
   - `BLOG_API_KEY=<isti ključ kao za blog-publish>`
   Bez njih korak 5/5 samo ispiše upozorenje (pipeline ne pada). Pipeline
   NEMA direktan pristup bazi — piše isključivo kroz `news-ingest`, i sve
   ulazi kao DRAFT (objava je uvijek tvoja odluka u `/admin` → VIJESTI).
4. Provjera API-ja za X agenta (Cowork):
   ```
   # popis objavljenih, još ne-tweetanih vijesti (bez ključa → 401)
   curl https://<ref>.supabase.co/functions/v1/news-list \
     -H "x-api-key: $BLOG_API_KEY"
   # nakon pripreme/objave tweeta označi vijest (id iz news-list):
   curl -X POST https://<ref>.supabase.co/functions/v1/news-mark-tweeted \
     -H "x-api-key: $BLOG_API_KEY" -H "content-type: application/json" \
     -d '{"id":"<uuid>"}'
   ```
   Cowork agent koristi SAMO ova dva endpointa — nikakav drugi pristup
   bazi (ni anon ni service ključ mu se ne daju).
5. X (Twitter) account: kreiraj NOVI račun za Burzovni list — odvojen od
   Wealtharian (@TheWealtharian), različit brend, ne miješati. Handle
   upiši u Vercel env `VITE_X_HANDLE` (Production + Preview) i redeployaj
   — prazna varijabla znači da se X linkovi u footeru i na /vijesti
   jednostavno ne prikazuju (promjena handlea = samo env update, bez
   promjene koda).

## Dnevni pipeline na GitHub Actions (M32 → M34: satni pokušaji)

`src/daily.py` se više NE vrti na lokalnom stroju/VPS-u — workflow
`.github/workflows/daily-eod.yml` ga pokreće **radnim danima svaki sat
od 16:20 do 23:20 Europe/Zagreb** (ZSE zatvara u 16:00, ali tečajnica
zna kasniti satima — incident 16.07.2026.: objava tek nakon 19 h, a stari
dizajn s jednim runom u 16:20 i retryjem do 18:00 ostavio bi jučerašnje
podatke 24 sata). Dva satna cron raspona pokrivaju ljetno i zimsko
računanje vremena; DST guard propušta samo runove u lokalnom prozoru
16–24 h (namjerno širok: GitHub cronovi znaju kasniti i >1 h — uski
prozor 16–17 h je 16.07. preskočio SVE zakazane runove). `concurrency:
daily-eod` garantira da se dva runa nikad ne izvršavaju paralelno.

Svaki satni run je kratak i BEZ spavanja (čekanje rade cron termini):
1. **Idempotentni guard**: današnji EOD već kompletan u bazi (udio live
   klasa s današnjim zapisom ≥ `EOD_COMPLETE_MIN_SHARE`, zadano 0,5)?
   → log "already done", nula posla, nula deploya (~10–30 s).
2. **Jedan pokušaj dohvata**: izvor još nema današnju tečajnicu →
   **SUCCESS** s logom `podaci još nisu objavljeni, pokušaj N od M` —
   to je NORMALAN ishod satne serije, ne greška (zeleni Actions tab).
3. **S podacima**: backfill jučerašnje rupe ako je izvor nudi (log
   `backfill {datum}` — serija ne smije trajno imati rupu), pa puni
   prolaz (watcher → extract → recompute → regen → commit exporta →
   deploy hook) točno JEDNOM taj dan; kasniji runovi = no-op.
4. **Alarm**: SAMO zadnji dnevni pokušaj (lokalno ≥ `EOD_FINAL_HOUR`,
   zadano 23 h) bez podataka vraća exit 3 → run failure + Issue
   `pipeline-fail` + GitHubov mail. Jedan alarm dnevno, ne po satu.
   Napomena: burzovni praznik radnim danom također okine alarm — takav
   issue samo zatvori.
5. **Kalibracija prozora**: pri prvom uspješnom dohvatu dana upisuje
   se KADA su podaci stvarno stigli (`eod_first_seen`: datum, lokalno
   vrijeme, koji satni pokušaj) — nakon par tjedana iz te tablice se
   vidi stvarna distribucija ZSE objava pa se raspored suzi na
   termine koji stvarno trebaju (`SELECT * FROM eod_first_seen
   ORDER BY trade_date`).
6. **Shema**: na početku svakog runa primjenjuje se idempotentna
   migracija `db/zse_schema_v3_1.sql` (IF NOT EXISTS) — lokalna i
   produkcijska baza ne mogu razjahati (uzrok pada 16.07.).

Semantika statusa u Actions tabu: SUCCESS s "not yet published" ili
"already done" u logu je normalan rad; FAILURE znači ili "dan bez
objave do 22:20" ili stvaran pad koda (issue nosi link na run).

Ručna nadoknada bilo kojeg dana: Actions → daily-eod → **Run workflow**
(dispatch preskače DST guard; uspješan run sam backfilla jučerašnju rupu
ako je izvor još nudi taj datum).

Model stanja (runner je efemeran — ništa ne preživljava run):
- **Postgres stanje** (companies, filings, financials, prices_eod,
  valuations…) živi u **Supabase Postgresu** — pipeline se spaja secretom
  `ZSE_DSN` (puni connection string; `src/config.py` mu daje prednost).
- **JSON exporti** (`frontend/public/data/`) se nakon uspješnog runa
  **commitaju natrag u repo** (`[skip ci]` u poruci da ne okinu novi
  workflow); Vercel build ih čita iz repoa — zato deploy hook ima smisla
  tek NAKON pusha.

### Ručni koraci za Borisa (M32)

1. **Migracija baze**: OBAVLJENA 15.07.2026. kroz Supabase Management API
   (svih 20 tablica, 38.291 redaka, potvrđeno usporedbom broja redaka po
   tablici; anon/authenticated grantovi maknuti — pipeline tablice nisu
   vidljive kroz API). `scripts/verify_migration.sql` ostaje za ponovnu
   provjeru (psql ili SQL editor). Nakon migracije resetiraj lozinku baze
   (Settings → Database) jer je korištena u chatu, i novu upiši u ZSE_DSN.
2. **GitHub secreti** (repo → Settings → Secrets and variables → Actions):
   - `ZSE_DSN` — isti Supabase connection string kao gore
   - `ANTHROPIC_API_KEY` — ekstrakcija novih izvješća (potrošnja i dalje
     ide kroz `src/api_usage.py` budžet)
   - `VERCEL_DEPLOY_HOOK_URL` — postojeći hook
   - `SUPABASE_URL` + `BLOG_API_KEY` — auto-vijesti (news-ingest)
   NIŠTA od ovoga ne ide u repo.
3. **Stari cron na tvom stroju**: obriši ga ako je ikad bio postavljen
   (`crontab -e`); ako nije bio — ništa.
4. **Prvi tjedan**: Actions tab — pogledaj u koliko sati prvi run nađe
   podatke (kalibrira koliko su satni termini stvarno potrebni) i koliko
   traju no-op runovi. Ručno pokretanje/nadoknada: Actions → daily-eod →
   **Run workflow**.
5. **Minute** (procjena M34 — nakon prvog tjedna upiši stvarnu brojku iz
   Actions taba): no-op run ~10–30 s × do 7 runova/dan + jedan puni run
   ~3–5 min ⇒ ~5–8 min/dan ≈ **110–175 min/mj** — daleko ispod besplatne
   kvote (2.000 min/mj za privatni repo).
