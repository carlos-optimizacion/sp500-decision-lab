from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def market_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2018-01-02", periods=900)
    returns = rng.normal(0.00035, 0.012, len(index))
    adjusted = 250 * np.exp(np.cumsum(returns))
    close = adjusted * 1.002
    open_price = close * (1 + rng.normal(0, 0.002, len(index)))
    high = np.maximum(open_price, close) * 1.004
    low = np.minimum(open_price, close) * 0.996
    return pd.DataFrame(
        {
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Adj Close": adjusted,
            "Volume": rng.integers(10_000_000, 150_000_000, len(index)),
            "vix": 18 + rng.normal(0, 2, len(index)),
            "macro_treasury_2y": 2.0,
            "macro_treasury_10y": 2.8,
            "macro_fed_funds": 2.2,
            "macro_credit_spread": 3.5,
            "macro_cpi": np.linspace(250, 290, len(index)),
            "macro_unemployment": 4.0,
            "macro_dollar_index": 105.0,
            "macro_wti": 75.0,
        },
        index=index,
    )

