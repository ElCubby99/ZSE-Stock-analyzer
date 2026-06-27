-- ============================================================
--  ZSE ANALYTICS — schema v2 (migracija na v1 iz zse_schema.sql)
--  Dodaje: klase dionica, vlasnički graf (SOTP), segmentni podaci.
--  Pokreni NAKON v1. Idempotentno (IF NOT EXISTS / OR REPLACE / ON CONFLICT).
-- ============================================================

-- ---------- 8. SHARE CLASSES ----------
-- Jedna firma (ADRS) može imati više uvrštenih klasa (ADRS redovna, ADRS2 povlaštena).
-- Fundamenti su na razini firme (konsolidirani FI = cijeli entitet).
-- Po klasi se razlikuju: cijena, broj dionica, glas, dividendni tretman, per-share.
CREATE TABLE IF NOT EXISTS share_classes (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    ticker          TEXT NOT NULL UNIQUE,        -- 'ADRS' | 'ADRS2'
    isin            TEXT UNIQUE,                 -- po KLASI (ADRS i ADRS2 imaju različit ISIN); NULL dok se ne provjeri na zse.hr
    class_type      TEXT NOT NULL,               -- 'ordinary' | 'preferred'
    shares_issued   NUMERIC,                     -- izdane dionice OVE klase
    treasury_shares NUMERIC DEFAULT 0,           -- vlastite dionice OVE klase
    has_voting      BOOLEAN,
    dividend_note   TEXT,                         -- npr. 'ista dividenda + prioritet'
    is_primary_line BOOLEAN DEFAULT FALSE         -- koja klasa je "glavna" za zadane prikaze
);

-- prices_eod i ratios idu po KLASI, ne po firmi (dvije cijene!).
ALTER TABLE prices_eod  ADD COLUMN IF NOT EXISTS share_class_id INTEGER REFERENCES share_classes(id);
ALTER TABLE ratios      ADD COLUMN IF NOT EXISTS share_class_id INTEGER REFERENCES share_classes(id);

-- KANONSKI broj dionica (rješava nesklad 92,1€ vs 89€ BVPS).
-- Pravilo: per-share valuacija koristi dionice BEZ trezorskih. Jedan izvor istine.
CREATE OR REPLACE VIEW v_shares_canonical AS
SELECT company_id,
       SUM(shares_issued)                               AS shares_issued_total,
       SUM(COALESCE(treasury_shares,0))                 AS treasury_total,
       SUM(shares_issued - COALESCE(treasury_shares,0)) AS shares_ex_treasury  -- <- koristi OVO
FROM   share_classes
GROUP  BY company_id;

-- ---------- 9. HOLDINGS (vlasnički graf — backbone SOTP-a) ----------
CREATE TABLE IF NOT EXISTS holdings (
    id                SERIAL PRIMARY KEY,
    parent_company_id INTEGER NOT NULL REFERENCES companies(id),
    held_company_id   INTEGER REFERENCES companies(id),   -- NULL ako neuvršten
    held_name         TEXT NOT NULL,
    ownership_pct     NUMERIC NOT NULL,
    listed            BOOLEAN NOT NULL,
    valuation_basis   TEXT NOT NULL,   -- 'market'|'ebitda_multiple'|'equity_method'|'book'
    segment_key       TEXT,            -- veza na segment_financials za ebitda_multiple
    default_multiple  NUMERIC,
    is_insurance      BOOLEAN DEFAULT FALSE,  -- ako TRUE i kontrola => EV/EBITDA matice kontaminiran
    as_of             DATE,
    source_page       TEXT,
    confidence        NUMERIC
);
CREATE INDEX IF NOT EXISTS idx_holdings_parent ON holdings (parent_company_id);
-- spriječi duple seed retke (idempotentni seed niže)
CREATE UNIQUE INDEX IF NOT EXISTS uq_holdings_parent_name ON holdings (parent_company_id, held_name);

-- ---------- 10. SEGMENT FINANCIALS (IFRS 8, iz bilješki) ----------
CREATE TABLE IF NOT EXISTS segment_financials (
    id           BIGSERIAL PRIMARY KEY,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    fiscal_year  INTEGER NOT NULL,
    period_type  TEXT NOT NULL,
    basis        TEXT NOT NULL,
    segment_key  TEXT NOT NULL,        -- 'tourism'|'insurance'|'aquaculture'|'energy'
    revenue      NUMERIC,
    ebitda       NUMERIC,
    net_result   NUMERIC,
    confidence   NUMERIC,
    source_page  TEXT
);
CREATE INDEX IF NOT EXISTS idx_seg_lookup ON segment_financials (company_id, fiscal_year, segment_key);

