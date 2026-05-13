# Frontend Context

This folder will host a simple Gradio UI intended for Hugging Face Spaces. The UI will collect user inputs needed to run inference using the model at ../model/stacking_classifier.joblib to predict whether a user will catch fish based on weather conditions and planned fishing details.

## Components Overview (planned)
- Inference UI: Gradio interface with input widgets for weather conditions and fishing plan details (exact fields TBD). Collects user inputs and triggers prediction.
- Prediction Handler: Loads the model, performs feature preprocessing (if required), runs inference, and returns a clear result message.
- Validation/Defaults: Ensures required inputs are provided and supplies safe defaults where appropriate.
- Outputs: A human-readable prediction result and, if needed, a probability score.
- UI Behavior: Default view shows only user-supplied inputs plus a compact auto-filled value display; a toggle button switches to an advanced mode where all fields are editable; the auto-fill status message warns when NYC forecast values are not yet filled.
- UI Labels: User-facing input labels expand FFDAYS2, HRSF, MODE_F, and CNTRBTRS into descriptive prompts.
- Fixed Inputs: year is hidden from the UI and forced to 2024 to match the dataset coverage.

## Constraints
- Target deployment: Hugging Face Spaces.
- UI framework: Gradio.
- Model file: ../model/stacking_classifier.joblib.

## Input Schema (model features)
Derived from data/processed/df_tripdata_engineered_with_total.csv (features exclude has_catch and total_catch). Defaults use the median for numeric fields and the mode for boolean fields.

```yaml
- name: FFDAYS2
	type: float
	min: 0.0
	max: 60.0
	default: 3.0
- name: HRSF
	type: float
	min: 0.5
	max: 24.0
	default: 3.5
- name: MODE_F
	type: float
	min: 1.0
	max: 8.0
	default: 7.0
- name: CNTRBTRS
	type: float
	min: 0.0
	max: 20.0
	default: 1.0
- name: IMP_REC
	type: float
	min: 0.0
	max: 1.0
	default: 0.0
- name: avg_wind_speed
	type: float
	min: 0.0
	max: 17.81111111111111
	default: 4.491666666666667
- name: avg_wind_gust
	type: float
	min: 0.0
	max: 22.48888888888889
	default: 5.555902777777778
- name: wind_speed_rose
	type: int
	min: 0
	max: 1
	default: 1
- name: wind_speed_fell
	type: int
	min: 0
	max: 1
	default: 1
- name: avg_air_pressure
	type: float
	min: 0.0
	max: 1048.16
	default: 1017.15
- name: air_pressure_rose
	type: int
	min: 0
	max: 1
	default: 1
- name: air_pressure_fell
	type: int
	min: 0
	max: 1
	default: 0
- name: avg_air_temp_c
	type: float
	min: -12.22
	max: 30.55
	default: 17.7
- name: air_temp_rose
	type: int
	min: 0
	max: 1
	default: 1
- name: air_temp_fell
	type: int
	min: 0
	max: 1
	default: 0
- name: avg_water_temp_c
	type: float
	min: 0.0
	max: 27.45
	default: 19.2
- name: water_temp_rose
	type: int
	min: 0
	max: 1
	default: 1
- name: water_temp_fell
	type: int
	min: 0
	max: 1
	default: 0
- name: avg_water_level
	type: float
	min: -0.6160000000000001
	max: 3.315
	default: 1.1931666666666665
- name: water_level_rose
	type: int
	min: 0
	max: 1
	default: 1
- name: water_level_fell
	type: int
	min: 0
	max: 1
	default: 1
- name: was_sunrise
	type: int
	min: 0
	max: 1
	default: 0
- name: was_sunset
	type: int
	min: 0
	max: 1
	default: 0
- name: was_moonrise
	type: int
	min: 0
	max: 1
	default: 0
- name: was_moonset
	type: int
	min: 0
	max: 1
	default: 0
- name: moon_phase_age
	type: float
	min: 0.033444444444445
	max: 27.95566666666667
	default: 14.189
- name: sun_distance
	type: float
	min: 147094392.09735674
	max: 152104280.0821802
	default: 151337958.76909158
- name: moon_distance
	type: float
	min: 351656.150469608
	max: 412119.14743852353
	default: 385300.1842715448
- name: year
	type: int
	min: 2014
	max: 2024
	default: 2019
- name: month
	type: int
	min: 1
	max: 12
	default: 8
- name: day
	type: int
	min: 1
	max: 31
	default: 16
- name: hour
	type: int
	min: 0
	max: 23
	default: 14
- name: dayofweek
	type: int
	min: 0
	max: 6
	default: 5
- name: is_weekend
	type: int
	min: 0
	max: 1
	default: 1
- name: hour_sin
	type: float
	min: -1.0
	max: 1.0
	default: -0.4999999999999997
- name: hour_cos
	type: float
	min: -1.0
	max: 1.0
	default: -0.7071067811865479
- name: month_sin
	type: float
	min: -1.0
	max: 1.0
	default: -0.4999999999999997
- name: month_cos
	type: float
	min: -1.0
	max: 1.0
	default: -0.5000000000000004
- name: dayofweek_sin
	type: float
	min: -0.9749279121818236
	max: 0.9749279121818236
	default: -0.7818314824680299
- name: dayofweek_cos
	type: float
	min: -0.9009688679024191
	max: 1.0
	default: -0.2225209339563146
- name: total_effort_hours
	type: float
	min: 0.0
	max: 144.0
	default: 3.0
- name: moon_illumination
	type: float
	min: 1.2659571066461726e-05
	max: 0.9999887300268552
	default: 0.5439929509656181
- name: major_minor_feeding
	type: int
	min: 0
	max: 4
	default: 0
- name: storm_approaching
	type: int
	min: 0
	max: 1
	default: 0
- name: cold_front
	type: int
	min: 0
	max: 1
	default: 0
- name: temp_diff
	type: float
	min: -26.0
	max: 23.975
	default: -0.6666666666666643
- name: temp_shock_magnitude
	type: float
	min: 0.0
	max: 26.0
	default: 1.1999999999999993
- name: water_is_moving
	type: int
	min: 0
	max: 1
	default: 1
- name: wind_x_pressure
	type: float
	min: 0.0
	max: 17886.907283950615
	default: 4563.791428571429
- name: gust_ratio
	type: float
	min: 0.0
	max: 100000.0
	default: 1.2343094684967193
- name: KOD_we
	type: bool
	min: 0
	max: 1
	default: true
```

## NYC Auto-Fill Plan (T07)
This plan defines which inputs are user-supplied vs auto-filled from NYC forecast data. Use it as the implementation note for tasks T08 to T10.

### User-Supplied Inputs
- FFDAYS2 (days fished)
- HRSF (hours per fishing trip)
- MODE_F (fishing mode)
- CNTRBTRS (number of contributors)

### Auto-Filled Inputs
- All remaining model features except IMP_REC
- IMP_REC is removed from the form and forced to 0 in the feature generator

### Form Exclusions
- Remove IMP_REC from the UI entirely
- Do not auto-fill or lock FFDAYS2, HRSF, MODE_F, CNTRBTRS (these remain user inputs)
