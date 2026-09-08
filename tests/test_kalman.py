from __future__ import annotations

import numpy as np
import pandas as pd

from models.kalman import KalmanTrendFilter


def test_kalman_is_causal_and_finite():
    index = pd.bdate_range("2020-01-01", periods=400)
    price = pd.Series(100 * np.exp(np.linspace(0, 0.35, len(index))), index=index)
    model = KalmanTrendFilter()
    output = model.filter(price)
    assert model.check_causality(price, 280)
    assert output["kalman_trend"].dropna().gt(0).all()
    assert output["kalman_nis"].dropna().ge(0).all()
    assert output["kalman_confidence"].dropna().between(0, 100).all()

