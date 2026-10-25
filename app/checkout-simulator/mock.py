"""Mock mode: a local formula that approximates the generator's logit (data/generator/config.yaml).

No Fabric needed. The formula uses the same coefficients as the data generator but drops the
random noise and the "weather surprise" term (the app only knows the forecast, not the actual
weather). It also draws random simulated orders from the generator's distributions.
"""
import math
import random
from datetime import datetime, timezone

from policy import CONTRACT_COLUMNS, REGIONS, BACKLOG_LOOKUP, FORECAST_LOOKUP

MOCK_MODEL_VERSION = "mock"

# Logit coefficients, copied from data/generator/config.yaml.
SCALE = 2.6   # multiplies every signal term (config.yaml logit.scale)
B0 = -4.45
CARRIER2 = 0.35
CARRIER3 = 0.20
CARRIER3_REMOTE = 1.40
EXPRESS = -0.80
BACKLOG = 1.50
FORECAST = 0.45
DISTANCE = 0.0015
LATE_HOUR = 0.60
WEEKEND = 0.25
PEAK = 0.70
ITEMS = 0.04
WEIGHT = 0.015
LONG_PROMISE = -0.30


def mock_late_risk(row: dict) -> float:
    """late_risk for one order. `row` has the 16 contract columns as keys."""
    carrier = int(row["carrier_id"])
    remote = int(row["remoteness"]) >= 2
    z = 0.0
    z += CARRIER2 * (carrier == 2)
    z += CARRIER3 * (carrier == 3)
    z += CARRIER3_REMOTE * (carrier == 3 and remote)
    z += EXPRESS * int(row["ship_method_express"])
    z += BACKLOG * max(0.0, float(row["backlog_index"]) - 0.8)
    z += FORECAST * int(row["forecast_severity"])
    z += DISTANCE * float(row["distance_km"])
    z += LATE_HOUR * (int(row["order_hour"]) >= 15)
    z += WEEKEND * int(row["is_weekend"])
    z += PEAK * int(row["is_peak"])
    z += ITEMS * int(row["items_count"])
    z += WEIGHT * float(row["total_weight_kg"])
    z += LONG_PROMISE * (int(row["promised_days"]) >= 5)
    z = B0 + SCALE * z
    p = 1.0 / (1.0 + math.exp(-z))
    return round(p, 4)


def mock_score(rows: list[list]) -> list[float]:
    """Same shape as FabricClient.score: a list of 16-value rows in -> a list of late_risk out."""
    out = []
    for values in rows:
        row = dict(zip(CONTRACT_COLUMNS, values))
        out.append(mock_late_risk(row))
    return out


def random_order(rng: random.Random, now: datetime | None = None) -> dict:
    """One random checkout, drawn like data/generator/generate.py draws orders.

    Returns a dict with the 16 contract columns (plus nothing else), so it can go straight
    into a request row with `[order[c] for c in CONTRACT_COLUMNS]`.
    """
    now = now or datetime.now(timezone.utc)
    # Customers are spread over regions with these weights (percent).
    region_weights = [11, 13, 10, 7, 9, 7, 10, 8, 6, 6, 7, 6]
    region_id = rng.choices(list(range(1, 13)), weights=region_weights)[0]
    _, remoteness, home_wh, base_km = REGIONS[region_id]
    warehouse_id = home_wh if rng.random() < 0.85 else rng.randint(1, 4)
    carrier_id = rng.choices([1, 2, 3], weights=[30, 45, 25])[0]
    express = 1 if rng.random() < 0.22 else 0
    # Geometric(0.35) clipped to 1..12 items.
    items = 1
    while rng.random() >= 0.35 and items < 12:
        items += 1
    weight = round(items * rng.uniform(0.3, 2.5) + rng.uniform(0.1, 0.5), 2)
    value = round(items * rng.lognormvariate(3.3, 0.5) + 5, 2)
    promised = (rng.randint(1, 2) if express else rng.randint(3, 5)) + (1 if remoteness >= 2 else 0)
    distance = round(base_km * rng.uniform(0.8, 1.2), 1)
    dow = now.weekday()
    month_day = now.strftime("%m-%d")
    is_peak = 1 if "11-15" <= month_day <= "12-31" else 0
    return {
        "carrier_id": carrier_id,
        "ship_method_express": express,
        "warehouse_id": warehouse_id,
        "region_id": region_id,
        "remoteness": remoteness,
        "distance_km": distance,
        "order_hour": now.hour,
        "order_dow": dow,
        "is_weekend": 1 if dow >= 5 else 0,
        "is_peak": is_peak,
        "items_count": items,
        "total_weight_kg": weight,
        "order_value": value,
        "promised_days": min(promised, 7),
        # Jitter the lookups a little so simulated orders are not all identical.
        "backlog_index": round(min(1.6, max(0.3, BACKLOG_LOOKUP[warehouse_id] + rng.uniform(-0.2, 0.3))), 3),
        "forecast_severity": min(3, max(0, FORECAST_LOOKUP[region_id] + rng.choice([-1, 0, 0, 0, 1]))),
    }


def random_orders(n: int, seed: int | None = None) -> list[dict]:
    """n random orders. Same seed -> same orders (deterministic)."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    return [random_order(rng, now) for _ in range(n)]
