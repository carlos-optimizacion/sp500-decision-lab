from __future__ import annotations

import numpy as np

from core.analysis import load_snapshot


def test_bundled_snapshot_is_internally_consistent():
    bundle = load_snapshot()
    decisions = bundle.decisions
    assert decisions.index.is_monotonic_increasing
    assert not decisions.index.duplicated().any()
    assert decisions.index.min().year == 2020
    assert decisions[["opportunity_score", "risk_score", "confidence_score"]].apply(lambda values: values.between(0, 100).all()).all()
    regime_columns = ["regime_Bull", "regime_Neutral", "regime_Correction", "regime_Stress"]
    assert np.allclose(decisions[regime_columns].sum(axis=1), 1.0, atol=1e-6)
    assert (bundle.fold_metrics["train_end"] < bundle.fold_metrics["test_start"]).all()
