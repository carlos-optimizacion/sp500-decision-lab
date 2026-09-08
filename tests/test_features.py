from __future__ import annotations

import numpy as np

from data.features import build_features, compute_drawdown


def test_returns_and_drawdown(market_frame):
    features = build_features(market_frame)
    expected = market_frame["Adj Close"].iloc[20] / market_frame["Adj Close"].iloc[0] - 1
    assert np.isclose(features["return_20d"].iloc[20], expected)
    assert (compute_drawdown(market_frame["Adj Close"]) <= 1e-12).all()
    assert np.isclose(features["drawdown"].iloc[0], 0.0)


def test_features_do_not_change_when_future_is_appended(market_frame):
    split = 700
    baseline = build_features(market_frame.iloc[:split])
    extended = market_frame.copy()
    extended.iloc[split:, extended.columns.get_loc("Adj Close")] *= 4
    comparison = build_features(extended).iloc[:split]
    columns = ["return_1d", "ma_200", "vix_percentile", "yield_spread_z_252d"]
    assert np.allclose(baseline[columns], comparison[columns], equal_nan=True)

