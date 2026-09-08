"""Opportunity Score: combinación de tendencia, momentum, régimen y contexto."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _series(frame: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in frame:
        return pd.Series(default, index=frame.index, dtype=float)
    return frame[name].astype(float).fillna(default)


def compute_opportunity_components(
    frame: pd.DataFrame,
    risk_score: pd.Series,
    use_kalman: bool = True,
    use_hmm: bool = True,
) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    distance = _series(frame, "distance_ma200")
    ma_cross = _series(frame, "ma20_vs_ma50")
    technical_trend = 50 + 32 * np.tanh(distance / 0.08) + 18 * np.tanh(ma_cross / 0.035)
    if use_kalman:
        slope = _series(frame, "kalman_slope_20d")
        result["score_trend"] = (0.68 * technical_trend + 0.32 * (50 + 50 * np.tanh(slope / 0.05))).clip(0, 100)
    else:
        result["score_trend"] = technical_trend.clip(0, 100)

    momentum_20 = _series(frame, "momentum_20d")
    momentum_60 = _series(frame, "momentum_60d")
    result["score_momentum"] = (
        50 + 24 * np.tanh(momentum_20 / 0.07) + 26 * np.tanh(momentum_60 / 0.14)
    ).clip(0, 100)

    if use_hmm and all(f"regime_{name}" in frame for name in ("Bull", "Neutral", "Correction", "Stress")):
        result["score_regime"] = (
            90 * frame["regime_Bull"]
            + 60 * frame["regime_Neutral"]
            + 35 * frame["regime_Correction"]
            + 10 * frame["regime_Stress"]
        ).fillna(50).clip(0, 100)
    else:
        result["score_regime"] = 50.0

    macro_parts: list[pd.Series] = []
    if "yield_spread_z_252d" in frame:
        macro_parts.append(50 + 20 * np.tanh(_series(frame, "yield_spread_z_252d") / 1.2))
    if "credit_spread_percentile" in frame:
        macro_parts.append(100 - _series(frame, "credit_spread_percentile", 50))
    if "fed_funds_change_60d" in frame:
        macro_parts.append(50 - 18 * np.tanh(_series(frame, "fed_funds_change_60d") / 0.75))
    if macro_parts:
        result["score_macro"] = pd.concat(macro_parts, axis=1).mean(axis=1).clip(0, 100)
    else:
        result["score_macro"] = 50.0

    depth = (-_series(frame, "drawdown")).clip(lower=0)
    result["score_drawdown_value"] = (
        50 + 35 * (depth / 0.18).clip(0, 1) - 45 * ((depth - 0.25) / 0.25).clip(0, 1)
    ).clip(0, 100)
    result["score_inverse_risk"] = (100 - risk_score).clip(0, 100)
    return result


def compute_opportunity_score(components: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    mapping = {
        "trend": "score_trend",
        "momentum": "score_momentum",
        "regime": "score_regime",
        "inverse_risk": "score_inverse_risk",
        "macro": "score_macro",
        "drawdown_value": "score_drawdown_value",
    }
    denominator = sum(float(weights[key]) for key in mapping)
    score = sum(components[column] * float(weights[key]) for key, column in mapping.items()) / denominator
    return score.clip(0, 100).rename("opportunity_score")

