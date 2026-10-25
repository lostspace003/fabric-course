"""The feature logic of nb_02_features, in pandas, so the generator tests prove the targets with the same features.
Leakage rule (kit 02 §4.5): only order attributes, the previous day's backlog_index for the same warehouse, and
forecast_severity. shipments / actual_severity are used for the LABEL only."""
from pathlib import Path
import numpy as np, pandas as pd

FEATURES = ["carrier_id", "ship_method_express", "warehouse_id", "region_id", "remoteness", "distance_km", "order_hour",
            "order_dow", "is_weekend", "is_peak", "items_count", "total_weight_kg", "order_value", "promised_days",
            "backlog_index", "forecast_severity"]
INT_COLS = [c for c in FEATURES if c not in ("distance_km", "total_weight_kg", "order_value", "backlog_index")]


def enrich_calendar(cal: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(cal["date"]); md = d.dt.strftime("%m-%d")
    cal = cal.copy()
    cal["dow"] = d.dt.day_of_week
    cal["is_weekend"] = (cal.dow >= 5).astype(int)
    cal["is_holiday"] = cal.holiday_name.notna().astype(int)
    cal["is_peak"] = (((md >= "11-15") & (md <= "12-31")) | cal.promo_event.notna()).astype(int)
    return cal


def build_features(orders, regions, calendar, daily_ops, weather, rng_seed=42) -> pd.DataFrame:
    o = orders.drop_duplicates("order_id").copy()
    ts = pd.to_datetime(o.order_ts, utc=True)
    o["date"] = ts.dt.strftime("%Y-%m-%d")
    o["order_hour"] = ts.dt.hour
    o["order_dow"] = ts.dt.day_of_week
    o["ship_method_express"] = (o.ship_method == "express").astype(int)
    o["promised_days"] = (pd.to_datetime(o.promised_date) - ts.dt.tz_localize(None).dt.normalize()).dt.days
    o = o.merge(regions[["region_id", "remoteness", "base_distance_km"]], on="region_id", how="left")
    # distance_km is not in the raw orders: nb_02 derives it from the region's base distance (deterministic jitter by order_id)
    jitter = 0.8 + 0.4 * ((o.order_id.astype("int64") * 2654435761) % 1000) / 1000
    o["distance_km"] = (o.base_distance_km * jitter).round(1)
    o = o.merge(calendar[["date", "is_weekend", "is_peak"]], on="date", how="left")
    prev = (pd.to_datetime(o.date) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    ops = daily_ops.rename(columns={"date": "prev_date"})[["prev_date", "warehouse_id", "backlog_index"]]
    o["prev_date"] = prev
    o = o.merge(ops, on=["prev_date", "warehouse_id"], how="left")
    o["backlog_index"] = o.backlog_index.fillna(0.8)
    o = o.merge(weather[["date", "region_id", "forecast_severity"]], on=["date", "region_id"], how="left")
    o["forecast_severity"] = o.forecast_severity.fillna(0).astype(int)
    for c in INT_COLS: o[c] = o[c].astype("int64")
    for c in ("distance_km", "total_weight_kg", "order_value", "backlog_index"): o[c] = o[c].astype("float64")
    return o


def build_training_frame(data: Path) -> pd.DataFrame:
    h, r = data / "history", data / "reference"
    o = build_features(pd.read_csv(h / "orders.csv"), pd.read_csv(r / "regions.csv"),
                       enrich_calendar(pd.read_csv(r / "calendar_raw.csv")), pd.read_csv(h / "daily_ops.csv"),
                       pd.read_csv(h / "weather_daily.csv"))
    s = pd.read_csv(h / "shipments.csv")
    o = o.merge(s[["order_id", "delivered_ts"]], on="order_id")
    delivered_day = pd.to_datetime(o.delivered_ts, utc=True).dt.tz_localize(None).dt.normalize()
    o["is_late"] = (delivered_day > pd.to_datetime(o.promised_date)).astype(int)
    o["split"] = np.where(pd.to_datetime(o.order_ts, utc=True) < pd.Timestamp("2026-07-01", tz="UTC"), "train", "holdout")
    return o
