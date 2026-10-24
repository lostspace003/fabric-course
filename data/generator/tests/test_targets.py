"""Kit 02 §4.4 targets. Run: .venv/Scripts/python -m pytest data/generator/tests -q
The feature build here mirrors nb_02_features (training mode) in pandas, so the AUC test is the same model
learners train in Lab 3 (v1 profile) against the same baseline."""
import json, subprocess, sys, hashlib
from pathlib import Path
import numpy as np, pandas as pd, pytest, yaml

GEN = Path(__file__).resolve().parents[1]
DATA = GEN.parent
CFG = yaml.safe_load((GEN / "config.yaml").read_text())
T = CFG["targets"]
sys.path.insert(0, str(GEN))
from features import build_training_frame, FEATURES  # noqa: E402


@pytest.fixture(scope="session")
def stats():
    subprocess.run([sys.executable, str(GEN / "generate.py")], check=True)
    return json.loads((GEN / "last_run_stats.json").read_text())


def test_deterministic(stats):
    h1 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*/*.csv")}
    subprocess.run([sys.executable, str(GEN / "generate.py")], check=True)
    h2 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*/*.csv")}
    assert h1 == h2


def test_row_counts(stats):
    r = stats["rows"]
    assert 89000 <= r["orders.csv"] <= 92000 and r["shipments.csv"] == 90000
    assert r["customers.csv"] == 8000 and r["orders_sample.csv"] == 5000 and r["regions.csv"] == 12
    m = json.loads((DATA / "manifest.json").read_text())
    assert {f["path"].split("/")[-1]: f["rows"] for f in m["files"]} == r


def test_late_rate(stats):
    assert T["late_rate"][0] <= stats["late_rate"] <= T["late_rate"][1]


def test_carrier3_remote(stats):
    assert stats["carrier3_remote_late"] >= T["carrier3_remote_min"]


def test_peak_ratio(stats):
    assert stats["peak_ratio"] >= T["peak_ratio_min"]


def test_duplicates(stats):
    o = pd.read_csv(DATA / "history/orders.csv")
    assert 0.003 <= o.duplicated("order_id").mean() <= 0.007


def test_model_lead(stats):
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.pipeline import make_pipeline
    from sklearn.compose import make_column_transformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    df = build_training_frame(DATA)
    assert df[FEATURES].isna().sum().sum() == 0
    tr, ho = df[df.split == "train"], df[df.split == "holdout"]
    assert len(ho) > 5000
    cat = ["carrier_id", "warehouse_id", "region_id"]
    b = lgb.train({"objective": "binary", "num_leaves": 15, "learning_rate": 0.05, "verbose": -1, "seed": 42},
                  lgb.Dataset(tr[FEATURES], tr.is_late, categorical_feature=cat), 200)
    auc = roc_auc_score(ho.is_late, b.predict(ho[FEATURES]))
    base = make_pipeline(make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler()),
                         LogisticRegression(max_iter=1000))
    base.fit(tr[FEATURES], tr.is_late)
    auc_b = roc_auc_score(ho.is_late, base.predict_proba(ho[FEATURES])[:, 1])
    print(f"\nLightGBM v1 AUC {auc:.3f}  baseline {auc_b:.3f}")
    assert T["lgbm_auc"][0] <= auc <= T["lgbm_auc"][1]
    assert auc - auc_b >= T["baseline_gap_min"]
