"""Planted-effect tests for cuped_segments.py (synthetic data, used only to test the code).

Builds a fake Criteo-shaped file where the true treatment effect, the share of
outcome variance explained by the features, and the per-decile effects are known,
then checks the estimator recovers them.
"""
import gzip

import numpy as np
import pytest

from cuped_segments import run, FEATURES


def make_file(path, n=400_000, effect=0.02, seed=0, hetero=False):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 12))
    t = (rng.random(n) < 0.85).astype(int)
    base = 0.30 + 0.08 * X[:, 0] - 0.05 * X[:, 3] + 0.04 * X[:, 7]
    base = np.clip(base, 0.01, 0.99)
    eff = effect * (1 + 2 * (base > np.median(base))) if hetero else np.full(n, effect)
    p = np.clip(base + t * eff, 0, 1)
    visit = (rng.random(n) < p).astype(int)
    conversion = (rng.random(n) < p * 0.2).astype(int)
    exposure = t * (rng.random(n) < 0.05).astype(int)
    with gzip.open(path, "wt") as f:
        f.write(",".join(FEATURES + ["treatment", "conversion", "visit", "exposure"]) + "\n")
        for i in range(n):
            f.write(",".join(f"{v:.6f}" for v in X[i]) + f",{t[i]},{conversion[i]},{visit[i]},{exposure[i]}\n")
    return base, eff


@pytest.fixture(scope="module")
def homogeneous(tmp_path_factory):
    p = tmp_path_factory.mktemp("d") / "h.csv.gz"
    make_file(p)
    return run(str(p), expected_rows=400_000)


def test_recovers_planted_effect(homogeneous):
    r = homogeneous["visit"]
    assert r["cuped"]["ci_low"] < 0.02 < r["cuped"]["ci_high"]
    assert abs(r["cuped"]["abs_lift"] - 0.02) < 0.004


def test_variance_reduction_matches_explained_variance(homogeneous):
    # var(base) / var(visit) is the variance the features can explain
    r = homogeneous["visit"]
    explained = (0.08**2 + 0.05**2 + 0.04**2) / (0.3 * 0.7)
    assert abs(r["variance_reduction"] - explained) < 0.02
    assert r["cuped"]["se"] < r["raw"]["se"]


def test_arms_balanced(homogeneous):
    assert homogeneous["balance"]["max_abs_smd"] < 0.02


def test_no_false_heterogeneity(homogeneous):
    # constant effect: Q test should usually not reject (seeded, so deterministic)
    assert homogeneous["visit"]["heterogeneity"]["p_value"] > 0.01


def test_detects_planted_heterogeneity(tmp_path):
    p = tmp_path / "het.csv.gz"
    make_file(p, hetero=True, effect=0.03, seed=1)
    r = run(str(p), expected_rows=400_000)["visit"]
    assert r["heterogeneity"]["p_value"] < 0.001
    low = np.mean([s["abs_lift"] for s in r["segments"][:3]])
    high = np.mean([s["abs_lift"] for s in r["segments"][-3:]])
    assert high > 2 * low


def test_row_count_guard(tmp_path):
    p = tmp_path / "small.csv.gz"
    make_file(p, n=1000)
    with pytest.raises(AssertionError):
        run(str(p))
