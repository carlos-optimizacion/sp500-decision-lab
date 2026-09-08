"""Confidence Score y regla de bloqueo de señales fuertes."""

from __future__ import annotations

import pandas as pd


def compute_confidence_score(
    frame: pd.DataFrame,
    weights: dict[str, float],
    data_quality_score: float | pd.Series,
    walk_forward_score: float | pd.Series = 50.0,
    model_flags: dict[str, bool] | None = None,
) -> pd.DataFrame:
    flags = {"kalman": True, "hmm": True, "change_point": True, **(model_flags or {})}
    result = pd.DataFrame(index=frame.index)
    result["confidence_kalman"] = frame.get("kalman_confidence", pd.Series(50, index=frame.index)).fillna(50).clip(0, 100)
    max_probability = frame.get("regime_max_probability", pd.Series(50, index=frame.index)).fillna(50)
    entropy_stability = frame.get("regime_stability", pd.Series(50, index=frame.index)).fillna(50)
    result["confidence_regime"] = (0.55 * max_probability + 0.45 * entropy_stability).clip(0, 100)
    result["confidence_structural_stability"] = (
        100 - frame.get("change_risk", pd.Series(50, index=frame.index)).fillna(50)
    ).clip(0, 100)
    result["confidence_model_stability"] = frame.get(
        "model_fit_confidence", pd.Series(60, index=frame.index)
    ).fillna(60).clip(0, 100)
    if isinstance(data_quality_score, pd.Series):
        result["confidence_data_quality"] = data_quality_score.reindex(frame.index).ffill().fillna(50).clip(0, 100)
    else:
        result["confidence_data_quality"] = float(data_quality_score)
    if isinstance(walk_forward_score, pd.Series):
        result["confidence_walk_forward"] = walk_forward_score.reindex(frame.index).ffill().fillna(50).clip(0, 100)
    else:
        result["confidence_walk_forward"] = float(walk_forward_score)

    mapping = {
        "kalman": "confidence_kalman",
        "regime": "confidence_regime",
        "structural_stability": "confidence_structural_stability",
        "model_stability": "confidence_model_stability",
        "data_quality": "confidence_data_quality",
        "walk_forward": "confidence_walk_forward",
    }
    enabled = {
        "kalman": flags["kalman"],
        "regime": flags["hmm"],
        "structural_stability": flags["change_point"],
        "model_stability": flags["hmm"] or flags["egarch"],
        "data_quality": True,
        "walk_forward": True,
    }
    denominator = sum(float(weights[key]) for key in mapping if enabled[key])
    result["confidence_score"] = (
        sum(result[column] * float(weights[key]) for key, column in mapping.items() if enabled[key]) / denominator
    ).clip(0, 100)
    return result
