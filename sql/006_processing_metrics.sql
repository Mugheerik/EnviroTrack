
ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_inserted INTEGER;

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_updated INTEGER;

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS records_unchanged INTEGER;

ALTER TABLE pipeline_runs
ADD CONSTRAINT chk_pipeline_load_metrics
CHECK (
    (records_inserted IS NULL OR records_inserted >= 0)
    AND (records_updated IS NULL OR records_updated >= 0)
    AND (records_unchanged IS NULL OR records_unchanged >= 0)
);
