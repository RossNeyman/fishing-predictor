from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

from schema import SCHEMA, SCHEMA_INDEX, build_default_input, validate_input


@dataclass(frozen=True)
class TrendFlags:
    rose: int
    fell: int
    delta: float


def _extract_hours(forecast: dict[str, Any], hours_ahead: float) -> list[dict[str, Any]]:
    hours = forecast.get("hours")
    if not isinstance(hours, list):
        raise ValueError("Forecast missing hours list")
    if hours_ahead <= 0:
        raise ValueError("hours_ahead must be positive")

    count = int(math.ceil(hours_ahead))
    if len(hours) < count:
        raise ValueError("Forecast does not include enough hours")
    return hours[:count]


def _mean_or_default(values: list[float], default: float) -> float:
    if not values:
        return default
    return float(sum(values)) / float(len(values))


def _series_values(hours: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for hour in hours:
        value = hour.get(key)
        if value is None:
            continue
        values.append(float(value))
    return values


def _trend(values: list[float], default_rose: int, default_fell: int) -> TrendFlags:
    if len(values) < 2:
        return TrendFlags(default_rose, default_fell, 0.0)
    delta = float(values[-1] - values[0])
    if delta > 0:
        return TrendFlags(1, 0, delta)
    if delta < 0:
        return TrendFlags(0, 1, delta)
    return TrendFlags(0, 0, 0.0)


def _clamp_to_schema(data: dict[str, Any]) -> dict[str, Any]:
    for field in SCHEMA:
        value = data.get(field.name)
        if field.field_type == "bool":
            data[field.name] = bool(value)
            continue
        if field.field_type == "int":
            numeric_value = int(round(float(value)))
        else:
            numeric_value = float(value)
        if numeric_value < field.min_value:
            numeric_value = field.min_value
        if numeric_value > field.max_value:
            numeric_value = field.max_value
        data[field.name] = int(numeric_value) if field.field_type == "int" else float(numeric_value)
    return data


def _apply_datetime_fields(data: dict[str, Any], timestamp: str | None) -> None:
    if not timestamp:
        return
    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return

    data["year"] = dt.year
    data["month"] = dt.month
    data["day"] = dt.day
    data["hour"] = dt.hour
    data["dayofweek"] = dt.weekday()
    data["is_weekend"] = 1 if dt.weekday() >= 5 else 0

    hour_angle = 2.0 * math.pi * (dt.hour / 24.0)
    data["hour_sin"] = math.sin(hour_angle)
    data["hour_cos"] = math.cos(hour_angle)

    month_angle = 2.0 * math.pi * ((dt.month - 1) / 12.0)
    data["month_sin"] = math.sin(month_angle)
    data["month_cos"] = math.cos(month_angle)

    dow_angle = 2.0 * math.pi * (dt.weekday() / 7.0)
    data["dayofweek_sin"] = math.sin(dow_angle)
    data["dayofweek_cos"] = math.cos(dow_angle)


def generate_features(forecast: dict[str, Any], user_inputs: dict[str, Any]) -> dict[str, Any]:
    data = build_default_input()
    data.update(user_inputs)

    hours_ahead = float(data.get("HRSF", 0.0))
    hours = _extract_hours(forecast, hours_ahead)

    wind_speed = _series_values(hours, "wind_speed")
    wind_gust = _series_values(hours, "wind_gust")
    air_pressure = _series_values(hours, "air_pressure")
    air_temp = _series_values(hours, "air_temp_c")
    water_temp = _series_values(hours, "water_temp_c")
    water_level = _series_values(hours, "water_level")

    data["avg_wind_speed"] = _mean_or_default(wind_speed, SCHEMA_INDEX["avg_wind_speed"].default)
    data["avg_wind_gust"] = _mean_or_default(wind_gust, SCHEMA_INDEX["avg_wind_gust"].default)
    data["avg_air_pressure"] = _mean_or_default(air_pressure, SCHEMA_INDEX["avg_air_pressure"].default)
    data["avg_air_temp_c"] = _mean_or_default(air_temp, SCHEMA_INDEX["avg_air_temp_c"].default)
    data["avg_water_temp_c"] = _mean_or_default(water_temp, SCHEMA_INDEX["avg_water_temp_c"].default)
    data["avg_water_level"] = _mean_or_default(water_level, SCHEMA_INDEX["avg_water_level"].default)

    wind_trend = _trend(
        wind_speed,
        SCHEMA_INDEX["wind_speed_rose"].default,
        SCHEMA_INDEX["wind_speed_fell"].default,
    )
    data["wind_speed_rose"] = wind_trend.rose
    data["wind_speed_fell"] = wind_trend.fell

    pressure_trend = _trend(
        air_pressure,
        SCHEMA_INDEX["air_pressure_rose"].default,
        SCHEMA_INDEX["air_pressure_fell"].default,
    )
    data["air_pressure_rose"] = pressure_trend.rose
    data["air_pressure_fell"] = pressure_trend.fell

    air_temp_trend = _trend(
        air_temp,
        SCHEMA_INDEX["air_temp_rose"].default,
        SCHEMA_INDEX["air_temp_fell"].default,
    )
    data["air_temp_rose"] = air_temp_trend.rose
    data["air_temp_fell"] = air_temp_trend.fell

    water_temp_trend = _trend(
        water_temp,
        SCHEMA_INDEX["water_temp_rose"].default,
        SCHEMA_INDEX["water_temp_fell"].default,
    )
    data["water_temp_rose"] = water_temp_trend.rose
    data["water_temp_fell"] = water_temp_trend.fell

    water_level_trend = _trend(
        water_level,
        SCHEMA_INDEX["water_level_rose"].default,
        SCHEMA_INDEX["water_level_fell"].default,
    )
    data["water_level_rose"] = water_level_trend.rose
    data["water_level_fell"] = water_level_trend.fell

    data["storm_approaching"] = 1 if pressure_trend.delta <= -2.0 else 0
    data["cold_front"] = 1 if air_temp_trend.delta <= -3.0 else 0

    data["temp_diff"] = data["avg_air_temp_c"] - data["avg_water_temp_c"]
    data["temp_shock_magnitude"] = abs(data["temp_diff"])

    water_level_delta = water_level_trend.delta
    data["water_is_moving"] = 1 if abs(water_level_delta) > 0.01 else 0

    data["wind_x_pressure"] = data["avg_wind_speed"] * data["avg_air_pressure"]
    data["gust_ratio"] = data["avg_wind_gust"] / data["avg_wind_speed"] if data["avg_wind_speed"] > 0 else 0.0

    data["total_effort_hours"] = float(data.get("FFDAYS2", 0.0)) * float(data.get("HRSF", 0.0))

    data["IMP_REC"] = 0.0

    _apply_datetime_fields(data, hours[0].get("time") if hours else None)

    _clamp_to_schema(data)
    validate_input(data)
    return data
