
CREATE TABLE IF NOT EXISTS raw_weather_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source VARCHAR(100) NOT NULL,
    location_name VARCHAR(100) NOT NULL,

    requested_latitude DOUBLE PRECISION NOT NULL,
    requested_longitude DOUBLE PRECISION NOT NULL,

    source_latitude DOUBLE PRECISION,
    source_longitude DOUBLE PRECISION,

    source_timezone VARCHAR(100),

    collected_at TIMESTAMPTZ NOT NULL,

    payload JSONB NOT NULL,

    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_weather_location_collected
ON raw_weather_data (location_name, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_weather_source_collected
ON raw_weather_data (source, collected_at DESC);
