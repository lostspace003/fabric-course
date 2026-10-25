"""Shared pieces of the feature contract (kit/02 §5 and kit/contracts/feature_contract.json).

Everything that both the app and the mock need lives here: the 16 column names in order,
the decision policy, and the small lookups the form uses to prefill backlog and forecast.
"""

# The 16 input columns, in the exact order the endpoint expects (orientation "values").
CONTRACT_COLUMNS = [
    "carrier_id",
    "ship_method_express",
    "warehouse_id",
    "region_id",
    "remoteness",
    "distance_km",
    "order_hour",
    "order_dow",
    "is_weekend",
    "is_peak",
    "items_count",
    "total_weight_kg",
    "order_value",
    "promised_days",
    "backlog_index",
    "forecast_severity",
]

# Decision thresholds from the contract.
EXTEND_THRESHOLD = 0.35
EXPRESS_THRESHOLD = 0.6

# Alert rule (used only for display; Activator enforces it in Fabric).
ALERT_RISK = 0.7
ALERT_VALUE = 200.0


def decision_policy(late_risk: float, express: int) -> str:
    """Return keep_promise / extend_promise / offer_express exactly as the contract says.

    - below 0.35            -> keep_promise
    - 0.35 to below 0.6     -> extend_promise
    - 0.6 or above          -> offer_express if the order is standard, else extend_promise
    """
    if late_risk < EXTEND_THRESHOLD:
        return "keep_promise"
    if late_risk < EXPRESS_THRESHOLD:
        return "extend_promise"
    return "extend_promise" if int(express) == 1 else "offer_express"


# --- Small reference lookups (copied from data/generator/generate.py) ---------------------

CARRIERS = {1: "Swiftline", 2: "Parcelaro", 3: "Northway Freight"}

WAREHOUSES = {1: "Northgate Hub (Leeds)", 2: "Riverside DC (Bristol)",
              3: "Eastfield Depot (Norwich)", 4: "Southbay Hub (Southampton)"}

# region_id -> (name, remoteness, home_warehouse_id, base_distance_km)
REGIONS = {
    1: ("Leeds City", 0, 1, 12),
    2: ("Manchester", 0, 1, 65),
    3: ("Bristol City", 0, 2, 10),
    4: ("Cardiff", 1, 2, 70),
    5: ("Norwich City", 0, 3, 14),
    6: ("Cambridge", 1, 3, 95),
    7: ("Southampton City", 0, 4, 11),
    8: ("Brighton", 1, 4, 90),
    9: ("Peak District", 2, 1, 140),
    10: ("Welsh Valleys", 2, 2, 160),
    11: ("Norfolk Broads", 2, 3, 120),
    12: ("Isle of Wight", 3, 4, 210),
}

# "Yesterday's" backlog per warehouse. Editable in the form; these are just sensible defaults.
BACKLOG_LOOKUP = {1: 0.95, 2: 1.10, 3: 0.80, 4: 0.90}

# Weather forecast issued the day before, per region (0 clear .. 3 severe).
FORECAST_LOOKUP = {1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0, 7: 0, 8: 1, 9: 2, 10: 1, 11: 1, 12: 2}
