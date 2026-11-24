
CREATE TABLE IF NOT EXISTS hourly_weather (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source VARCHAR(100) NOT NULL,
    location_name VARCHAR(100) NOT NULL,

    measurement_time TIMESTAMPTZ NOT NULL,

    temperature_celsius DOUBLE PRECISION,
    relative_humidity_percent DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    wind_speed_kmh DOUBLE PRECISION,

    raw_data_id BIGINT REFERENCES raw_weather_data(id),

    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_hourly_weather_source_location_time
        UNIQUE (source, location_name, measurement_time),

    CONSTRAINT chk_relative_humidity
        CHECK (
            relative_humidity_percent IS NULL
            OR (relative_humidity_percent >= 0
                AND relative_humidity_percent <= 100)
        ),

    CONSTRAINT chk_precipitation
        CHECK (
            precipitation_mm IS NULL
            OR precipitation_mm >= 0
        ),

    CONSTRAINT chk_wind_speed
        CHECK (
            wind_speed_kmh IS NULL
            OR wind_speed_kmh >= 0
        )
);

CREATE INDEX IF NOT EXISTS idx_hourly_weather_location_time
ON hourly_weather (location_name, measurement_time DESC);
