"""Decision policy boundaries at 0.35 and 0.6."""
import pytest

from policy import decision_policy


@pytest.mark.parametrize("risk,express,expected", [
    (0.00, 0, "keep_promise"),
    (0.3499, 0, "keep_promise"),
    (0.35, 0, "extend_promise"),       # boundary: 0.35 is extend
    (0.5999, 0, "extend_promise"),
    (0.60, 0, "offer_express"),        # boundary: 0.6 standard -> offer express
    (0.60, 1, "extend_promise"),       # boundary: 0.6 express -> extend
    (0.99, 0, "offer_express"),
    (0.99, 1, "extend_promise"),
    (0.35, 1, "extend_promise"),
])
def test_decision_policy(risk, express, expected):
    assert decision_policy(risk, express) == expected
