-- ============================================================
--  ZSE ANALYTICS — schema v3.1 (konsolidacija runtime DDL-a).
--  Pokreni NAKON v1+v2+v3. IDEMPOTENTNO (IF NOT EXISTS svugdje) —
--  primjenjuje se automatski na POČETKU svakog daily runa
--  (src/daily.py::ensure_schema), pa lokalna i produkcijska baza
--  više ne mogu razjahati (incident 16.07.2026.: produkciji su
--  falili v3 stupci jer je DDL izvršavan samo lokalno).
-- ============================================================

-- v2/v3: taksonomija holdinga + NACE sektor
ALTER TABLE companies ADD COLUMN IF NOT EXISTS holding_type TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS nace TEXT;

-- v3 DIV: klasifikacija isplata + politika dividendi
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS payout_type TEXT;
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS payout_ratio NUMERIC;
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS classified_reason TEXT;

CREATE TABLE IF NOT EXISTS dividend_policies (
    company_id INT PRIMARY KEY REFERENCES companies(id),
    policy_type TEXT NOT NULL,  -- postotak_dobiti|progresivna|fiksna|nema
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL,       -- dokument + stranica / URL
    extracted_on DATE NOT NULL
);

-- v3 SOTP: JV knjigovodstvena vrijednost + pridruženi NI na holdings
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS associate_ni NUMERIC;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS jv_book_value_eur NUMERIC;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS jv_book_source TEXT;

CREATE OR REPLACE VIEW v_sotp_inputs AS
 SELECT parent_company_id,
    held_name,
    ownership_pct,
    listed,
    valuation_basis,
    is_insurance,
    held_company_id,
    segment_key,
    default_multiple,
    associate_ni,
    jv_book_value_eur,
    jv_book_source
   FROM holdings h;

-- guidance signali (samo guidance-DCF FCF proxy; v3.1: NE za g1)
CREATE TABLE IF NOT EXISTS growth_estimates (
  id           SERIAL PRIMARY KEY,
  company_id   INT NOT NULL REFERENCES companies(id),
  fiscal_year  INT NOT NULL,
  g1           NUMERIC,
  horizon_years INT DEFAULT 5,
  method       TEXT NOT NULL DEFAULT 'forward_signals',
  rule         TEXT,
  drivers      TEXT,
  basis        TEXT NOT NULL,
  signals      JSONB,
  confidence   NUMERIC,
  source       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE (company_id, fiscal_year, method)
);

-- M47: knjiga narudžbi (backlog) — objavljena TVRDA brojka koja potkrjepljuje
-- near-term rast (npr. proizvođači opreme: KODT). Ručni unos iz izvještaja
-- (0 API), s izvorom (dokument + stranica). growth_rate = implicirani godišnji
-- rast prihoda iz backloga (npr. backlog / godišnji prihod − 1, ili navod
-- uprave); NULL kad se ne može izvesti kao stopa.
CREATE TABLE IF NOT EXISTS backlogs (
  id           SERIAL PRIMARY KEY,
  company_id   INT NOT NULL REFERENCES companies(id),
  fiscal_year  INT NOT NULL,
  backlog_eur  NUMERIC,
  growth_rate  NUMERIC,               -- implicirana godišnja stopa rasta (ili NULL)
  source       TEXT NOT NULL,         -- dokument + stranica / navod uprave
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE (company_id, fiscal_year)
);

-- povijest promjena fer-zona (transparentnost po dionici)
CREATE TABLE IF NOT EXISTS valuation_changelog (
  id          SERIAL PRIMARY KEY,
  company_id  INT NOT NULL REFERENCES companies(id),
  changed_on  DATE NOT NULL,
  old_low     NUMERIC, old_high NUMERIC,
  new_low     NUMERIC, new_high NUMERIC,
  reason      TEXT NOT NULL,
  kind        TEXT NOT NULL DEFAULT 'recompute',  -- methodology|recompute|backfill
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (company_id, changed_on, reason)
);

-- M35.1: higijena dividendi (incident 16.07.2026.: 24 sintetička test
-- retka HT/FY1999 procurila u dev bazu i na /dividende — test se oslanjao
-- na rollback, a classify_company interno commita; UNIQUE ključ ih nije
-- hvatao jer se NULL ex_date vrijednosti u Postgresu ne sudaraju).
DELETE FROM dividends WHERE source_url = 'sintetički-test';
DELETE FROM dividends d USING dividends d2
 WHERE d.ex_date IS NULL AND d2.ex_date IS NULL
   AND d.class_ticker = d2.class_ticker
   AND COALESCE(d.fiscal_year, 0) = COALESCE(d2.fiscal_year, 0)
   AND d.amount_eur = d2.amount_eur
   AND d.id > d2.id;
CREATE UNIQUE INDEX IF NOT EXISTS uq_dividends_no_exdate
  ON dividends (class_ticker, COALESCE(fiscal_year, 0), amount_eur)
  WHERE ex_date IS NULL;

-- M35: KADA su EOD podaci stvarno postali dostupni — kalibracija cron
-- rasporeda iz stvarnosti (upisuje se pri PRVOM uspješnom dohvatu dana)
CREATE TABLE IF NOT EXISTS eod_first_seen (
    trade_date DATE PRIMARY KEY,
    found_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    found_local TEXT,          -- "HH:MM" Europe/Zagreb (čitljivo za pregled)
    attempt    INT,            -- koji satni pokušaj je uspio (1 = 16:20)
    n_records  INT
);

-- M-IDX / M-BOND / M-FOND pomoćne tablice (moduli ih inače stvaraju
-- runtime — ovdje su radi kompletnosti migracije na svježu bazu)
CREATE TABLE IF NOT EXISTS index_eod (
    index_isin TEXT NOT NULL,
    trade_date DATE NOT NULL,
    close_value NUMERIC NOT NULL,
    source TEXT,
    PRIMARY KEY (index_isin, trade_date));