-- ZAMKA/validacija: Σ segment EBITDA ≠ Grupa EBITDA (eliminacije, trošak centra, NCI).
-- Ako |plug| > 15% grupne EBITDA => needs_review (vjerojatno krivi segment).

-- ---------- SOTP komponente (helper view) ----------
CREATE OR REPLACE VIEW v_sotp_inputs AS
SELECT h.parent_company_id,
       h.held_name,
       h.ownership_pct,
       h.listed,
       h.valuation_basis,
       h.is_insurance,
       h.held_company_id,
       h.segment_key,
       h.default_multiple
FROM   holdings h;

-- ============================================================
--  SEED — firme iz ADRS grafa (ISIN NULL dok se ne provjeri na zse.hr; NE izmišljaj)
--  sector DRIVA rutanje metode. ADRS='holding' (consolidates_insurer blokira EV/EBITDA),
--  CROS='insurance' (financijski sektor), MAIS='tourism'.
-- ============================================================
INSERT INTO companies (ticker, name, sector, is_group) VALUES
  ('ADRS', 'Adris grupa d.d.',        'holding',   TRUE),
  ('CROS', 'Croatia osiguranje d.d.', 'insurance', TRUE),
  ('MAIS', 'Maistra d.d.',            'tourism',   TRUE)
ON CONFLICT (ticker) DO NOTHING;

-- ADRS klase dionica (ISIN NULL dok se ne potvrdi na zse.hr)
INSERT INTO share_classes (company_id, ticker, class_type, has_voting, dividend_note, is_primary_line) VALUES
  ((SELECT id FROM companies WHERE ticker='ADRS'),  'ADRS',  'ordinary',  TRUE,  'redovna',                       TRUE),
  ((SELECT id FROM companies WHERE ticker='ADRS'),  'ADRS2', 'preferred', FALSE, 'povlaštena (ista div + prioritet)', FALSE)
ON CONFLICT (ticker) DO NOTHING;

-- ---------- SEED: ADRS holdinzi ----------
-- Postoci iz priloženog izvora; PROVJERI protiv Adris FI 2025 (bilješke) i zse.hr.
-- is_insurance=TRUE na CROS-u AUTOMATSKI diskvalificira EV/EBITDA za ADRS (vidi registar metoda).
INSERT INTO holdings (parent_company_id, held_company_id, held_name, ownership_pct, listed,
                      valuation_basis, segment_key, default_multiple, is_insurance, as_of, source_page, confidence) VALUES
  ((SELECT id FROM companies WHERE ticker='ADRS'), (SELECT id FROM companies WHERE ticker='CROS'),
     'Croatia osiguranje', 0.6747, TRUE,  'market',          'insurance',   NULL, TRUE,  '2025-12-31', 'seed/FI2025?', 0.80),
  ((SELECT id FROM companies WHERE ticker='ADRS'), (SELECT id FROM companies WHERE ticker='MAIS'),
     'Maistra',            0.9354, TRUE,  'market',          'tourism',     NULL, FALSE, '2025-12-31', 'seed/FI2025?', 0.80),
  ((SELECT id FROM companies WHERE ticker='ADRS'), NULL,
     'HUP-Zagreb',         1.0000, FALSE, 'ebitda_multiple', 'tourism',     7.5,  FALSE, '2025-12-31', 'seed/FI2025?', 0.70),
  ((SELECT id FROM companies WHERE ticker='ADRS'), NULL,
     'Cromaris',           1.0000, FALSE, 'ebitda_multiple', 'aquaculture', 8.0,  FALSE, '2025-12-31', 'seed/FI2025?', 0.70),
  ((SELECT id FROM companies WHERE ticker='ADRS'), NULL,
     'Energetika',         1.0000, FALSE, 'ebitda_multiple', 'energy',      7.0,  FALSE, '2025-12-31', 'seed/FI2025?', 0.70)
ON CONFLICT (parent_company_id, held_name) DO NOTHING;
