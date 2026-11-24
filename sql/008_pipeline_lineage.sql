ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS source_raw_data_id BIGINT
REFERENCES raw_weather_data(id);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_raw_data
ON pipeline_runs (source_raw_data_id);