CREATE TABLE IF NOT EXISTS calibrations (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    source TEXT,
    computed_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS index_constituents (
    index_isin TEXT NOT NULL,
    ticker TEXT NOT NULL,
    name TEXT,
    weight_pct NUMERIC,
    free_float_factor NUMERIC,
    as_of DATE NOT NULL,
    source TEXT,
    PRIMARY KEY (index_isin, ticker));
CREATE TABLE IF NOT EXISTS bonds (
    symbol TEXT PRIMARY KEY,
    isin TEXT NOT NULL,
    issuer TEXT,
    series_name TEXT,
    btype TEXT NOT NULL,
    coupon_pct NUMERIC,
    maturity_date DATE,
    price_currency TEXT,
    coupon_freq INT,
    freq_assumed BOOLEAN DEFAULT TRUE,
    day_count TEXT DEFAULT 'ACT/ACT',
    day_count_assumed BOOLEAN DEFAULT TRUE,
    nominal_note TEXT,
    status TEXT NOT NULL DEFAULT 'u obradi',
    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS bond_prices_eod (
    symbol TEXT NOT NULL,
    trade_date DATE NOT NULL,
    clean_price_pct NUMERIC,
    turnover_eur NUMERIC,
    source TEXT,
    PRIMARY KEY (symbol, trade_date));
CREATE TABLE IF NOT EXISTS fund_units (
    fund TEXT NOT NULL,
    category TEXT NOT NULL,
    value_date DATE NOT NULL,
    unit_value NUMERIC NOT NULL,
    source TEXT,
    PRIMARY KEY (fund, category, value_date));
CREATE TABLE IF NOT EXISTS mirex (
    category TEXT NOT NULL,
    value_date DATE NOT NULL,
    value NUMERIC NOT NULL,
    source TEXT,
    PRIMARY KEY (category, value_date));
-- M40: EN prijevod poslovnog profila (djelatnost/segmenti/tržišta/tvrdnje).
-- Mirror strukture bez source_page (ti se ne prevode); overlay po indeksu.
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS bp_en JSONB;

-- M59: dividenda isplativa u VIŠE RATA (HPB FY2025: GS 24.7.2026. dijeli
-- 17,54 € po dionici u dvije rate po 8,77 € — dospijeće 4.8.2026. i
-- 28.1.2027.). EHO strukturirani blok "Informacije o dividendi" nosi samo
-- ukupni iznos sa ZADNJIM datumom isplate, pa je 1. rata nedostajala.
-- Svaka rata je zaseban redak (vlastiti datum isplate + napomena čitatelju);
-- dedup ključ zato mora uključiti i datum isplate — dvije rate dijele
-- (klasa, ex-datum, iznos). Agregati (dps, payout, povijest) zbrajaju po
-- fiskalnoj godini pa ukupno ostaje 17,54 €.
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS note TEXT;
-- Ključ uključuje i div_type: prijedlog i izglasana verzija ISTE dividende
-- znaju dijeliti (klasa, ex, iznos, isplata) — stari ključ je tada gutao
-- IZGLASANI redak ako je prijedlog scrapean prvi (KOEI FY2025: dps je na
-- produkciji postojao samo kao 'Prijedlog' pa je ispao iz financials).
DROP INDEX IF EXISTS uq_dividends_event;
CREATE UNIQUE INDEX IF NOT EXISTS uq_dividends_event_v2
  ON dividends (class_ticker, ex_date, amount_eur,
                COALESCE(payment_date, '0001-01-01'::date), div_type);
ALTER TABLE dividends
  DROP CONSTRAINT IF EXISTS dividends_class_ticker_ex_date_amount_eur_key;

-- HPB podatkovni fix (idempotentan): makni zbirni redak 17,54 s jednim
-- datumom, upiši dvije rate. Izvor: Odluke Glavne skupštine HPB d.d.
-- 24.7.2026. (EHO objava #67878) — "isplatom u iznosu od ... 8,77 EUR bruto
-- po dionici ... dospijeva dana 4. kolovoza 2026." + druga jednaka tražbina
-- "dospijeva dana 28. siječnja 2027." po ispunjenju uvjeta iz čl. 324. ZKI.
DELETE FROM dividends
 WHERE class_ticker='HPB' AND ex_date=DATE '2026-07-29'
   AND amount_eur=17.54 AND payment_date=DATE '2027-01-28';
INSERT INTO dividends (company_id, share_class_id, class_ticker, fiscal_year,
                       amount_eur, div_type, ex_date, record_date,
                       payment_date, source_url, note)
SELECT c.id, sc.id, 'HPB', 2025, t.amount, 'Izglasana dividenda',
       DATE '2026-07-29', DATE '2026-07-30', t.pay,
       'https://eho.zse.hr/obavijesti-izdavatelja/view/67878', t.note
FROM companies c
JOIN share_classes sc ON sc.company_id=c.id AND sc.ticker='HPB'
CROSS JOIN (VALUES
  (8.77, DATE '2026-08-04',
   '1. od 2 rate — Glavna skupština 24.7.2026. odobrila je ukupno 17,54 € po dionici, isplativo u dvije jednake rate po 8,77 €'),
  (8.77, DATE '2027-01-28',
   '2. od 2 rate (ukupno 17,54 € po dionici) — dospijeće 28.1.2027., uz uvjet smanjenja temeljnog kapitala iz čl. 324. Zakona o kreditnim institucijama')
) AS t(amount, pay, note)
WHERE c.ticker='HPB'
ON CONFLICT DO NOTHING;

-- M59 (nastavak): ISTA praksa rata i kod GS 19.12.2024. (EHO #58617) —
-- ukupno 23,90 € iz zadržane dobiti 2023., dvije rate po 11,95 €
-- (7.1.2025. i 26.6.2025., druga uz uvjet iz čl. 312.a ZKI). Stari dedup
-- ključ (klasa, ex-datum, iznos) je 2. ratu tiho progutao, pa je na
-- produkciji FY2023 stajao podcijenjen (11,95 umjesto 23,90).
INSERT INTO dividends (company_id, share_class_id, class_ticker, fiscal_year,
                       amount_eur, div_type, ex_date, record_date,
                       payment_date, source_url, note)
SELECT c.id, sc.id, 'HPB', 2023, 11.95, 'Izglasana dividenda',
       DATE '2024-12-23', DATE '2024-12-24', DATE '2025-06-26',
       'https://eho.zse.hr/obavijesti-izdavatelja/view/58617',
       '2. od 2 rate (ukupno 23,90 € po dionici iz zadržane dobiti 2023.) — dospijeće 26.6.2025., uz uvjet iz čl. 312.a Zakona o kreditnim institucijama'
FROM companies c
JOIN share_classes sc ON sc.company_id=c.id AND sc.ticker='HPB'
WHERE c.ticker='HPB'
ON CONFLICT DO NOTHING;
UPDATE dividends
   SET note='1. od 2 rate — Glavna skupština 19.12.2024. odobrila je ukupno 23,90 € po dionici iz zadržane dobiti 2023., isplativo u dvije jednake rate po 11,95 €'
 WHERE class_ticker='HPB' AND ex_date=DATE '2024-12-23'
   AND amount_eur=11.95 AND payment_date=DATE '2025-01-07' AND note IS NULL;
UPDATE dividends
   SET note='2. od 2 rate (ukupno 23,90 € po dionici iz zadržane dobiti 2023.) — dospijeće 26.6.2025., uz uvjet iz čl. 312.a Zakona o kreditnim institucijama'
 WHERE class_ticker='HPB' AND ex_date=DATE '2024-12-23'
   AND amount_eur=11.95 AND payment_date=DATE '2025-06-26' AND note IS NULL;

-- M63a: admin oznaka za vlasnika (boris.cubric@gmail.com) — idempotentno i
-- SIGURNO prije registracije: čim se račun pojavi u auth.users, prvi
-- sljedeći run ga promovira. Guard: lokalni dev nema auth shemu ni
-- profiles.is_admin (Supabase-only migracije) — tada no-op.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema='auth' AND table_name='users')
     AND EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='profiles'
                   AND column_name='is_admin') THEN
    UPDATE public.profiles p SET is_admin = true
    FROM auth.users u
    WHERE u.id = p.id AND lower(u.email) = 'boris.cubric@gmail.com'
      AND NOT p.is_admin;
  END IF;
END $$;

-- M66: dedup ključ dividendi v3 — v2 (s punim div_type) je uz prijedlog
-- propustio i TREĆI zapis iste isplate s drugim tipom ('cash' sa zse.hr
-- stranice papira uz 'Izglasana dividenda' s EHO-a): SNBA 0,72 € se
-- prikazivala dvaput, a povijest je zbrajala 1,44 €. Ključ razlikuje SAMO
-- prijedlog od stvarne isplate; među stvarnima ostaje jedan zapis
-- (prednost 'Izglasana%' — nosi puni EHO izvor).
DELETE FROM dividends d USING dividends k
 WHERE d.id <> k.id
   AND d.class_ticker = k.class_ticker
   AND d.ex_date IS NOT NULL AND d.ex_date = k.ex_date
   AND d.amount_eur = k.amount_eur
   AND COALESCE(d.payment_date, '0001-01-01') = COALESCE(k.payment_date, '0001-01-01')
   AND d.div_type NOT ILIKE '%rijedlog%' AND k.div_type NOT ILIKE '%rijedlog%'
   AND (CASE WHEN d.div_type ILIKE 'Izglasana%' THEN 0 ELSE 1 END, d.id)
     > (CASE WHEN k.div_type ILIKE 'Izglasana%' THEN 0 ELSE 1 END, k.id);
DROP INDEX IF EXISTS uq_dividends_event_v2;
CREATE UNIQUE INDEX IF NOT EXISTS uq_dividends_event_v3
  ON dividends (class_ticker, ex_date, amount_eur,
                COALESCE(payment_date, '0001-01-01'::date),
                (div_type ILIKE '%rijedlog%'));

-- M66: vijesti nose datum objave NA IZVORU (EHO/ZSE), ne trenutak našeg
-- uvoza. Idempotentna noćna korekcija postojećih auto vijesti iz izvora
-- (filings.published_at; za dividende datum EHO objave kroz announcements).
-- Guard: lokalni dev nema news_items (Supabase-only migracija) — no-op.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema='public' AND table_name='news_items') THEN
    UPDATE news_items n
       SET published_at = f.published_at::timestamptz
      FROM filings f
     WHERE n.source_type = 'auto'
       AND n.auto_source_ref = 'filing:' || f.id
       AND f.published_at IS NOT NULL
       AND (n.published_at IS NULL OR n.published_at::date <> f.published_at);
    UPDATE news_items n
       SET published_at = COALESCE(a.published_at, d.published_at)::timestamptz
      FROM dividends d
      LEFT JOIN announcements a ON a.external_id = d.source_url
     WHERE n.source_type = 'auto'
       AND n.auto_source_ref = 'dividend:' || d.id
       AND COALESCE(a.published_at, d.published_at) IS NOT NULL
       AND (n.published_at IS NULL
            OR n.published_at::date <> COALESCE(a.published_at, d.published_at));
    -- M66: 'najava isplate' nastala NAKON ex-datuma je backfill artefakt
    -- (nikad nije bila aktualna najava) -> makni iz objavljenih (draft);
    -- incident 4.8.2026.: ~200 povijesnih rata preplavilo /vijesti
    UPDATE news_items n SET status = 'draft'
      FROM dividends d
     WHERE n.source_type = 'auto'
       AND n.auto_source_ref = 'dividend:' || d.id
       AND n.status = 'published'
       AND d.ex_date IS NOT NULL
       AND d.ex_date < n.created_at::date - 7;
    -- M66: vijest čiji izvorni zapis više ne postoji (dedup v3 briše
    -- duplikate dividendi) ostaje siroče s dupliciranim naslovom
    -- (npr. JNAF 2x) -> makni iz objavljenih
    UPDATE news_items n SET status = 'draft'
     WHERE n.source_type = 'auto'
       AND n.status = 'published'
       AND n.auto_source_ref LIKE 'dividend:%'
       AND NOT EXISTS (SELECT 1 FROM dividends d
                       WHERE 'dividend:' || d.id = n.auto_source_ref);
    UPDATE news_items n SET status = 'draft'
     WHERE n.source_type = 'auto'
       AND n.status = 'published'
       AND n.auto_source_ref LIKE 'filing:%'
       AND NOT EXISTS (SELECT 1 FROM filings f
                       WHERE 'filing:' || f.id = n.auto_source_ref);
    -- M66.1: vijest iz PRIJEDLOGA dividende je duplikat kad postoji i
    -- objavljena vijest iz izglasane dividende iste isplate (JNAF 2x
    -- "Najavljena isplata ... 20,21 €") -> prijedlog-vijest u draft
    UPDATE news_items n SET status = 'draft'
      FROM dividends dp
     WHERE n.source_type = 'auto'
       AND n.status = 'published'
       AND n.auto_source_ref = 'dividend:' || dp.id
       AND dp.div_type ILIKE '%rijedlog%'
       AND EXISTS (
             SELECT 1 FROM dividends di
             JOIN news_items n2 ON n2.auto_source_ref = 'dividend:' || di.id
            WHERE di.company_id = dp.company_id
              AND di.amount_eur = dp.amount_eur
              AND COALESCE(di.fiscal_year, 0) = COALESCE(dp.fiscal_year, 0)
              AND (di.div_type IS NULL OR di.div_type NOT ILIKE '%rijedlog%')
              AND n2.status = 'published');
  END IF;
END $$;

-- M70: dvojezični blog — svaki post nosi i englesku verziju (title_en,
-- meta_description_en, content_md_en); guard: blog_posts postoji samo u
-- Supabase produkciji. Prijevodi POSTOJEĆIH CMS postova su ispod
-- (idempotentno: samo dok je title_en NULL).
ALTER TABLE IF EXISTS blog_posts ADD COLUMN IF NOT EXISTS title_en TEXT;
ALTER TABLE IF EXISTS blog_posts ADD COLUMN IF NOT EXISTS meta_description_en TEXT;
ALTER TABLE IF EXISTS blog_posts ADD COLUMN IF NOT EXISTS content_md_en TEXT;

-- M69: top 10 dioničara PO KLASI dionice — ZSE stranica papira objavljuje
-- zasebnu listu za svaki ISIN (CROS i CROS2 imaju različite imatelje).
-- Postojeći redovi su skidani s primarne klase -> backfill; unique ključ
-- dobiva class_ticker da snapshoti klasa koegzistiraju.
ALTER TABLE shareholders ADD COLUMN IF NOT EXISTS class_ticker TEXT;
UPDATE shareholders s SET class_ticker = COALESCE(
    (SELECT sc.ticker FROM share_classes sc
      WHERE sc.company_id = s.company_id AND sc.is_primary_line LIMIT 1),
    (SELECT sc2.ticker FROM share_classes sc2
      WHERE sc2.company_id = s.company_id ORDER BY sc2.id LIMIT 1))
  WHERE s.class_ticker IS NULL;
ALTER TABLE shareholders DROP CONSTRAINT IF EXISTS
  shareholders_company_id_snapshot_date_source_rank_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_shareholders_snap
  ON shareholders (company_id, class_ticker, snapshot_date, source, rank);

-- M67: newsletter — minimizacija podataka (GDPR čl. 5. st. 1. t. (c) i (e)):
-- nepotvrđena double opt-in prijava starija od 30 dana se briše (privola
-- nikad nije dovršena). Potvrđeni i odjavljeni zapisi OSTAJU (dokaz privole
-- i lista isključenja). Guard: tablicu kreira supabase/migration_newsletter.sql
-- (Supabase-only) — lokalni dev bez nje = no-op.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema='public' AND table_name='newsletter_subscribers') THEN
    DELETE FROM newsletter_subscribers
     WHERE status = 'pending' AND created_at < now() - interval '30 days';
  END IF;
