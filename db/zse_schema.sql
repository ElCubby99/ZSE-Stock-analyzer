-- ============================================================
--  ZSE FUNDAMENTAL ANALYTICS — Postgres schema (MVP: Končar)
--  Dizajn: raw "long" fact table s provenijencijom + confidence,
--  iznad njega derived sloj (canonical metrics, ratios, valuations).
--  Validacija i valuacija žive u kodu/SQL-u, ne u LLM-u.
-- ============================================================

-- ---------- 1. COMPANIES ----------
CREATE TABLE companies (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL UNIQUE,        -- 'KOEI'
    isin            TEXT UNIQUE,                 -- TODO: provjeri točan ISIN na zse.hr (ne izmišljaj)
    name            TEXT NOT NULL,               -- 'KONČAR - Elektroindustrija d.d.'
    sector          TEXT NOT NULL,               -- 'industrial' | 'bank' | 'insurance' | 'tourism' | 'utility' ...
                                                 -- DRIVA rutanje valuacijske metode. Krivi sektor = kriva metoda.
    is_group        BOOLEAN DEFAULT TRUE,        -- objavljuje li konsolidirano (Končar = grupa => TRUE)
    base_currency   TEXT NOT NULL DEFAULT 'EUR',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ---------- 2. FILINGS ----------
-- Svaki dokument koji ingestamo. Metapodaci ovdje su kritični:
-- pogrešan period_type/basis/scale tiho pokvari sve nizvodno.
CREATE TABLE filings (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    doc_type        TEXT NOT NULL,               -- 'financial_report'|'annual_report'|'dividend'|'gsa'
                                                 -- |'manager_transaction'|'buyback'|'capital_change'|'other'
    fiscal_year     INTEGER,
    period_type     TEXT,                        -- 'annual'|'Q1'|'H1'|'9M'  (NULL za ne-financijske objave)
    basis           TEXT,                        -- 'consolidated'|'standalone'  (NIKAD ne miješaj u analizi)
    audited         BOOLEAN,
    cumulative      BOOLEAN,                     -- ZAMKA: IFRS interim brojke su obično KUMULATIVNE (YTD).
                                                 -- H1 = 6 mjeseci, 9M = 9 mjeseci. Ako misliš da je Q diskretan
                                                 -- a zapravo je YTD => dupliciraš ili krivo uspoređuješ.
    period_start    DATE,
    period_end      DATE,
    currency        TEXT,                        -- 'EUR' (od 2023), 'HRK' (do 2022, fiksno 7.53450)
    reporting_scale BIGINT DEFAULT 1,            -- ZAMKA: hrv. izvješća često u '000 EUR (scale=1000)
                                                 -- ili milijunima (1000000). value_eur = value_raw * scale.
    source_url      TEXT NOT NULL,
    published_at    DATE,
    status          TEXT DEFAULT 'pending',      -- 'pending'|'extracted'|'validated'|'needs_review'|'failed'
    ingested_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (company_id, doc_type, fiscal_year, period_type, basis)
);

-- ---------- 3. FINANCIALS (raw fact table, "long") ----------
-- Jedan red = jedna stavka iz jednog izvješća. Svaka brojka nosi izvor i confidence.
-- Restatement handling: kasniji filing za isti period nadjačava — "latest filing wins"
-- (vidi view v_financials_current niže).
CREATE TABLE financials (
    id              BIGSERIAL PRIMARY KEY,
    filing_id       INTEGER NOT NULL REFERENCES filings(id),
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    fiscal_year     INTEGER NOT NULL,
    period_type     TEXT NOT NULL,
    basis           TEXT NOT NULL,
    statement       TEXT NOT NULL,               -- 'income'|'balance'|'cashflow'|'shares'
    item            TEXT NOT NULL,               -- kanonski ključ (vidi taksonomiju u extraction promptu)
    value_raw       NUMERIC,                     -- kako piše u izvješću (prije scale/valute)
    value_eur       NUMERIC,                     -- normalizirano: raw * scale, HRK->EUR ako treba
    confidence      NUMERIC,                     -- 0..1 od extractora
    source_page     TEXT,                        -- str./bilješka za audit trail
    is_reported     BOOLEAN DEFAULT TRUE,        -- TRUE=pročitano; FALSE=mi izračunali (npr. net_debt)
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_fin_lookup ON financials (company_id, fiscal_year, period_type, basis, item);

-- View: trenutno važeća brojka po periodu (najnoviji filing pobjeđuje => hvata restatemente)
CREATE VIEW v_financials_current AS
SELECT DISTINCT ON (company_id, fiscal_year, period_type, basis, item)
       company_id, fiscal_year, period_type, basis, statement, item,
       value_eur, confidence, source_page, filing_id
FROM   financials f
ORDER  BY company_id, fiscal_year, period_type, basis, item,
          (SELECT published_at FROM filings WHERE id = f.filing_id) DESC NULLS LAST;

-- ---------- 4. PRICES (EOD) ----------
CREATE TABLE prices_eod (
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    trade_date  DATE NOT NULL,
    close_eur   NUMERIC,
    volume      NUMERIC,                          -- ZAMKA: ako je volume 0/NULL, dionica nije trgovala —
                                                  -- "zadnja cijena" je stara. Frontend to mora označiti.
    source      TEXT,
    PRIMARY KEY (company_id, trade_date)
);

-- ---------- 5. RATIOS (derived) ----------
CREATE TABLE ratios (
    company_id     INTEGER NOT NULL REFERENCES companies(id),
    as_of_date     DATE NOT NULL,
    market_cap_eur NUMERIC,
    ev_eur         NUMERIC,
    pe             NUMERIC,
    ev_ebitda      NUMERIC,
    pb             NUMERIC,
    dividend_yield NUMERIC,
    PRIMARY KEY (company_id, as_of_date)
);

-- ---------- 6. VALUATIONS (sektorski svjesne, raspon + pretpostavke) ----------
CREATE TABLE valuations (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    as_of_date  DATE NOT NULL,
    method      TEXT NOT NULL,                    -- 'dcf'|'multiples_peer'|'ddm'|'pb_roe'
    value_low   NUMERIC,
    value_base  NUMERIC,
    value_high  NUMERIC,
    assumptions JSONB,                            -- {wacc, g, peer_set, multiple, ...} — MORA biti vidljivo na sajtu
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------- 7. ANNOUNCEMENTS (watcher log) ----------
CREATE TABLE announcements (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    published_at  DATE,
    title         TEXT,
    category      TEXT,                           -- klasifikator: 'financial_report'|'dividend'|...
    confidence    NUMERIC,
    source_url    TEXT,
    action_taken  TEXT,                           -- 'extraction_triggered'|'logged'|...
    needs_review  BOOLEAN DEFAULT FALSE,          -- low-confidence ide tebi na pregled, NE tiho u bazu
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ---------- SEED (MVP) ----------
INSERT INTO companies (ticker, name, sector, is_group)
VALUES ('KOEI', 'KONČAR - Elektroindustrija d.d.', 'industrial', TRUE);
-- ISIN ostavi NULL dok ne provjeriš na zse.hr — radije prazno nego izmišljeno.
