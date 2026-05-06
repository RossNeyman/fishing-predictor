# NOAA Data Pipeline — Technical Context

This document is intended for developers or AI agents continuing work on this component. It captures design decisions, architecture details, known issues, and next steps.

---

## Purpose

This pipeline is the **data collection layer** of a fishing prediction project. It retrieves multi-decade marine environmental data for the New York region (NY Harbor, Long Island Sound, NY Bight) from two NOAA sources, stores it locally as Parquet, and will later be joined with NOAA fisheries survey catch data to train a predictive model.

---

## File structure

```
noaa_data_pipeline/
    config/
        stations.json          # Curated NY station list — edit this to add stations
    data/                      # Downloaded Parquet files (git-ignored)
    requirements.txt
    src/
        stations.py            # Config loader + validation
        utils.py               # Shared: month chunking, retry, path helpers, logging
        coops_downloader.py    # CO-OPS datagetter API client
        ndbc_downloader.py     # NDBC stdmet archive client
        pipeline.py            # Orchestrator + CLI entry point
```

---

## Architecture decisions

### Manual station list (not auto-discovery)
Stations are defined in `config/stations.json` rather than discovered via geographic radius search. This avoids building a full station discovery pipeline and allows rapid progress toward modeling. The architecture does not prevent adding auto-discovery later.

### Monthly chunking
Data is requested one month at a time to avoid NOAA API timeouts and large response payloads. Each month = one Parquet file for CO-OPS, one year = one Parquet file for NDBC.

### Skip-if-exists
Before any HTTP request, the downloader checks whether the output file already exists. This makes re-runs and resume-after-crash free.

### Rate limiting
A 0.5 s sleep is inserted after every successful CO-OPS request, and a 2 s sleep after any failure. This prevents NOAA from dropping connections under sustained load (observed in production with bare back-to-back requests).

### Retry logic
`utils.get_with_retry()` catches all exceptions (including raw `ssl.SSLError` and `OSError`, not just `requests.RequestException`) and retries up to 3 times with exponential backoff (1 s, 2 s, 4 s).

### CO-OPS API error detection
The CO-OPS datagetter returns HTTP 200 even for invalid requests, putting the error inside the JSON body as `{"error": {"message": "..."}}`. The parser explicitly checks for this and logs + skips rather than writing an empty or corrupt file.

---

## Data sources

### CO-OPS (Tides & Currents)
- **API**: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- **Resolution**: 6-minute intervals (7,440 rows/month when data exists)
- **Auth**: None required
- **Metadata API**: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{id}.json`
  - Returns station `established` date, available products, coordinates
  - Used by `--all-history` mode to determine per-station start date

### NDBC (National Data Buoy Center)
- **Archive**: `https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz`
- **Resolution**: Hourly
- **Format**: Fixed-width text, gzip-compressed, two header rows (column names + units)
- **Missing values**: Sentinel values 99, 999, 9999 (and decimal variants) → replaced with NaN

---

## Known issues and observations

### CO-OPS digital data starts ~1996
Even though some stations were established much earlier (e.g. Battery/8518750 since 1919), the 6-minute digital record only begins around 1996. Using `--all-history` wastes ~2 hours making API calls that return "No data was found". **Recommended start date: 1996-01-01.**

### Bergen Point currents (8519483) fails with HTTP 400
The standard datagetter API returns 400 for the `currents` product at this station. The currents endpoint requires a bin/channel parameter that varies by station and is not documented in the standard API. This is logged as a warning and skipped. Fix: query the MDAPI for the station's current meter configuration before requesting currents data.

### NDBC column format varies by era
Older NDBC files (pre-2000) use a 2-digit year column (`#YY`) and may omit the minute column (`mm`). The parser handles both formats via `_build_timestamp()`, but some very old files may have additional format quirks not yet encountered.

### `--all-history` is slow
The MDAPI `established` field does not always match when digital data actually starts. Consider caching known digital data start dates in `stations.json` as an optional `"digital_start"` field per station to avoid dead API calls.

---

## Parquet schema

### CO-OPS
| Column | Type | Notes |
|---|---|---|
| timestamp | datetime64[ns] | UTC, 6-minute intervals |
| station_id | str | e.g. "8518750" |
| product | str | e.g. "water_level" |
| value | float64 | Primary measurement in metric units |
| quality_flag | str | NOAA quality code where available |

### NDBC
| Column | Type | Notes |
|---|---|---|
| timestamp | datetime64[ns] | UTC, hourly |
| station_id | str | e.g. "44025" |
| wind_direction_deg | float64 | |
| wind_speed_ms | float64 | |
| wind_gust_ms | float64 | |
| wave_height_m | float64 | |
| dominant_wave_period_s | float64 | |
| avg_wave_period_s | float64 | |
| wave_direction_deg | float64 | |
| air_pressure_hpa | float64 | |
| air_temp_c | float64 | |
| water_temp_c | float64 | |
| dewpoint_c | float64 | |

---

## Loading the data

```python
import pandas as pd
import glob

# Load all water_level data for one station
files = glob.glob("noaa_data_pipeline/data/source=coops/station=8518750/product=water_level/**/*.parquet", recursive=True)
df = pd.concat([pd.read_parquet(f) for f in sorted(files)])

# Load all NDBC data for one buoy
files = glob.glob("noaa_data_pipeline/data/source=ndbc/station=44025/**/*.parquet", recursive=True)
df = pd.concat([pd.read_parquet(f) for f in sorted(files)])
```

---

## Next steps

1. **Join with fisheries data** — NOAA NEFSC trawl survey catch records, keyed by date and location, joined to the nearest environmental station readings at the time of each tow.
2. **Feature engineering** — rolling averages, lagged variables, seasonal decomposition.
3. **Fix currents at 8519483** — query MDAPI for bin configuration, use the currents_predictions or water_level+velocity endpoint.
4. **Add more stations** — candidate stations: Montauk (8510560), Bridgeport CT (8467150), Sandy Hook NJ (8531680).
5. **Data normalization layer** — standardize all timestamps to UTC, unify column names across CO-OPS and NDBC into a single wide table per observation.