END $$;

-- M70: prijevodi postojeća 4 CMS posta (idempotentno — samo dok je
-- title_en NULL; novi postovi dolaze dvojezično kroz admin/blog-publish)
DO $m70$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema='public' AND table_name='blog_posts') THEN

    UPDATE blog_posts SET
      title_en = 'Burzovni list is live: value analysis for every Zagreb Stock Exchange stock',
      meta_description_en = 'Burzovni list is live: free analysis and fair value for every Zagreb Stock Exchange stock — indicators, dividend calendar, screener and comparison.',
      content_md_en = $md$The Zagreb Stock Exchange has a new home for everyone who wants to understand what sits behind a share price. **Burzovni list** is live as of today — a free, informational platform with fundamental analysis for **all 73 share classes** listed on the Zagreb Stock Exchange.

## What we offer

For every stock — from the most liquid names like HT, Podravka or Končar to those that trade rarely — Burzovni list shows:

- **The fair-value zone**: an estimated range of the share's value derived from several valuation methods, shown next to the current market price.
- **Key indicators**: profitability, leverage, liquidity and trends from the financial statements, presented clearly and comparably.
- **[Dividend calendar](/en/dividends)**: dates, amounts and payout history for every payer on the exchange.
- **[Screener](/en/screener) and [stock comparison](/en/comparison)**: filter the whole exchange by indicators or put several stocks side by side.
- **Portfolio tracking**: with free registration you can build your own list of stocks and follow it in one place.

