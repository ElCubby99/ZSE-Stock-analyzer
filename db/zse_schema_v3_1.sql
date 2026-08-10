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
