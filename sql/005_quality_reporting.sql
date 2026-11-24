
CREATE OR REPLACE VIEW pipeline_quality_summary AS
SELECT
    location_name,
    pipeline_name,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    ROUND(
        AVG(quality_percentage)::numeric,
        2
    ) AS average_quality_percentage,
    SUM(records_received) AS total_records_received,
    SUM(records_accepted) AS total_records_accepted,
    SUM(records_rejected) AS total_records_rejected,
    ROUND(
        AVG(duration_seconds)::numeric,
        3
    ) AS average_duration_seconds
FROM pipeline_runs
GROUP BY location_name, pipeline_name;


CREATE OR REPLACE VIEW pipeline_quality_daily AS
SELECT
    location_name,
    pipeline_name,
    DATE(started_at AT TIME ZONE 'Asia/Karachi') AS run_date,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    ROUND(
        AVG(quality_percentage)::numeric,
        2
    ) AS average_quality_percentage,
    SUM(records_received) AS total_records_received,
    SUM(records_accepted) AS total_records_accepted,
    SUM(records_rejected) AS total_records_rejected
FROM pipeline_runs
GROUP BY
    location_name,
    pipeline_name,
    DATE(started_at AT TIME ZONE 'Asia/Karachi');
