"""Brightcart synthetic data (kit 02 §4). Deterministic: seed 42 -> byte-identical CSVs.

    python generate.py            # writes ../reference, ../history, ../ops, ../manifest.json
    python generate.py --check    # also prints the §4.4 targets (late rate, carrier-3 remote, peak ratio)

Only what is known at checkout goes into the features (nb_02 enforces it). The label is drawn from the logit in
config.yaml; nothing is faked after the draw.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd, yaml

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
CFG = yaml.safe_load((HERE / "config.yaml").read_text())
BASE_URL = "https://raw.githubusercontent.com/lostspace003/fabric-course/main/data"

CARRIERS = pd.DataFrame({"carrier_id": [1, 2, 3], "carrier_name": ["Swiftline", "Parcelaro", "Northway Freight"],
                         "service_level": ["fast", "standard", "budget"]})
WAREHOUSES = pd.DataFrame({"warehouse_id": [1, 2, 3, 4],
                           "warehouse_name": ["Northgate Hub", "Riverside DC", "Eastfield Depot", "Southbay Hub"],
                           "city": ["Leeds", "Bristol", "Norwich", "Southampton"],
                           "daily_capacity": [1200, 900, 600, 800]})
REGIONS = pd.DataFrame({
    "region_id": range(1, 13),
    "region_name": ["Leeds City", "Manchester", "Bristol City", "Cardiff", "Norwich City", "Cambridge",
                    "Southampton City", "Brighton", "Peak District", "Welsh Valleys", "Norfolk Broads", "Isle of Wight"],
    "remoteness": [0, 0, 0, 1, 0, 1, 0, 1, 2, 2, 2, 3],
    "home_warehouse_id": [1, 1, 2, 2, 3, 3, 4, 4, 1, 2, 3, 4],
    "base_distance_km": [12, 65, 10, 70, 14, 95, 11, 90, 140, 160, 120, 210]})
HOLIDAYS = {"01-01": "New Year's Day", "12-25": "Christmas Day", "12-26": "Boxing Day", "05-05": "Early May bank holiday",
            "08-25": "Summer bank holiday"}
PROMOS = {("2025-03-10", "2025-03-16"): "Spring Sale", ("2025-07-07", "2025-07-13"): "Summer Deals",
          ("2026-03-09", "2026-03-15"): "Spring Sale", ("2026-07-06", "2026-07-12"): "Summer Deals"}


def calendar() -> pd.DataFrame:
    d = pd.date_range(CFG["dates"]["history_start"], CFG["dates"]["calendar_end"], freq="D")
    cal = pd.DataFrame({"date": d.strftime("%Y-%m-%d")})
    cal["holiday_name"] = [HOLIDAYS.get(x.strftime("%m-%d")) for x in d]
    promo = []
    for x in d:
        name = None
        for (a, b), n in PROMOS.items():
            if a <= x.strftime("%Y-%m-%d") <= b:
                name = n
        promo.append(name)
    cal["promo_event"] = promo
    return cal


def enriched_calendar(cal: pd.DataFrame) -> pd.DataFrame:
    """What df_calendar (Dataflow Gen2) adds. Used here for the label only; the lakehouse gets it from the dataflow."""
    d = pd.to_datetime(cal["date"])
    md = d.dt.strftime("%m-%d")
    out = cal.copy()
    out["dow"] = d.dt.day_of_week
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["is_holiday"] = cal["holiday_name"].notna().astype(int)
    out["is_peak"] = (((md >= CFG["peak"]["start_md"]) & (md <= CFG["peak"]["end_md"])) | cal["promo_event"].notna()).astype(int)
    return out


def main(check: bool) -> dict:
    rng = np.random.default_rng(CFG["seed"])
    L = CFG["logit"]; C = CFG["counts"]; D = CFG["dates"]
    cal = enriched_calendar(calendar()).set_index("date")

    # customers
    cust = pd.DataFrame({"customer_id": np.arange(1, C["customers"] + 1)})
    cust["region_id"] = rng.choice(REGIONS.region_id, C["customers"], p=np.array([11, 13, 10, 7, 9, 7, 10, 8, 6, 6, 7, 6]) / 100)
    cust["signup_date"] = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 900, C["customers"]), "D")
    cust["signup_date"] = cust["signup_date"].dt.strftime("%Y-%m-%d")
    cust["segment"] = rng.choice(["new", "regular", "vip"], C["customers"], p=[0.3, 0.6, 0.1])

    # daily volume weights (peak + promo +60%)
    days = pd.date_range(D["history_start"], D["history_end"], freq="D")
    dstr = days.strftime("%Y-%m-%d")
    w = np.ones(len(days)) * (1 + CFG["peak"]["volume_uplift"] * cal.loc[dstr, "is_peak"].values)
    w *= rng.uniform(0.85, 1.15, len(days))
    w /= w.sum()

    def make_orders(n: int, start_id: int, day_pool, day_w, with_dups: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
        di = rng.choice(len(day_pool), n, p=day_w)
        day = day_pool[di]
        hour = rng.choice(24, n, p=np.r_[np.full(7, 0.5), np.full(8, 1.6), np.full(6, 2.0), np.full(3, 0.8)] / (0.5 * 7 + 1.6 * 8 + 2 * 6 + 0.8 * 3))
        ts = pd.to_datetime(day) + pd.to_timedelta(hour, "h") + pd.to_timedelta(rng.integers(0, 3600, n), "s")
        cid = rng.integers(1, C["customers"] + 1, n)
        region = cust.region_id.values[cid - 1]
        reg = REGIONS.set_index("region_id").loc[region]
        remoteness = reg.remoteness.values
        warehouse = np.where(rng.random(n) < 0.85, reg.home_warehouse_id.values, rng.integers(1, 5, n))
        carrier = rng.choice([1, 2, 3], n, p=[0.3, 0.45, 0.25])
        express = (rng.random(n) < 0.22).astype(int)
        items = np.clip(rng.geometric(0.35, n), 1, 12)
        weight = np.round(items * rng.uniform(0.3, 2.5, n) + rng.uniform(0.1, 0.5, n), 2)
        value = np.round(items * rng.lognormal(3.3, 0.5, n) + 5, 2)
        promised_days = np.where(express == 1, rng.integers(1, 3, n), rng.integers(3, 6, n)) + (remoteness >= 2).astype(int)
        distance = np.round(reg.base_distance_km.values * rng.uniform(0.8, 1.2, n), 1)
        dstr_ = pd.Series(day).dt.strftime("%Y-%m-%d").values if not isinstance(day[0], str) else day
        o = pd.DataFrame({
            "order_id": np.arange(start_id, start_id + n), "customer_id": cid,
            "order_ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "region_id": region, "warehouse_id": warehouse,
            "carrier_id": carrier, "ship_method": np.where(express == 1, "express", "standard"),
            "items_count": items, "total_weight_kg": weight, "order_value": value,
            "promised_date": (pd.to_datetime(dstr_) + pd.to_timedelta(promised_days, "D")).strftime("%Y-%m-%d"),
            "channel": rng.choice(["web", "app"], n, p=[0.55, 0.45])})
        hidden = pd.DataFrame({"date": dstr_, "remoteness": remoteness, "distance_km": distance, "hour": hour,
                               "promised_days": promised_days, "express": express})
        return o, hidden

    orders, h = make_orders(C["orders"], 1, dstr, w, True)

    # daily ops (backlog rises with volume) and weather
    vol = pd.Series(h["date"]).value_counts().reindex(dstr, fill_value=0)
    ops_rows = []
    for wh in WAREHOUSES.warehouse_id:
        share = (orders.warehouse_id == wh).mean()
        cap = WAREHOUSES.set_index("warehouse_id").daily_capacity[wh]
        load = vol.values * share / (cap / 1.6)
        backlog = np.clip(0.55 + 0.9 * load + rng.normal(0, 0.12, len(dstr)), 0.3, 1.6)
        ops_rows.append(pd.DataFrame({"date": dstr, "warehouse_id": wh, "backlog_index": np.round(backlog, 3),
                                      "staffing_level": rng.choice(["normal", "reduced", "boosted"], len(dstr), p=[0.75, 0.15, 0.10])}))
    daily_ops = pd.concat(ops_rows, ignore_index=True)
    wx_rows = []
    month = pd.to_datetime(dstr).month
    for r in REGIONS.itertuples():
        p_bad = 0.08 + 0.05 * r.remoteness + 0.08 * np.isin(month, [11, 12, 1, 2])
        actual = np.where(rng.random(len(dstr)) < p_bad, rng.choice([1, 2, 3], len(dstr), p=[0.55, 0.3, 0.15]), 0)
        forecast = np.clip(actual + rng.choice([-1, 0, 0, 0, 1], len(dstr)), 0, 3)
        wx_rows.append(pd.DataFrame({"date": dstr, "region_id": r.region_id, "forecast_severity": forecast, "actual_severity": actual}))
    weather = pd.concat(wx_rows, ignore_index=True)

    def label(o: pd.DataFrame, h: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        prev = (pd.to_datetime(h["date"]) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
        ops_idx = daily_ops.set_index(["date", "warehouse_id"]).backlog_index
        backlog = ops_idx.reindex(list(zip(prev, o.warehouse_id))).fillna(0.8).values
        wx_idx = weather.set_index(["date", "region_id"])
        wx = wx_idx.reindex(list(zip(h["date"], o.region_id)))
        fc, ac = wx.forecast_severity.fillna(0).values, wx.actual_severity.fillna(0).values
        c = cal.loc[h["date"].values]
        k = L.get("scale", 1.0)
        z = (L["b0"] + k * (L["carrier2"] * (o.carrier_id == 2) + L["carrier3"] * (o.carrier_id == 3)
             + L["carrier3_remote"] * ((o.carrier_id == 3) & (h.remoteness >= 2))
             + L["express"] * h.express + L["backlog"] * np.maximum(0, backlog - 0.8)
             + L["forecast"] * fc + L["weather_surprise"] * (ac - fc) + L["distance"] * h.distance_km
             + L["late_hour"] * (h.hour >= 15) + L["weekend"] * c.is_weekend.values + L["peak"] * c.is_peak.values
             + L["items"] * o.items_count + L["weight"] * o.total_weight_kg + L["long_promise"] * (h.promised_days >= 5))
             + rng.normal(0, L["noise_sd"], len(o)))
        p = 1 / (1 + np.exp(-z.astype(float)))
        return (rng.random(len(o)) < p).astype(int), backlog, c.is_peak.values

    is_late, backlog, is_peak = label(orders, h)
    promised = pd.to_datetime(orders.promised_date)
    shipped = pd.to_datetime(orders.order_ts).dt.tz_localize(None) + pd.to_timedelta(rng.integers(4, 30, len(orders)), "h")
    deliv_day = np.where(is_late == 1, rng.integers(1, 5, len(orders)), -rng.integers(0, 3, len(orders)))
    delivered = promised + pd.to_timedelta(deliv_day, "D") + pd.to_timedelta(rng.integers(8, 20, len(orders)), "h")
    delivered = np.maximum(delivered, shipped + pd.Timedelta(hours=6))
    # an on-time order never slips past its promised day because it shipped late: cap it at 23:00 on the promised date
    delivered = np.where(is_late == 1, delivered, np.minimum(delivered, promised + pd.Timedelta(hours=23)))
    delivered = pd.Series(pd.to_datetime(delivered))
    shipments = pd.DataFrame({"order_id": orders.order_id, "shipped_ts": shipped.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "delivered_ts": delivered.dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "carrier_id": orders.carrier_id})

    # bronze duplicates (0.5%)
    dup = orders.sample(int(len(orders) * C["duplicate_rate"]), random_state=CFG["seed"])
    orders_bronze = pd.concat([orders, dup]).sample(frac=1, random_state=CFG["seed"]).reset_index(drop=True)

    # open orders (3 days before as_of), no label
    as_of = pd.Timestamp(D["as_of"])
    open_days = (as_of - pd.to_timedelta([3, 2, 1], "D")).strftime("%Y-%m-%d").values
    open_orders, _ = make_orders(C["open_orders"], 200001, open_days, np.array([0.3, 0.35, 0.35]), False)
    open_orders["status"] = "in_transit"
    # open orders need ops + weather rows for those days too
    extra_ops = []
    for d in (as_of - pd.to_timedelta([4, 3, 2, 1], "D")).strftime("%Y-%m-%d"):
        for wh in WAREHOUSES.warehouse_id:
            extra_ops.append({"date": d, "warehouse_id": wh, "backlog_index": round(float(rng.uniform(0.6, 1.3)), 3), "staffing_level": "normal"})
    daily_ops = pd.concat([daily_ops, pd.DataFrame(extra_ops)], ignore_index=True)
    extra_wx = []
    for d in open_days:
        for r in REGIONS.region_id:
            a = int(rng.choice([0, 0, 0, 1, 2])); extra_wx.append({"date": d, "region_id": r, "forecast_severity": a, "actual_severity": a})
    weather = pd.concat([weather, pd.DataFrame(extra_wx)], ignore_index=True)

    # sample orders for Part 2 (labelled)
    samp = orders.sample(C["sample_orders"], random_state=CFG["seed"]).copy()
    samp["is_late"] = is_late[samp.index]
    samp = samp.sort_values("order_id")

    # write
    ref, hist, ops = DATA / "reference", DATA / "history", DATA / "ops"
    for p in (ref, hist, ops): p.mkdir(parents=True, exist_ok=True)
    files = {ref / "carriers.csv": CARRIERS, ref / "warehouses.csv": WAREHOUSES, ref / "regions.csv": REGIONS,
             ref / "calendar_raw.csv": calendar(), ref / "orders_sample.csv": samp,
             hist / "customers.csv": cust, hist / "orders.csv": orders_bronze, hist / "shipments.csv": shipments,
             hist / "daily_ops.csv": daily_ops, hist / "weather_daily.csv": weather}
    manifest = {"baseUrl": BASE_URL, "seed": CFG["seed"], "files": []}
    for p, df in files.items():
        df.to_csv(p, index=False, lineterminator="\n")
        rel = p.relative_to(DATA).as_posix()
        manifest["files"].append({"path": rel, "url": f"{BASE_URL}/{rel}", "rows": int(len(df)),
                                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]})
    manifest["history_files"] = [f["path"].split("/", 1)[1] for f in manifest["files"] if f["path"].startswith("history/")]
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    write_ops_sql(open_orders, ops / "sqldb_ops_setup.sql")

    stats = {"rows": {k.name: len(v) for k, v in files.items()}, "late_rate": float(is_late.mean()),
             "carrier3_remote_late": float(is_late[(orders.carrier_id == 3) & (h.remoteness >= 2)].mean()),
             "peak_late": float(is_late[is_peak == 1].mean()), "offpeak_late": float(is_late[is_peak == 0].mean())}
    stats["peak_ratio"] = stats["peak_late"] / stats["offpeak_late"]
    (HERE / "last_run_stats.json").write_text(json.dumps(stats, indent=1))
    if check:
        print(json.dumps(stats, indent=1))
    return stats


def write_ops_sql(open_orders: pd.DataFrame, path: Path) -> None:
    lines = ["-- sqldb_brightcart_ops: created in demo 2.5, used by Lab 5 (alert fallback) and Lab 6 (nightly source).",
             "-- Run in the Fabric SQL database query editor. Idempotent.",
             "IF OBJECT_ID('dbo.open_orders') IS NOT NULL DROP TABLE dbo.open_orders;",
             "IF OBJECT_ID('dbo.risk_alerts') IS NOT NULL DROP TABLE dbo.risk_alerts;",
             "CREATE TABLE dbo.open_orders (order_id INT PRIMARY KEY, customer_id INT, order_ts DATETIME2(0), region_id INT,",
             "  warehouse_id INT, carrier_id INT, ship_method VARCHAR(10), items_count INT, total_weight_kg FLOAT,",
             "  order_value FLOAT, promised_date DATE, channel VARCHAR(5), status VARCHAR(20));",
             "CREATE TABLE dbo.risk_alerts (alert_id INT IDENTITY(1,1) PRIMARY KEY, order_id INT, late_risk FLOAT,",
             "  order_value FLOAT, created_at DATETIME2(0) DEFAULT SYSUTCDATETIME());",
             "GO"]
    rows = open_orders.itertuples(index=False)
    chunk = []
    for i, r in enumerate(rows, 1):
        chunk.append(f"({r.order_id},{r.customer_id},'{r.order_ts.replace('T', ' ').rstrip('Z')}',{r.region_id},{r.warehouse_id},"
                     f"{r.carrier_id},'{r.ship_method}',{r.items_count},{r.total_weight_kg},{r.order_value},'{r.promised_date}','{r.channel}','{r.status}')")
        if len(chunk) == 500 or i == len(open_orders):
            lines.append("INSERT INTO dbo.open_orders VALUES\n" + ",\n".join(chunk) + ";")
            chunk = []
    lines.append(f"-- {len(open_orders)} open orders inserted.")
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)
