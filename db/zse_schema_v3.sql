-- ============================================================
--  ZSE ANALYTICS — schema v3 (orchestrator, M6). Pokreni NAKON v1+v2.
--  Idempotentno (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
--  Vidi docs/zse_orchestrator_spec.md (+ dogovorena izmjena: sector_assigned).
-- ============================================================

ALTER TABLE companies ADD COLUMN IF NOT EXISTS tier SMALLINT;              -- 1|2|3
ALTER TABLE companies ADD COLUMN IF NOT EXISTS onboarding_status TEXT DEFAULT 'discovered';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_live BOOLEAN DEFAULT FALSE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS data_limited BOOLEAN DEFAULT FALSE;
-- IZMJENA speca: sektor se dodjeljuje s confidenceom PRIJE ekstrakcije
ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector_confidence NUMERIC;

CREATE TABLE IF NOT EXISTS watcher_state (
    source       TEXT PRIMARY KEY,            -- 'zse_disclosure'
    last_seen_id TEXT,
    last_run_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT,
    stage       TEXT,       -- 'watcher'|'extract'|'validate'|'value'|'prices'|'regen'|'onboard:*'
    company_id  INTEGER REFERENCES companies(id),
    status      TEXT,       -- 'ok'|'skipped'|'needs_review'|'failed'
    message     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run ON pipeline_runs (run_id);

-- Dedup objava (Dio B korak 2): UNIQUE po ID-u objave (EHO link).
ALTER TABLE announcements ADD COLUMN IF NOT EXISTS external_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_announcements_ext ON announcements (external_id)
    WHERE external_id IS NOT NULL;

-- Ekstrakcijski queue: filings.status='pending' (bez nove tablice) — filings
-- unique ključ već postoji; pending redovi nose izvor u source_url.

-- State machine ima eksplicitnu fazu "sektor nepoznat" (prije sector_assigned):
-- v1 NOT NULL na companies.sector više ne odgovara modelu.
ALTER TABLE companies ALTER COLUMN sector DROP NOT NULL;

-- Profil dionice (priprema podataka): povijesni EOD backfill sa službenog
-- zse.hr securityHistory endpointa nosi i STVARNI dnevni promet (turnover_n)
-- — točniji od aproksimacije close×volumen za liquidity prag od 5.000 €.
ALTER TABLE prices_eod ADD COLUMN IF NOT EXISTS turnover_eur NUMERIC;

-- M10: kalibracija iz tržišnih serija (src/calibrate.py)
CREATE TABLE IF NOT EXISTS index_eod (
    index_isin  TEXT NOT NULL,
    trade_date  DATE NOT NULL,
    close_value NUMERIC NOT NULL,
    source      TEXT,
    PRIMARY KEY (index_isin, trade_date)
);
CREATE TABLE IF NOT EXISTS calibrations (
    key         TEXT PRIMARY KEY,     -- 'beta:<TICKER>' | 'holding_discount:ADRS'
    value       JSONB NOT NULL,       -- metoda + brojke + ograde
    source      TEXT,
    computed_at TIMESTAMPTZ DEFAULT now()
);

-- M9: profil poslovanja — ČINJENICE iz izvješća s citatima po stranicama.
-- Epiteti izdavatelja idu ODVOJENO u issuer_claims (označeni kao tvrdnja).
CREATE TABLE IF NOT EXISTS business_profiles (
    company_id  INTEGER PRIMARY KEY REFERENCES companies(id),
    fiscal_year INTEGER,
    activity    TEXT,            -- djelatnost, neutralno, 1-2 rečenice
    activity_source_page TEXT,
    segments    JSONB,           -- [{name, description|null, source_page}]
    markets     JSONB,           -- [{market, source_page}]
    export_share JSONB,          -- {value, basis, source_page} | NULL (samo ako objavljen)
    issuer_claims JSONB,         -- [{claim, source_page}] — tvrdnje izdavatelja, citirane
    source      TEXT,            -- dokument + metoda (API ekstrakcija / ručno s citatima)
    extracted_at TIMESTAMPTZ DEFAULT now()
);

-- M19-A: praćenje troška API poziva (ekstrakcija/klasifikacija) + budžet alarm.
-- Cijene po modelu drže se u config/api_pricing.json (NE hardkodirano).
CREATE TABLE IF NOT EXISTS api_usage (
    id            SERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
    ticker        TEXT,                 -- firma (NULL = nije vezano uz firmu)
    operation     TEXT NOT NULL,        -- extraction | segments | classification | ...
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_input_tokens     INTEGER NOT NULL DEFAULT 0,
    batch         BOOLEAN NOT NULL DEFAULT FALSE,
    est_cost_eur  NUMERIC NOT NULL     -- procjena iz config cijena u trenutku poziva
);
CREATE INDEX IF NOT EXISTS api_usage_ts_idx ON api_usage (ts);
CREATE INDEX IF NOT EXISTS api_usage_ticker_idx ON api_usage (ticker);
