"""Cálculo interpretable del Risk Score."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _neutral(series: pd.Series | None, index: pd.Index, value: float = 50.0) -> pd.Series:
    if series is None:
        return pd.Series(value, index=index, dtype=float)
    return series.astype(float).reindex(index).fillna(value).clip(0, 100)


def regime_risk(frame: pd.DataFrame) -> pd.Series:
    weights = {"Bull": 10.0, "Neutral": 38.0, "Correction": 68.0, "Stress": 95.0}
    available = [f"regime_{name}" for name in weights if f"regime_{name}" in frame]
    if len(available) != 4:
        return pd.Series(50.0, index=frame.index)
    return sum(frame[f"regime_{name}"].fillna(0) * score for name, score in weights.items()).clip(0, 100)


def compute_risk_components(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    result["risk_egarch"] = _neutral(frame.get("egarch_volatility_percentile"), frame.index)
    result["risk_vix"] = _neutral(frame.get("vix_percentile"), frame.index)
    result["risk_drawdown"] = ((-frame.get("drawdown", pd.Series(0, index=frame.index))).clip(lower=0) / 0.35 * 100).clip(0, 100)
    result["risk_change"] = _neutral(frame.get("change_risk"), frame.index)
    result["risk_regime"] = regime_risk(frame)
    return result


def compute_risk_score(
    frame: pd.DataFrame,
    weights: dict[str, float],
    model_flags: dict[str, bool] | None = None,
) -> pd.DataFrame:
    flags = {"egarch": True, "hmm": True, "change_point": True, **(model_flags or {})}
    components = compute_risk_components(frame)
    keys = {
        "egarch": "risk_egarch",
        "vix": "risk_vix",
        "drawdown": "risk_drawdown",
        "change": "risk_change",
        "regime": "risk_regime",
    }
    enabled = {
        "egarch": flags["egarch"],
        "vix": True,
        "drawdown": True,
        "change": flags["change_point"],
        "regime": flags["hmm"],
    }
    denominator = sum(float(weights[key]) for key in keys if enabled[key])
    score = sum(components[column] * float(weights[key]) for key, column in keys.items() if enabled[key]) / denominator
    components["risk_score"] = score.clip(0, 100)
    return components