All of the above is free and available without any subscription.

## How the estimates are made

All estimates are derived exclusively from **publicly published financial reports** and official Zagreb Stock Exchange data. For each stock we apply several valuation methods and present the result as a range — the fair-value zone — rather than a single "correct" number, because every valuation carries assumptions and uncertainty.

That is exactly why **all assumptions and the entire methodology are publicly available** on the [Methodology](/en/methodology) page. We want everyone to be able to check how we arrived at a number, not just read the result.

The data is updated **every trading day after the close**, based on official trading data, so you always find a fresh state in the morning.

## What Burzovni list is not

This is important to say clearly and without small print: **Burzovni list is not investment advice or a recommendation to buy or sell any stock.**

The fair-value zone is an informational display of what publicly available data and the chosen valuation methods say about a company's value — nothing more. A market price can deviate from anyone's value estimate for years, and every method has its limitations. We do not predict price movements and we promise no returns.

Our job is to present the data and the calculation transparently. **The conclusion always belongs to the reader** — ideally alongside your own research and, when needed, a conversation with a licensed adviser.

## Why we are doing this

Information about Croatian stocks is scattered across reports, filings and tables that are neither accessible nor readable for the average investor. We believe the domestic capital market deserves the kind of tool large world markets have had for a long time: a place where data, indicators and value estimates are available to everyone, free of charge.

