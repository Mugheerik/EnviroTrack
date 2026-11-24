
ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_received INTEGER NOT NULL DEFAULT 0;

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_accepted INTEGER NOT NULL DEFAULT 0;

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_rejected INTEGER NOT NULL DEFAULT 0;

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS quality_percentage DOUBLE PRECISION;

ALTER TABLE pipeline_runs
ADD CONSTRAINT chk_pipeline_quality_counts
CHECK (
    records_received >= 0
    AND records_accepted >= 0
    AND records_rejected >= 0
    AND records_accepted + records_rejected <= records_received
);

ALTER TABLE pipeline_runs
ADD CONSTRAINT chk_pipeline_quality_percentage
CHECK (
    quality_percentage IS NULL
    OR (quality_percentage >= 0 AND quality_percentage <= 100)
);
