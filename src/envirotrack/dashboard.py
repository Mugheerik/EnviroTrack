import os
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st

from envirotrack.db import DATABASE_URL

DB_URL = os.getenv("DATABASE_URL", DATABASE_URL)
LOCATION = "abbottabad"
TIMEZONE = ZoneInfo("Asia/Karachi")


st.set_page_config(
    
    page_title="EnviroTrack | Environmental Intelligence",
    page_icon="🌦️",
    layout="wide",
)
if st.button("Refresh dashboard"):
    st.cache_data.clear()
    st.rerun()


# --------------------------------------------------
# Weather code descriptions
# --------------------------------------------------


def weather_description(code):
    if code is None:
        return "Unknown"

    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    return descriptions.get(int(code), "Unknown")


def format_metric(value, unit="", precision=1):
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.{precision}f}{unit}"


# --------------------------------------------------
# Database access
# --------------------------------------------------


@st.cache_data(ttl=300)
def fetch_data(query: str, params: tuple = ()) -> pd.DataFrame:
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cursor:
        cursor.execute(query, params)
        columns = [column.name for column in cursor.description]
        rows = cursor.fetchall()

    return pd.DataFrame(rows, columns=columns)


def load_dashboard_data():
    forecast = fetch_data(
        """
        SELECT
            measurement_time,
            temperature_celsius,
            relative_humidity_percent,
            precipitation_mm,
            wind_speed_kmh
        FROM hourly_weather
        WHERE location_name = %s
          AND measurement_time >= NOW()
        ORDER BY measurement_time
        LIMIT 48
        """,
        (LOCATION,),
    )

    freshness = fetch_data(
        """
        SELECT
            MAX(collected_at) AS last_collected,
            COUNT(*) AS total_payloads
        FROM raw_weather_data
        WHERE location_name = %s
        """,
        (LOCATION,),
    )

    quality = fetch_data(
        """
    SELECT *
    FROM pipeline_quality_daily
    WHERE location_name = %s
      AND pipeline_name = 'hourly_weather_processing'
    ORDER BY run_date DESC
    LIMIT 14
    """,
        (LOCATION,),
    )

    runs = fetch_data(
        """
        SELECT
            id,
            pipeline_name,
            status,
            records_processed,
            duration_seconds,
            started_at,
            error_message
        FROM pipeline_runs
        WHERE location_name = %s
        ORDER BY started_at DESC
        LIMIT 15
        """,
        (LOCATION,),
    )

    return forecast, freshness, quality, runs


# --------------------------------------------------
# Latest current weather from original API payload
# --------------------------------------------------


@st.cache_data(ttl=300)
def load_current_weather():
    return fetch_data(
        """
        SELECT
            payload->'current' AS current_conditions
        FROM raw_weather_data
        WHERE location_name = %s
          AND payload ? 'current'
        ORDER BY collected_at DESC
        LIMIT 1
        """,
        (LOCATION,),
    )


# --------------------------------------------------
# Official daily forecast from original API payload
# --------------------------------------------------


@st.cache_data(ttl=300)
def load_daily_forecast():
    return fetch_data(
        """
        SELECT
            payload->'daily'->'time' AS dates,
            payload->'daily'->'temperature_2m_max'
                AS temperature_high,
            payload->'daily'->'temperature_2m_min'
                AS temperature_low,
            payload->'daily'->'rain_sum' AS rainfall,
            payload->'daily'->'precipitation_sum'
                AS precipitation,
            payload->'daily'->'precipitation_probability_max'
                AS precipitation_probability,
            payload->'daily'->'weather_code' AS weather_code
        FROM raw_weather_data
        WHERE location_name = %s
          AND payload ? 'daily'
        ORDER BY collected_at DESC
        LIMIT 1
        """,
        (LOCATION,),
    )


# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

st.title("🌦️ EnviroTrack")

st.caption("Environmental Data Platform | Abbottabad, Pakistan")

if st.button("↻ Refresh dashboard"):
    st.cache_data.clear()


try:
    forecast, freshness, quality, runs = load_dashboard_data()
    current_data = load_current_weather()
    daily_data = load_daily_forecast()

except psycopg.Error as error:
    st.error(f"Database error while loading dashboard: {error}")
    st.stop()


# --------------------------------------------------
# Data freshness
# --------------------------------------------------

st.header("Data Freshness")

last_collected = freshness.iloc[0]["last_collected"]

if pd.notna(last_collected):
    age_hours = (
        pd.Timestamp.now(tz="UTC") - pd.Timestamp(last_collected)
    ).total_seconds() / 3600

    freshness_status = "Fresh" if 0 <= age_hours <= 6 else "Stale"

    st.caption(
        f"Last data collection: "
        f"{last_collected.astimezone(TIMEZONE):%d %b %Y, %H:%M} PKT"
        f" | Status: {freshness_status}"
    )
