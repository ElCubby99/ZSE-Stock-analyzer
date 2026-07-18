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
