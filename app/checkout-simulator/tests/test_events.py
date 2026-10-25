"""Events validate against kit/contracts/checkout_event.schema.json; sender is a no-op when unset."""
import json
import os
import random

import jsonschema

from events import EventSender, build_event, new_order_id
from mock import random_orders, mock_score
from policy import CONTRACT_COLUMNS, decision_policy

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "..", "..", "kit", "contracts", "checkout_event.schema.json")


def test_events_match_schema():
    with open(SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    orders = random_orders(50, seed=7)
    risks = mock_score([[o[c] for c in CONTRACT_COLUMNS] for o in orders])
    rng = random.Random(7)
    for o, r in zip(orders, risks):
        ev = build_event(o, r, decision_policy(r, o["ship_method_express"]), "mock", 12, order_id=new_order_id(rng))
        validator.validate(ev)


def test_order_id_format():
    rng = random.Random(1)
    for _ in range(100):
        oid = new_order_id(rng)
        assert len(oid) == 8 and oid[0] == "S" and oid[1:].isdigit()


def test_sender_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("EVENTSTREAM_CONNECTION_STRING", raising=False)
    s = EventSender()
    assert s.configured is False
    assert s.send([{"anything": 1}]) == 0
