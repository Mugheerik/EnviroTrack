import math
from datetime import datetime
from zoneinfo import ZoneInfo

VARIABLES = {
    "temperature_2m": (-90, 65),
    "relative_humidity_2m": (0, 100),
    "precipitation": (0, None),
    "wind_speed_10m": (0, 400),
}


def validate_hourly_payload(
    payload: dict,
) -> tuple[list[dict], list[str]]:

    if not isinstance(payload, dict):
        raise TypeError("Payload must be a dictionary")

    hourly = payload.get("hourly")

    if not isinstance(hourly, dict):
        raise TypeError("Hourly data must be a dictionary")

    times = hourly.get("time")

    if not isinstance(times, list) or not times:
        raise ValueError("Missing or empty hourly timestamps")

    for variable in VARIABLES:
        values = hourly.get(variable)

        if not isinstance(values, list):
            raise TypeError(f"Measurement array must be a list: {variable}")

        if len(values) != len(times):
            raise ValueError(
                f"Array length mismatch for {variable}: "
                f"{len(values)} values for {len(times)} timestamps"
            )

    timezone_name = payload.get("timezone", "UTC")

    try:
        local_timezone = ZoneInfo(timezone_name)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid source timezone: {timezone_name}") from error

    valid_records = []
    issues = []

    for index, time_string in enumerate(times):
        try:
            if not isinstance(time_string, str):
                raise TypeError("Timestamp must be a string")

            measurement_time = datetime.fromisoformat(time_string)

            if measurement_time.tzinfo is None:
                measurement_time = measurement_time.replace(tzinfo=local_timezone)

        except (ValueError, TypeError) as error:
            issues.append(f"Row {index}: invalid timestamp: {error}")
            continue

        measurements = {}
        row_valid = True

        for variable, (minimum, maximum) in VARIABLES.items():
            value = hourly[variable][index]

            # Null is allowed: it represents a missing measurement.
            if value is None:
                measurements[variable] = None
                continue

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                issues.append(f"Row {index}: {variable} is not numeric")
                row_valid = False
                break

            numeric_value = float(value)

            if not math.isfinite(numeric_value):
                issues.append(f"Row {index}: {variable} is not finite")
                row_valid = False
                break

            if numeric_value < minimum:
                issues.append(f"Row {index}: {variable} below minimum {minimum}")
                row_valid = False
                break

            if maximum is not None and numeric_value > maximum:
                issues.append(f"Row {index}: {variable} above maximum {maximum}")
                row_valid = False
                break

            measurements[variable] = numeric_value

        if row_valid:
            valid_records.append(
                {
                    "measurement_time": measurement_time,
                    **measurements,
                }
            )

    return valid_records, issues