Burzovni list is only at the beginning. We plan to keep expanding the content and tools, and reader feedback will steer what we build next.

## Start right away

Open the [screener](/en/screener) and filter the exchange by indicators, check the [dividend calendar](/en/dividends), [compare the stocks](/en/comparison) you are interested in, or simply pick a stock from the home page and look at its fair-value zone. If you want to track your portfolio, registration is free.

Welcome to Burzovni list.

---

*Burzovni list is an informational platform. The content does not constitute investment advice or a recommendation to trade financial instruments.*$md$
    WHERE slug = 'burzovni-list-je-online' AND title_en IS NULL;

    UPDATE blog_posts SET
      title_en = 'Pension funds (OMF): how to read accounting units and where the funds hold money on the ZSE',
      meta_description_en = 'Croatian mandatory pension funds: unit values by category, the Mirex benchmark, and the ZSE stocks where pension funds hold the largest stakes.',
      content_md_en = $md$Mandatory pension funds (OMF) manage the compulsory second-pillar savings of almost every employed person in Croatia. For most people it is the largest single financial position they have — and at the same time the one they look at least often. The data is public: HANFA publishes accounting-unit values monthly, and the ZSE and SKDD publish lists of the largest shareholders of individual companies. This text explains how to read that data, with figures as of **31 May 2026** available on our [pension funds page](/en/pension-funds).

A note before the numbers: this is a factual overview, not a ranking and not a recommendation. The categories differ in their permitted equity exposure, so comparing the returns of category A and category C makes no sense — they are different products with different purposes.

## Three categories, three different profiles

Each of the four OMFs (AZ, Erste Plavi, PBZ CO, Raiffeisen) offers three categories:

- **Category A** — the highest permitted equity exposure, intended for those with the most time left to retirement. Entry is voluntary.
- **Category B** — the default category members are assigned to if they do not choose another. Balanced exposure.
- **Category C** — predominantly bonds, mandatory for members in the last five years before retirement.

The logic is simple: the longer the period to payout, the larger the fluctuations in value that can be tolerated. That is why the numbers below differ so much between categories.

## What the accounting units show as of 31 May 2026

**Category A** — YTD returns range from +4.97% (Raiffeisen A) to +10.12% (Erste Plavi A). Over one year the range is +11.85% to +20.72%, and over ten years from +88.63% to +162.53%.

**Category B** — YTD from +2.73% (Raiffeisen B) to +7.50% (Erste Plavi B); one year +6.64% to +15.05%; ten years +54.97% to +97.75%.

**Category C** — YTD from +0.55% to +0.74%, one year +1.41% to +1.76%, ten years +27.50% to +35.39%.

The range within the same category is what is interesting. In category A the difference between the highest and the lowest ten-year return is about 74 percentage points. Over decades of saving that is not a cosmetic difference — but by itself it is no proof that the same ordering will hold in the future. A historical return is a fact about the past, nothing more.

## Mirex as a benchmark

Alongside each fund, **Mirex** is published — a composite return index of all funds in the same category. It is useful because it provides a benchmark without ranking the funds against each other: as of 31 May 2026 Mirex A was at +9.81% YTD, Mirex B +5.10%, Mirex C +0.58%.

Comparing an individual fund with the Mirex of the same category shows whether the fund was above or below the average of its group in the observed period. On the [chart on our page](/en/pension-funds) all series start from 100, so movements are compared directly, without absolute unit values.

## Where the OMFs actually hold money on the Zagreb Stock Exchange

The second part of the story is more concrete than percentages. Public top-10 shareholder lists show in which ZSE companies the pension industry is most present. According to the snapshot of 14 July 2026:

