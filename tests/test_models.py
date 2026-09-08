from __future__ import annotations

import numpy as np
import pandas as pd

from models.change_point import causal_change_risk
from models.egarch import EGARCHModel
from models.hmm import GaussianRegimeHMM


def test_egarch_forecast_is_positive():
    rng = np.random.default_rng(7)
    train = pd.Series(rng.normal(0, 0.012, 700))
    test = pd.Series(rng.normal(0, 0.015, 40), index=pd.bdate_range("2025-01-02", periods=40))
    model = EGARCHModel(max_iterations=80).fit(train)
    forecast = model.forecast_sequence(test)
    assert len(forecast) == len(test)
    assert forecast.gt(0).all()


def test_hmm_probabilities_sum_to_one():
    rng = np.random.default_rng(11)
    blocks = []
    for mean, volatility in [(0.7, 0.6), (0.1, 0.9), (-0.3, 1.1), (-0.9, 1.8)]:
        block = np.column_stack([rng.normal(mean, 0.3, 220), rng.normal(volatility, 0.15, 220), rng.normal(0, 1, 220)])
        blocks.append(block)
    values = np.vstack(blocks)
    model = GaussianRegimeHMM(max_iterations=35).fit(values)
    probabilities = model.filter_probabilities(values)
    regime_columns = ["regime_Bull", "regime_Neutral", "regime_Correction", "regime_Stress"]
    assert np.allclose(probabilities[regime_columns].sum(axis=1), 1.0)
    assert set(probabilities["regime_label"].unique()).issubset({"Bull", "Neutral", "Correction", "Stress"})


def test_change_risk_has_no_future_leakage():
    rng = np.random.default_rng(13)
    index = pd.bdate_range("2020-01-01", periods=400)
    returns = pd.Series(rng.normal(0, 0.01, len(index)), index=index)
    baseline = causal_change_risk(returns.iloc[:300])
    altered = returns.copy()
    altered.iloc[300:] = 0.2
    comparison = causal_change_risk(altered).iloc[:300]
    assert np.allclose(baseline, comparison, equal_nan=True)

