from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.engine import run_backtest
from backtesting.walk_forward import expanding_year_splits


def test_signal_is_shifted_one_session():
    index = pd.bdate_range("2025-01-01", periods=3)
    frame = pd.DataFrame({"return_1d": [np.nan, 0.10, -0.10], "target_exposure": [1.0, 0.0, 0.0]}, index=index)
    result = run_backtest(frame)
    assert np.isclose(result.daily["strategy_return"].iloc[0], 0.10)
    assert np.isclose(result.daily["strategy_return"].iloc[1], 0.0)


def test_walk_forward_train_precedes_test():
    index = pd.bdate_range("2016-01-01", "2023-12-31")
    splits = list(expanding_year_splits(index, "2016-01-01", 2020))
    assert len(splits) == 4
    for train, test, fold in splits:
        assert train.max() < test.min()
        assert fold.train_end < fold.test_start

