import logging
import time

import requests

from envirotrack.config import TIMEZONE

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"

MAX_ATTEMPTS = 5
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def fetch_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "rain,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "hourly": ("temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"),
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "rain_sum,"
            "precipitation_sum,"
            "precipitation_probability_max,"
            "weather_code"
        ),
        "timezone": TIMEZONE,
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logger.info(
                "Requesting weather data (attempt %s/%s)",
                attempt,
                MAX_ATTEMPTS,
            )

            response = requests.get(
                BASE_URL,
                params=params,
                timeout=(5, 30),
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == MAX_ATTEMPTS:
                    response.raise_for_status()

                retry_delay = min(2 ** (attempt - 1), 16)

                logger.warning(
                    "API returned HTTP %s. Retrying in %s seconds",
                    response.status_code,
                    retry_delay,
                )

                time.sleep(retry_delay)
                continue

            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, dict):
                raise TypeError("API response must be a JSON object")

            if "hourly" not in payload:
                raise ValueError("API response does not contain hourly data")

            if "daily" not in payload:
                raise ValueError("API response does not contain daily data")

            if "current" not in payload:
                raise ValueError("API response does not contain current data")

            logger.info("Weather API request successful")

            return payload

        except (requests.Timeout, requests.ConnectionError) as error:
            if attempt == MAX_ATTEMPTS:
                logger.exception("Weather API request failed after all retries")
                raise

            retry_delay = min(2 ** (attempt - 1), 16)

            logger.warning(
                "Network error: %s. Retrying in %s seconds",
                error,
                retry_delay,
            )

            time.sleep(retry_delay)

    raise RuntimeError("Weather API request failed")