| Stock | Combined OMF stake |
| --- | --- |
| VILLA DUBROVNIK (VIDU) | 96.12% |
| MODRA ŠPILJA (MDSP) | 95.50% |
| JADRAN (JDRN) | 89.31% |
| VIS (VIS) | 86.95% |
| Quattro logistika (QTLG) | 78.92% |
| PROFESSIO ENERGIA (DLPR) | 78.53% |
| HELIOS FAROS (HEFA) | 76.98% |

For better-known names the stakes are lower but still significant: [Podravka](/en/stock/podr) 45.40%, [KONČAR – Elektroindustrija](/en/stock/koei) 37.29%, [Čakovečki mlinovi](/en/stock/ckml) 34.96%, [Atlantic Grupa](/en/stock/atgr) 29.19%, [Luka Rijeka](/en/stock/lkri) 30.28%.

Why is this worth knowing? A high share of institutional owners in practice means a smaller free float — fewer shares that actually circulate in the market. That affects liquidity and how much the price moves on relatively small orders. It is neither good nor bad news in itself; it is a characteristic worth keeping in mind when looking at a stock's daily turnover.

## The third pillar: voluntary funds

Alongside the mandatory funds, voluntary pension funds (DMF) also appear in the shareholder lists. According to our snapshots, the largest by market value of ZSE positions are **AZ Profit** (€81.65M, 17 positions in top-10 lists) and **Raiffeisen DMF** (€58.32M, 10 positions), followed by Erste Plavi Expert (€8.14M) and AZ Benefit (€3.57M).

An open DMF is available to anyone, while a closed one is tied to an employer or a professional group — the lists include the AZ Zaba, Cestarski, Erste, Nestlé and Pošta closed DMFs, all with small ZSE positions. It should be stressed: this is not a register of all voluntary funds in Croatia, only those that appear in publicly published top-10 shareholder lists.

## How to use this data

A few practical notes:

1. **Check which category you are in.** If you never chose, you are probably in B. Switching to A or C is your decision and depends on how much time you have to retirement — not on which category had the higher return last year.
2. **The data lags by a month.** HANFA publishes units monthly, so the freshest common cut-off is always the end of the previous month. For daily market movements the [ZSE indices](/en/indices) are more useful.
3. **Compare within a category.** Fund A against fund A, with Mirex A as the benchmark. Any other comparison mixes different risk profiles.
4. **Return is not the only criterion.** Fees, portfolio structure and consistency of strategy through cycles are equally part of the picture, and they are not visible in a single number.

All the figures above and their sources are available on the [Pension funds](/en/pension-funds) page, and the calculation method is described in the [methodology](/en/methodology).

---

*Sources: HANFA public releases (accounting units, as of 31 May 2026), ZSE/SKDD top-10 shareholder lists (snapshot 14 July 2026). This text is informational and presents a factual overview of publicly published data. It contains no investment recommendations or advice, is not an invitation to buy or sell any financial instrument, and guarantees no future returns. Past returns are not an indicator of future results.*$md$
    WHERE slug = 'mirovinski-fondovi-omf-jedinice-prinosi-zse' AND title_en IS NULL;

    UPDATE blog_posts SET
      title_en = 'AD Plastik (ADPL): reading an auto-parts supplier''s numbers — revenue, EBITDA margin and the fair-value zone',
      meta_description_en = 'AD Plastik (ADPL) data analysis: revenue 2023-2025, EBITDA margin, P/E 7.5, P/B 0.94, fair-value zone and dividend. Informational, not a recommendation.',
      content_md_en = $md$AD Plastik (ADPL) is one of the rarer stocks on the Zagreb Stock Exchange where the past three years brought a visible change in the business numbers themselves, not only in the price. This text walks through the data we hold on ADPL in the Burzovni list database and explains **how such data is read** — without a conclusion on whether the stock is a good or bad buy. That conclusion is not our job.

## What the company does

AD PLASTIK d.d. develops and manufactures plastic components for the automotive industry: interior and exterior solutions, from development and engineering to serial production. The core of the technology portfolio is injection moulding, along with surface treatment and painting, extrusion and blow-moulding technology (annual report, pp. 11 and 25).

Beyond the core business, the report also mentions entry into the **commercial vehicles segment** with project activities aimed at the logistics sector (p. 8).

The company operates in markets across Europe (Belgium, Czechia, France, Italy, Hungary, Germany, Poland, Romania, Russia, Slovakia, Slovenia, Serbia, Spain, Sweden, United Kingdom) and overseas (Argentina, Brazil, Mexico, Turkey, USA, Morocco, Egypt, India, Vietnam, Taiwan, South Korea) — p. 22. Key customers listed are Ford, Mercedes, Renault Group, Stellantis, Suzuki, Togg, Vaz and Volkswagen Group (p. 23).

This matters more for reading the numbers than it first appears: **ADPL is a second-tier supplier to the industry.** Revenue does not depend on its own sales to end customers but on the production plans of large automotive groups. That is the frame in which everything else is read.

## Three years of revenue and margin

The report data as it stands in our database:

| Fiscal year | Revenue | EBITDA margin |
| --- | --- | --- |
| FY2023 | €129.5M | 5.6% |
| FY2024 | €152.4M (+17.8%) | 8.8% |
| FY2025 | €157.9M (+3.6%) | 12.2% |

Over the whole period revenue grew 21.9%.

What is worth noticing here is not the revenue growth but **its shape**: a jump of almost 18% in 2024, then a slowdown to 3.6% in 2025. At the same time the EBITDA margin kept rising even in the slowdown year — from 8.8% to 12.2%.

