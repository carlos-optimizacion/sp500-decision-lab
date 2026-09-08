from __future__ import annotations

import numpy as np
import pandas as pd

from core.config import load_settings
from decision.engine import build_decision_frame


def test_low_confidence_caps_exposure():
    index = pd.bdate_range("2025-01-01", periods=8)
    frame = pd.DataFrame(index=index)
    frame["distance_ma200"] = 0.20
    frame["ma20_vs_ma50"] = 0.08
    frame["kalman_slope_20d"] = 0.10
    frame["momentum_20d"] = 0.15
    frame["momentum_60d"] = 0.30
    frame["drawdown"] = -0.08
    frame["vix_percentile"] = 10
    frame["egarch_volatility_percentile"] = 10
    frame["change_risk"] = 95
    frame["kalman_confidence"] = 0
    frame["regime_Bull"] = 0.95
    frame["regime_Neutral"] = 0.03
    frame["regime_Correction"] = 0.01
    frame["regime_Stress"] = 0.01
    frame["regime_stability"] = 90
    frame["regime_max_probability"] = 95
    frame["yield_spread_z_252d"] = 1
    frame["credit_spread_percentile"] = 10
    frame["fed_funds_change_60d"] = -0.5
    result = build_decision_frame(frame, load_settings()["decision"], data_quality_score=0, walk_forward_score=0)
    assert result["confidence_score"].lt(60).all()
    assert result["target_exposure"].le(0.25).all()
    assert result[["opportunity_score", "risk_score", "confidence_score"]].apply(lambda column: column.between(0, 100).all()).all()

