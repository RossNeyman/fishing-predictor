from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldSpec:
    name: str
    field_type: str
    min_value: float
    max_value: float
    default: Any


SCHEMA = [
    FieldSpec("FFDAYS2", "float", 0.0, 60.0, 3.0),
    FieldSpec("HRSF", "float", 0.5, 24.0, 3.5),
    FieldSpec("MODE_F", "float", 1.0, 8.0, 7.0),
    FieldSpec("CNTRBTRS", "float", 0.0, 20.0, 1.0),
    FieldSpec("IMP_REC", "float", 0.0, 1.0, 0.0),
    FieldSpec("avg_wind_speed", "float", 0.0, 17.81111111111111, 4.491666666666667),
    FieldSpec("avg_wind_gust", "float", 0.0, 22.48888888888889, 5.555902777777778),
    FieldSpec("wind_speed_rose", "int", 0.0, 1.0, 1),
    FieldSpec("wind_speed_fell", "int", 0.0, 1.0, 1),
    FieldSpec("avg_air_pressure", "float", 0.0, 1048.16, 1017.15),
    FieldSpec("air_pressure_rose", "int", 0.0, 1.0, 1),
    FieldSpec("air_pressure_fell", "int", 0.0, 1.0, 0),
    FieldSpec("avg_air_temp_c", "float", -12.22, 30.55, 17.7),
    FieldSpec("air_temp_rose", "int", 0.0, 1.0, 1),
    FieldSpec("air_temp_fell", "int", 0.0, 1.0, 0),
    FieldSpec("avg_water_temp_c", "float", 0.0, 27.45, 19.2),
    FieldSpec("water_temp_rose", "int", 0.0, 1.0, 1),
    FieldSpec("water_temp_fell", "int", 0.0, 1.0, 0),
    FieldSpec("avg_water_level", "float", -0.6160000000000001, 3.315, 1.1931666666666665),
    FieldSpec("water_level_rose", "int", 0.0, 1.0, 1),
    FieldSpec("water_level_fell", "int", 0.0, 1.0, 1),
    FieldSpec("was_sunrise", "int", 0.0, 1.0, 0),
    FieldSpec("was_sunset", "int", 0.0, 1.0, 0),
    FieldSpec("was_moonrise", "int", 0.0, 1.0, 0),
    FieldSpec("was_moonset", "int", 0.0, 1.0, 0),
    FieldSpec("moon_phase_age", "float", 0.033444444444445, 27.95566666666667, 14.189),
    FieldSpec(
        "sun_distance", "float", 147094392.09735674, 152104280.0821802, 151337958.76909158
    ),
    FieldSpec("moon_distance", "float", 351656.150469608, 412119.14743852353, 385300.1842715448),
    FieldSpec("year", "int", 2014.0, 2024.0, 2019),
    FieldSpec("month", "int", 1.0, 12.0, 8),
    FieldSpec("day", "int", 1.0, 31.0, 16),
    FieldSpec("hour", "int", 0.0, 23.0, 14),
    FieldSpec("dayofweek", "int", 0.0, 6.0, 5),
    FieldSpec("is_weekend", "int", 0.0, 1.0, 1),
    FieldSpec("hour_sin", "float", -1.0, 1.0, -0.4999999999999997),
    FieldSpec("hour_cos", "float", -1.0, 1.0, -0.7071067811865479),
    FieldSpec("month_sin", "float", -1.0, 1.0, -0.4999999999999997),
    FieldSpec("month_cos", "float", -1.0, 1.0, -0.5000000000000004),
    FieldSpec("dayofweek_sin", "float", -0.9749279121818236, 0.9749279121818236, -0.7818314824680299),
    FieldSpec("dayofweek_cos", "float", -0.9009688679024191, 1.0, -0.2225209339563146),
    FieldSpec("total_effort_hours", "float", 0.0, 144.0, 3.0),
    FieldSpec("moon_illumination", "float", 1.2659571066461726e-05, 0.9999887300268552, 0.5439929509656181),
    FieldSpec("major_minor_feeding", "int", 0.0, 4.0, 0),
    FieldSpec("storm_approaching", "int", 0.0, 1.0, 0),
    FieldSpec("cold_front", "int", 0.0, 1.0, 0),
    FieldSpec("temp_diff", "float", -26.0, 23.975, -0.6666666666666643),
    FieldSpec("temp_shock_magnitude", "float", 0.0, 26.0, 1.1999999999999993),
    FieldSpec("water_is_moving", "int", 0.0, 1.0, 1),
    FieldSpec("wind_x_pressure", "float", 0.0, 17886.907283950615, 4563.791428571429),
    FieldSpec("gust_ratio", "float", 0.0, 100000.0, 1.2343094684967193),
    FieldSpec("KOD_we", "bool", 0.0, 1.0, True),
]

SCHEMA_INDEX = {field.name: field for field in SCHEMA}


def build_default_input() -> dict[str, Any]:
    return {field.name: field.default for field in SCHEMA}


def validate_input(data: dict[str, Any]) -> None:
    errors: list[str] = []

    for field in SCHEMA:
        if field.name not in data:
            errors.append(f"Missing field: {field.name}")
            continue

        value = data[field.name]
        if field.field_type == "bool":
            if not isinstance(value, bool):
                errors.append(f"Field {field.name} must be bool")
                continue
            numeric_value = 1.0 if value else 0.0
        elif field.field_type == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"Field {field.name} must be int")
                continue
            numeric_value = float(value)
        else:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"Field {field.name} must be float")
                continue
            numeric_value = float(value)

        if numeric_value < field.min_value or numeric_value > field.max_value:
            errors.append(
                f"Field {field.name} out of range [{field.min_value}, {field.max_value}]: {numeric_value}"
            )

    if errors:
        raise ValueError("; ".join(errors))
