# NOAA Data Pipeline

Downloads marine environmental data from NOAA buoys and coastal stations for the New York region and stores it locally as Parquet files.

---

## What it collects

**NDBC offshore buoys** — wave height, wave period, wave direction, wind speed/direction/gust, air pressure, air temperature, water temperature, dewpoint  
**CO-OPS coastal stations** — water level, water temperature, wind, air pressure, air temperature, humidity, visibility, currents

See [`config/stations.json`](config/stations.json) for the full station list.

---

## Setup

```powershell
pip install -r noaa_data_pipeline/requirements.txt
```

Requirements: `requests`, `pandas`, `pyarrow`

---

## Usage

Run from the repository root:

```powershell
# Recommended starting point — last 30 years of CO-OPS + NDBC
python noaa_data_pipeline/src/pipeline.py --start 1996-01-01

# Single month test (fast, verifies everything works)
python noaa_data_pipeline/src/pipeline.py --start 2024-01-01 --end 2024-01-31 --only coops

# One source type only
python noaa_data_pipeline/src/pipeline.py --start 1996-01-01 --only ndbc

# Full available history per station (slow — see note below)
python noaa_data_pipeline/src/pipeline.py --all-history
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--start YYYY-MM-DD` | required* | Start of date range |
| `--end YYYY-MM-DD` | today | End of date range |
| `--all-history` | off | Auto-detect earliest date per station. Overrides `--start` |
| `--only coops\|ndbc` | both | Restrict to one source |
| `--station-config PATH` | `config/stations.json` | Custom station list |
| `--log-level` | INFO | DEBUG / INFO / WARNING / ERROR |

*Not required when `--all-history` is set.

### Runtime estimate

| Command | Approximate time |
|---|---|
| `--start 1996-01-01` | ~90 minutes |
| `--all-history` | ~3.5 hours (includes many empty years) |
| Single month test | ~30 seconds |

Re-runs are fast — months that already have a Parquet file on disk are skipped immediately.

---

## Output layout

```
noaa_data_pipeline/data/
    source=coops/
        station=8518750/
            product=water_level/
                year=2024/
                    month=01.parquet
    source=ndbc/
        station=44025/
            year=2024/
                data.parquet
```

Each Parquet file contains:

**CO-OPS** — `timestamp`, `station_id`, `product`, `value`, `quality_flag` (where available)  
**NDBC** — `timestamp`, `station_id`, plus one column per variable (wave_height_m, wind_speed_ms, etc.)

---

## Adding stations

Edit [`config/stations.json`](config/stations.json). No code changes needed.

```json
{
  "region": "new_york",
  "ndbc": ["44025", "44065", "44017"],
  "coops": [
    {
      "id": "8516945",
      "name": "Kings Point, NY",
      "products": ["water_level", "water_temperature", "wind", "air_pressure", "air_temperature"]
    }
  ]
}
```

Available CO-OPS products: `water_level`, `water_temperature`, `wind`, `air_pressure`, `air_temperature`, `humidity`, `visibility`, `currents`

---

## Data sources

- **CO-OPS API**: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- **NDBC archive**: https://www.ndbc.noaa.gov/data/historical/stdmet/
- **CO-OPS metadata**: https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{id}.json
