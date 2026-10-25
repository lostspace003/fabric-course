"""Mock mode runs with no env and behaves like the generator's logit."""
import os

from mock import mock_score, random_orders
from policy import CONTRACT_COLUMNS


def test_mock_runs_without_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith("FABRIC_") or k.startswith("EVENTSTREAM_"):
            monkeypatch.delenv(k)
    orders = random_orders(20, seed=3)
    risks = mock_score([[o[c] for c in CONTRACT_COLUMNS] for o in orders])
    assert len(risks) == 20
    assert all(0.0 <= r <= 1.0 for r in risks)


def test_mock_is_deterministic():
    assert random_orders(10, seed=5) == random_orders(10, seed=5)


def test_mock_direction():
    # Easy order: express, carrier 1, urban, no backlog.
    easy = [1, 1, 1, 1, 0, 12.0, 10, 1, 0, 0, 1, 0.9, 42.5, 1, 0.65, 0]
    # Hard order: standard, carrier 3 remote, afternoon, peak, backlog, bad forecast.
    hard = [3, 0, 2, 12, 3, 210.0, 16, 5, 1, 1, 6, 8.0, 249.0, 5, 1.5, 3]
    easy_r, hard_r = mock_score([easy, hard])
    assert easy_r < 0.35
    assert hard_r >= 0.6


def test_import_app_module():
    """`import app` must work in mock mode (Streamlit is only used inside main())."""
    import app  # noqa: F401
    assert app.model_version_label() == "mock"
