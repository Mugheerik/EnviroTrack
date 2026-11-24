
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    location_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'running',

    records_processed INTEGER NOT NULL DEFAULT 0,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,

    duration_seconds DOUBLE PRECISION,

    error_message TEXT,

    CONSTRAINT chk_pipeline_status
        CHECK (status IN ('running', 'success', 'failed')),

    CONSTRAINT chk_pipeline_records
        CHECK (records_processed >= 0)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_location_started
ON pipeline_runs (location_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status_started
ON pipeline_runs (status, started_at DESC);
