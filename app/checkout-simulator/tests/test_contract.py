"""Request column order matches kit/contracts/feature_contract.json."""
import json
import os

from policy import CONTRACT_COLUMNS
from fabric_client import build_request
from mock import random_orders

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "..", "..", "..", "kit", "contracts", "feature_contract.json")
SAMPLE = os.path.join(HERE, "..", "..", "..", "kit", "contracts", "score_request.sample.json")


def test_column_order_matches_contract():
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)
    expected = [c["name"] for c in sorted(contract["inputs"], key=lambda c: c["order"])]
    assert CONTRACT_COLUMNS == expected
    assert len(CONTRACT_COLUMNS) == 16


def test_request_shape_matches_sample():
    with open(SAMPLE, encoding="utf-8") as f:
        sample = json.load(f)
    order = random_orders(1, seed=1)[0]
    body = build_request([[order[c] for c in CONTRACT_COLUMNS]])
    assert body["formatType"] == sample["formatType"] == "dataframe"
    assert body["orientation"] == sample["orientation"] == "values"
    assert len(body["inputs"][0]) == len(sample["inputs"][0]) == 16


def test_random_orders_respect_ranges():
    for o in random_orders(200, seed=42):
        assert 1 <= o["carrier_id"] <= 3
        assert o["ship_method_express"] in (0, 1)
        assert 1 <= o["warehouse_id"] <= 4
        assert 1 <= o["region_id"] <= 12
        assert 0 <= o["remoteness"] <= 3
        assert 1 <= o["items_count"] <= 12
        assert 1 <= o["promised_days"] <= 7
        assert 0.3 <= o["backlog_index"] <= 1.6
        assert 0 <= o["forecast_severity"] <= 3