Those are two different stories in the same table. Revenue growth comes from outside (customer orders). Margin growth with stagnating revenue comes from inside — from the cost structure, the product mix or prices. When the two lines diverge, it is useful to watch **how much of the margin held in the following period**, because a one-off improvement is something entirely different from a lasting change in profitability. The full set of line items is on the [ADPL financials page](/en/stock/adpl/financials).

## Indicators: P/E 7.5 and P/B 0.94

On 31 July 2026 ADPL closed at **€25.70** (−1.15%), with a market capitalisation of about **€107M**, a 52-week range of **€13.30–31.30** and average daily turnover of **€137,964** (20 traded days, actual turnover).

Indicators from the database: **P/E 7.5** and **P/B 0.94**.

A P/B below 1 means the market capitalisation is lower than the book value of equity. That is often read as "cheap", but by itself the number says only one thing: **the market values the company's equity below its book amount.** The reasons can differ and be mutually exclusive — from scepticism about the sustainability of earnings, through assets the market considers overvalued on the books, to a simple lack of liquidity and interest. Here the last item is relevant: with average daily turnover below €140 thousand, ADPL is not a stock where positions change quickly.

A P/E of 7.5 is read in the same key — it is low relative to the broader European context, but for a cyclical automotive supplier a low P/E often reflects an expectation that earnings are not at a sustainable level. We explained how P/E is interpreted in more detail in [How to read the P/E ratio](/en/blog/kako-citati-pe-omjer). You can compare how ADPL's indicators look against the rest of the exchange in the [screener](/en/screener).

## The fair-value zone and the gap

Our estimated fair-value zone for ADPL is **€59.4–96.3**, which puts the market price of €25.70 **56.7% below the lower edge of the zone**.

Care is needed in reading this, and explicitly so. The fair-value zone is **a range derived from publicly published reports using a public methodology** — it is not a price target, not a forecast and not a recommendation. When the gap is this large, it usually means one of two things: either the market is pricing in something the historical reports do not show, or the model rests on assumptions that do not hold as well for this business profile as they do for more stable issuers. For a cyclical supplier with a concentrated customer base, the latter is entirely possible.

That is why the fair-value zone should never be read as a standalone number. It is **a starting point for a question**, not an answer. How it is constructed is described in the [methodology](/en/methodology), and a broader explanation of the concept itself in [What the fair-value zone is](/en/blog/sto-je-fer-zona).

## Dividend

For fiscal 2025 a dividend of **€0.80 per share** was paid, with an ex-date of 22 July 2026 and payment on 28 July 2026. It is **the only payout in the last five fiscal years** we have in the database, so the average equals that single payout and dividend growth is not computable (fewer than three years of data).

One payout does not make a dividend policy. Unlike issuers with a long payout record, no expectation can be derived from the data here — it can only be recorded that a payout happened. No upcoming payout is currently announced. An overview of all announced payouts on the ZSE is on the [dividends](/en/dividends) page.

## What you can actually use from all of this

Three things ADPL illustrates well as a general reading pattern:

1. **Revenue growth and margin growth are not the same information.** When they diverge, the question is which of the two lines carries the change.
2. **A low P/B and a low P/E are the beginning of an analysis, not a conclusion.** For a company exposed to other companies' production cycles, a low valuation often has an explanation that is not visible in the ratios themselves.
3. **Liquidity is part of the picture.** Average daily turnover below €140 thousand changes the practical meaning of every other number on the page.

Complete and regularly updated data — price, indicators, financials, reports and shareholder structure — is on the [ADPL stock page](/en/stock/adpl).

---

*An informational presentation of data from publicly published reports and official Zagreb Stock Exchange end-of-day data. Not investment advice or a recommendation to buy or sell. Prices are official ZSE closes, with a delay. Data as of 31 July 2026.*$md$
    WHERE slug = 'ad-plastik-adpl-prihodi-ebitda-marza-fer-zona' AND title_en IS NULL;

    UPDATE blog_posts SET
      title_en = 'ING-GRAD (IG): revenue +72.9% in three years, margin declining, dividend €3.00 — how to read the numbers',
      meta_description_en = 'ING-GRAD (IG): price €66.00, revenue €97.4M to €168.4M in three years, P/E 15.7, dividend €3.00 and a -28.2% gap to the fair-value zone. No recommendations.',
      content_md_en = $md$ING-GRAD (IG) is one of those names rarely mentioned in daily Zagreb Stock Exchange commentary, yet it doubled its revenue in three years. In this text we walk through the numbers as they stand in the Burzovni list database — no estimates, no recommendations, with a note of where each data point comes from.

All values in the text refer to the official Zagreb Stock Exchange end-of-day close of **7 August 2026** and the company's most recently published financial reports.

## What ING-GRAD does

ING-GRAD d.d. is a construction company headquartered in Zagreb, registered for specialised construction works. According to the notes to the financial statements, its main activity covers construction and finishing works, investment, design, construction supervision, the building of residential and commercial buildings, the sale of apartments and commercial space, and the sale of construction materials.

Its market is Croatia, with headquarters in Zagreb. The export share is not disclosed in the report — so we do not estimate it either.

This combination matters for reading the numbers that follow: ING-GRAD is not just a contractor but also an investor selling its own apartments and commercial space. A revenue structure that mixes contracted works and real-estate sales explains why the margin need not move in the same direction as revenue.

## Revenue: +72.9% in three years

| Fiscal year | Revenue | Change |
| --- | --- | --- |
| FY2023 | €97.4M | — |
| FY2024 | €128.9M | +32.3% |
| FY2025 | €168.4M | +30.7% |

Over the whole period that is growth of **+72.9%**, two years in a row at a rate above 30%.

The EBITDA margin over the same period goes: **15.9% → 17.3% → 15.4%**. So revenue is growing, but the margin fell back below its 2023 level in the final year. In absolute terms EBITDA still grows (from about €16M to about €26M), because 15.4% of €168M is more than 15.9% of €97M. But the direction of the margin is down — a fact worth keeping in mind when looking only at the revenue curve.

