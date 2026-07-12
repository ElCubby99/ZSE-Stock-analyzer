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
