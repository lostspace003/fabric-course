# Data dictionary

All data is synthetic, made by `generator/generate.py` with seed 42 (kit 02 §4). No real people, companies or addresses.
Row counts and hashes: `manifest.json`. Pipelines read the files over HTTP from `manifest.json › files[].url`.

## Reference (`reference/`, Part 2 → `lh_reference`)

| File → table | Column | Type | Meaning |
|---|---|---|---|
| `carriers.csv` → `ref_carriers` | carrier_id | int | 1 Swiftline, 2 Parcelaro, 3 Northway Freight |
| | carrier_name | string | |
| | service_level | string | fast · standard · budget |
| `warehouses.csv` → `ref_warehouses` | warehouse_id | int | 1–4 |
| | warehouse_name, city | string | |
| | daily_capacity | int | orders per day the site handles comfortably |
| `regions.csv` → `ref_regions` | region_id | int | 1–12 |
| | region_name | string | |
| | remoteness | int | 0 urban · 1 suburban · 2 rural · 3 remote |
| | home_warehouse_id | int | the warehouse that normally ships to the region |
| | base_distance_km | double | typical distance from the home warehouse |
| `calendar_raw.csv` → `ref_calendar` (via `df_calendar`) | date | date | 2025-01-01 … 2026-12-31 |
| | holiday_name | string, nullable | |
| | promo_event | string, nullable | Spring Sale / Summer Deals weeks |
| | *added by Dataflow Gen2:* dow, is_weekend, is_holiday, is_peak | int | is_peak = 15 Nov–31 Dec or a promo week |
| `orders_sample.csv` → `sample_orders` | orders columns + is_late | | 5,000 labelled orders for demos 2.8 and 2.9 |

## History (`history/`, Part 3 → `Files/bronze/history/`)

| File | Column | Type | Meaning |
|---|---|---|---|
| `customers.csv` | customer_id | int | |
| | region_id | int | |
| | signup_date | date | |
| | segment | string | new · regular · vip |
| `orders.csv` | order_id | int | **about 0.5 % duplicated rows** – Lab 2 removes them |
| | customer_id | int | |
| | order_ts | timestamp (UTC, `…Z`) | checkout time |
| | region_id, warehouse_id, carrier_id | int | |
| | ship_method | string | standard · express |
| | items_count | int | 1–12 |
| | total_weight_kg | double | |
| | order_value | double | |
| | promised_date | date | the date shown at checkout |
| | channel | string | web · app |
| `shipments.csv` | order_id | int | one row per order |
| | shipped_ts, delivered_ts | timestamp | **label only** – never a feature |
| | carrier_id | int | |
| `daily_ops.csv` | date, warehouse_id | | |
| | backlog_index | double | 0.3–1.6; the feature uses the **previous day's** value |
| | staffing_level | string | normal · reduced · boosted |
| `weather_daily.csv` | date, region_id | | |
| | forecast_severity | int | 0–3, issued the day before → allowed feature |
| | actual_severity | int | 0–3 → **label only** |

## Operational (`ops/sqldb_ops_setup.sql`, demo 2.5 → `sqldb_brightcart_ops`)

| Table | Columns | Meaning |
|---|---|---|
| `dbo.open_orders` | orders columns + status (`in_transit`) | 1,500 orders from the three days before 2026-10-01; Lab 6 copies them nightly |
| `dbo.risk_alerts` | alert_id (identity), order_id, late_risk, order_value, created_at | written by `pl_log_alert` (Lab 5 fallback) |

## Label and features
- `is_late` = delivered date > promised_date (about 20 % of orders).
- Features = the 16 columns of `kit/contracts/feature_contract.json`, in that order. `distance_km` is derived in nb_02 from the
  region's base distance (deterministic jitter by order_id); `backlog_index` is the previous day's value for the order's
  warehouse; `forecast_severity` is the forecast for the order date.
- Holdout = order_ts ≥ 2026-07-01. On it LightGBM (v1 profile) reaches ROC-AUC ≈ 0.84 and the logistic baseline ≈ 0.80
  (`generator/tests/test_targets.py` asserts 0.80–0.87 and a gap ≥ 0.03).
- Leakage rule (kit §4.5): nothing recorded after `order_ts` is a feature.