One step further down the income statement, the [consolidated statements of ING-GRAD](/en/stock/ig/financials) show for FY2024: operating revenue €128.0M, operating expenses €108.6M, depreciation €2.0M, operating profit (EBIT) **€20.3M**, profit before tax €20.6M, tax −€3.8M and **net profit €16.8M**. For FY2023 EBIT was €13.8M and net profit attributable to owners of the parent €11.5M.

The FY2025 line items in the consolidated table have not yet been extracted from the filing — with us an empty field means "not published / not extracted", never zero. More on how line items are standardised is in the [methodology](/en/methodology).

## Price, liquidity and indicators

The last market price is **€66.00** (7 Aug 2026, daily change −0.30%). Other data from the [IG stock profile](/en/stock/ig):

- **52-week range:** €52.40–75.40
- **Market capitalisation:** €263M
- **Average daily turnover:** €87,677 (20 traded days, actual turnover)
- **Liquidity:** traded on 240 of roughly 250 working days over the past year (96%)
- **P/E:** 15.7
- **P/B:** 12.52
- **Dividend yield:** 4.55% with DPS of €3.00

Liquidity of 96% of traded days is above average for the ZSE — the stock trades almost every day. Average daily turnover of €87,677 is nevertheless modest in absolute terms, so larger individual orders can move the price. That is not a judgement but a description of the mechanics of the market being looked at.

A P/E of 15.7 and a P/B of 12.52 together say the market pays relatively little for profit and relatively much for book value. For a builder that does part of its work on other people's land and with a large share of payables, a low book base is not unusual — but the combination of those two numbers means P/B carries less information here than for, say, a bank or a hotelier. If these ratios are not your daily tool, a short explanation is in [how to read the P/E ratio](/en/blog/kako-citati-pe-omjer).

## Dividend: three payouts in five years, but rising

ING-GRAD paid a dividend in **3 of the last 5 fiscal years** (our data starts with FY2023):

| Fiscal year | Amount per share | Type | Ex-date | Payment |
| --- | --- | --- | --- | --- |
| FY2025 | €3.00 | regular | 22 Jul 2026 | 29 Jul 2026 |
| FY2024 | €2.60 | regular | 3 Jul 2025 | 10 Jul 2025 |
| FY2023 | €0.43 | — | — | — |

The average payout over the period is €2.01 per share, and dividend growth measured as a CAGR from FY2023 to FY2025 is +164.3% per year — a number that looks dramatic primarily because the starting base (€0.43) was very low.

With the payout policy so far — about **62% of profit** in years with a regular dividend — the expected dividend per share comes out at **€2.94**. That is a quantity derived from the company's behaviour so far, not an announcement. No upcoming payout is currently announced; the last one was paid on 29 July 2026.

The full calendar of payouts and announcements for all ZSE stocks is on the [dividends](/en/dividends) page.

## The gap to the fair-value zone

Our fair-value zone for IG is **€92–124**, and the market price of €66.00 sits **28.2% below the lower edge of that zone**.

It is important to be precise about what that number is and what it is not. The fair-value zone is a range that comes out of publicly published reports and a publicly published methodology — it is not a price target, not a forecast and not a recommendation. The −28.2% gap is a factual statement about the relation of two numbers: where the price is and where the lower edge of the range is. Why the gap is what it is, and whether the market is right or not, the text does not claim. More on the concept itself is in [what the fair-value zone is](/en/blog/sto-je-fer-zona).

For context: with a gap this pronounced at a builder, three questions are usually asked — how much of the revenue growth is repeatable (contracted works have an end date), how much of the profit is tied to one-off real-estate sales, and what the structure of liabilities looks like. The answers are in the reports themselves, not in the ratios.

## Sector context

On Friday 7 August 2026 **CROBEXkonstrukt fell 2.13%**, while the broader market measured by CROBEX slipped 0.24% (to 4,430.63 points, YTD +14.87%). Construction was among the weaker sectors on the exchange that day — INGRA lost 5.50%, and Dalekovod, with turnover of about €69 thousand, was the sixth most traded stock of the day.

Current values of all ZSE indices are on the [indices](/en/indices) page, and you can compare IG with other stocks by indicators in the [screener](/en/screener).

## What to actually say about these numbers

A summary of the facts, without a conclusion:

- Revenue has grown two years in a row at a rate above 30%, in total +72.9% over three years.
- The EBITDA margin fell over the same period from a peak of 17.3% to 15.4%, although EBITDA grows in absolute terms.
- FY2024 net profit is €16.8M per the consolidated statements.
- The dividend was paid in three of five years and rose from €0.43 to €3.00 per share.
- The price of €66.00 is 28.2% below the lower edge of our €92–124 fair-value zone.
- Liquidity is high by traded days (96%), but turnover is small in absolute terms (about €88 thousand a day).

Which of these facts you consider important and what conclusion you draw from them — that is your business. Burzovni list gives no buy or sell recommendations and promises no returns; it presents publicly published data in one place, with a source next to every number.

---

*Sources: the IG stock profile and financial statements on Burzovni list (data from annual and consolidated reports published via EHO/ZSE), official Zagreb Stock Exchange end-of-day closes for 7 Aug 2026, the dividend calendar from issuers' EHO filings.*

*Informational content — not investment advice, a recommendation or an inducement to trade. The data may contain errors; the issuers' and the Zagreb Stock Exchange's original publications are authoritative.*$md$
    WHERE slug = 'ing-grad-ig-prihodi-ebitda-dividenda-fer-zona' AND title_en IS NULL;

  END IF;
END $m70$;