else:
    st.warning("No raw weather data has been collected yet.")


# --------------------------------------------------
# Current weather conditions
# --------------------------------------------------

st.header("Current Weather Conditions")

if not current_data.empty:
    current = current_data.iloc[0]["current_conditions"]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Temperature",
        format_metric(current.get("temperature_2m"), " °C"),
    )

    col2.metric(
        "Feels Like",
        format_metric(current.get("apparent_temperature"), " °C"),
    )

    col3.metric(
        "Humidity",
        format_metric(current.get("relative_humidity_2m"), "%", 0),
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Wind Speed",
        format_metric(current.get("wind_speed_10m"), " km/h"),
    )

    col2.metric(
        "Current Rain",
        format_metric(current.get("rain"), " mm"),
    )

    col3.metric(
        "Current Precipitation",
        format_metric(current.get("precipitation"), " mm"),
    )

    st.caption(
        f"Conditions: "
        f"{weather_description(current.get('weather_code'))}"
        f" | API timestamp: {current.get('time', 'N/A')}"
    )

else:
    st.info("Current weather data is not available. Run ingestion to collect it.")


# --------------------------------------------------
# Hourly forecast
# --------------------------------------------------

st.header("Hourly Weather Forecast")

if forecast.empty:
    st.warning("No upcoming hourly forecast measurements available.")

else:
    forecast = forecast.copy()

    forecast["measurement_time"] = pd.to_datetime(
        forecast["measurement_time"], utc=True
    ).dt.tz_convert("Asia/Karachi")

    st.subheader("48-hour Temperature Forecast")

    temperature_chart = px.line(
        forecast,
        x="measurement_time",
        y="temperature_celsius",
        markers=True,
        labels={
            "measurement_time": "Forecast time",
            "temperature_celsius": "Temperature (°C)",
        },
    )

    st.plotly_chart(
        temperature_chart,
        use_container_width=True,
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Humidity Forecast")

        humidity_chart = px.line(
            forecast,
            x="measurement_time",
            y="relative_humidity_percent",
            labels={
                "measurement_time": "Forecast time",
                "relative_humidity_percent": "Humidity (%)",
            },
        )

        st.plotly_chart(
            humidity_chart,
            use_container_width=True,
        )

    with right:
        st.subheader("Hourly Rainfall Forecast")

        precipitation_chart = px.bar(
            forecast,
            x="measurement_time",
            y="precipitation_mm",
            labels={
                "measurement_time": "Forecast time",
                "precipitation_mm": "Rainfall (mm)",
            },
        )

        st.plotly_chart(
            precipitation_chart,
            use_container_width=True,
        )


# --------------------------------------------------
# Official daily forecast
# --------------------------------------------------

st.divider()
st.header("Official Daily Forecast")

if not daily_data.empty:
    daily = daily_data.iloc[0]

    daily_table = pd.DataFrame(
        {
            "Date": daily["dates"],
            "High (°C)": daily["temperature_high"],
            "Low (°C)": daily["temperature_low"],
            "Rainfall (mm)": daily["rainfall"],
            "Rain Probability (%)": daily["precipitation_probability"],
            "Conditions": [weather_description(code) for code in daily["weather_code"]],
        }
    )

    st.dataframe(
        daily_table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Daily high, low, rainfall, precipitation probability and "
        "weather conditions are supplied by Open-Meteo."
    )

else:
    st.info("Daily forecast data is not available.")


# --------------------------------------------------
# Data quality
# --------------------------------------------------

st.divider()

st.header("Data Quality & Pipeline Operations")

if not quality.empty:
    latest_quality = quality.iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Accepted Records",
        int(latest_quality["total_records_accepted"]),
    )

    col2.metric(
        "Latest Rejected Records",
        int(latest_quality["total_records_rejected"]),
    )

    col3.metric(
        "Average Quality",
        (
            f"{latest_quality['average_quality_percentage']:.2f}%"
            if pd.notna(latest_quality["average_quality_percentage"])
            else "N/A"
        ),
    )

    quality_chart = px.bar(
        quality.sort_values("run_date"),
        x="run_date",
        y=["successful_runs", "failed_runs"],
        barmode="group",
        labels={
            "run_date": "Date",
            "value": "Pipeline runs",
            "variable": "Status",
        },
    )

    st.subheader("Daily Pipeline Execution History")

    st.plotly_chart(
        quality_chart,
        use_container_width=True,
    )

else:
    st.info("No daily pipeline quality statistics available yet.")


# --------------------------------------------------
# Pipeline execution history
# --------------------------------------------------

st.subheader("Recent Pipeline Executions")

if not runs.empty:
    st.dataframe(
        runs,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No pipeline execution history available.")


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "EnviroTrack | Data source: Open-Meteo | "
    "Database: PostgreSQL | "
    "Forecast data, not historical weather observations."
)
