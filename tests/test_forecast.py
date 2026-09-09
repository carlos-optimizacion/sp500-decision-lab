from __future__ import annotations

from copy import deepcopy

import numpy as np

from core.config import load_settings
from data.features import build_features
from forecasting import build_next_session_forecast


def _settings():
    settings = deepcopy(load_settings())
    settings["backtest"]["train_start"] = "2018-01-01"
    settings["backtest"]["first_test_year"] = 2020
    settings["forecast"]["minimum_train_observations"] = 250
    settings["forecast"]["minimum_validation_observations"] = 100
    settings["models"]["egarch"]["min_train_observations"] = 250
    settings["models"]["egarch"]["iterations"] = 45
    return settings


def _model_frame(features):
    return features.assign(egarch_volatility_forecast=features["volatility_20d"])


def test_next_session_forecast_has_probabilities_and_interval(market_frame):
    features = build_features(market_frame)
    result = build_next_session_forecast(features, _model_frame(features), _settings())
    current = result.current
    assert 0.0 <= current["probability_positive"] <= 1.0
    assert current["lower_price"] < current["expected_price"] < current["upper_price"]
    assert current["volatility_annualized"] > 0.0
    assert result.validation["observations"] > 100
    assert result.history.index.is_monotonic_increasing
    evaluated = result.history.dropna(subset=["realized_return", "outcome_date"])
    assert (evaluated["outcome_date"] > evaluated.index).all()


def test_forecast_does_not_change_past_when_future_is_altered(market_frame):
    split = 760
    baseline_market = market_frame.iloc[:split].copy()
    altered_market = market_frame.copy()
    factor = np.linspace(1.0, 2.0, len(altered_market) - split)
    for column in ("Open", "High", "Low", "Close", "Adj Close"):
        altered_market.iloc[split:, altered_market.columns.get_loc(column)] *= factor
    baseline_features = build_features(baseline_market)
    altered_features = build_features(altered_market)
    baseline = build_next_session_forecast(
        baseline_features,
        _model_frame(baseline_features),
        _settings(),
    ).history
    altered = build_next_session_forecast(
        altered_features,
        _model_frame(altered_features),
        _settings(),
    ).history
    common = baseline.index[:-2].intersection(altered.index)
    columns = ["probability_positive", "expected_return"]
    assert np.allclose(baseline.loc[common, columns], altered.loc[common, columns], equal_nan=True)
