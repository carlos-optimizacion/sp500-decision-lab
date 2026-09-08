"""Motor que convierte estados cuantitativos en rangos, nunca en órdenes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .confidence import compute_confidence_score
from .opportunity import compute_opportunity_components, compute_opportunity_score
from .risk import compute_risk_score


DECISION_LABELS = {
    "wait": "Esperar / Riesgo elevado",
    "partial": "Entrada muy parcial / Condición incierta",
    "gradual": "Entrada gradual favorable",
    "favorable": "Condición históricamente muy favorable",
}


def _decision_label(
    opportunity: float,
    risk: float,
    confidence: float,
    minimum_confidence: float,
    maximum_risk: float,
    thresholds: list[float],
) -> str:
    if not np.isfinite(opportunity) or not np.isfinite(confidence):
        return "Datos insuficientes"
    low, medium, high = thresholds
    if risk >= maximum_risk or opportunity < low:
        return DECISION_LABELS["wait"]
    if confidence < minimum_confidence or opportunity < medium:
        return DECISION_LABELS["partial"]
    if opportunity < high:
        return DECISION_LABELS["gradual"]
    return DECISION_LABELS["favorable"]


def _target_exposure(
    opportunity: pd.Series,
    risk: pd.Series,
    confidence: pd.Series,
    thresholds: list[float],
    exposure_levels: list[float],
    minimum_confidence: float,
    maximum_risk: float,
    confidence_cap: float,
) -> pd.Series:
    bins = [-np.inf, *thresholds, np.inf]
    exposure = pd.cut(opportunity, bins=bins, labels=exposure_levels, right=False).astype(float)
    exposure = exposure.where(confidence >= minimum_confidence, np.minimum(exposure, confidence_cap))
    exposure = exposure.where(risk < maximum_risk, 0.0)
    return exposure.fillna(0).clip(0, 1)


def build_decision_frame(
    frame: pd.DataFrame,
    config: dict[str, Any],
    data_quality_score: float | pd.Series = 90.0,
    walk_forward_score: float | pd.Series = 50.0,
    model_flags: dict[str, bool] | None = None,
) -> pd.DataFrame:
    flags = {"kalman": True, "hmm": True, "egarch": True, "change_point": True, **(model_flags or {})}
    result = frame.copy()
    risk = compute_risk_score(result, config["risk_weights"], flags)
    result = result.join(risk)
    opportunity_components = compute_opportunity_components(
        result,
        result["risk_score"],
        use_kalman=flags["kalman"],
        use_hmm=flags["hmm"],
    )
    result = result.join(opportunity_components)
    result["opportunity_score"] = compute_opportunity_score(opportunity_components, config["opportunity_weights"])
    confidence = compute_confidence_score(
        result,
        config["confidence_weights"],
        data_quality_score,
        walk_forward_score,
        flags,
    )
    result = result.join(confidence)
    minimum = float(config["minimum_strong_confidence"])
    maximum_risk = float(config["maximum_risk_for_exposure"])
    confidence_cap = float(config["low_confidence_exposure_cap"])
    thresholds = [float(value) for value in config["thresholds"]]
    result["decision_state"] = [
        _decision_label(opportunity, risk_value, confidence_value, minimum, maximum_risk, thresholds)
        for opportunity, risk_value, confidence_value in zip(
            result["opportunity_score"], result["risk_score"], result["confidence_score"]
        )
    ]
    result["target_exposure"] = _target_exposure(
        result["opportunity_score"],
        result["risk_score"],
        result["confidence_score"],
        thresholds,
        [float(value) for value in config["exposure_levels"]],
        minimum,
        maximum_risk,
        confidence_cap,
    )
    result["condition_volatility"] = (100 - result["risk_egarch"]).clip(0, 100)
    result["condition_global_risk"] = (100 - result["risk_score"]).clip(0, 100)
    result["condition_liquidity"] = result["score_macro"].clip(0, 100)
    return result


def explain_latest_signal(frame: pd.DataFrame) -> dict[str, list[str]]:
    if frame.empty:
        return {"positive": [], "risks": []}
    row = frame.dropna(subset=["opportunity_score", "risk_score"], how="any").iloc[-1]
    positives = {
        "Tendencia": float(row.get("score_trend", 50)),
        "Momentum": float(row.get("score_momentum", 50)),
        "Régimen": float(row.get("score_regime", 50)),
        "Entorno macro/liquidez": float(row.get("score_macro", 50)),
        "Valor por drawdown": float(row.get("score_drawdown_value", 50)),
    }
    risks = {
        "Volatilidad EGARCH": float(row.get("risk_egarch", 50)),
        "VIX": float(row.get("risk_vix", 50)),
        "Drawdown": float(row.get("risk_drawdown", 50)),
        "Ruptura estructural": float(row.get("risk_change", 50)),
        "Régimen adverso": float(row.get("risk_regime", 50)),
    }
    positive_text = [f"{name}: {value:.0f}/100" for name, value in sorted(positives.items(), key=lambda item: item[1], reverse=True)[:3]]
    risk_text = [f"{name}: {value:.0f}/100" for name, value in sorted(risks.items(), key=lambda item: item[1], reverse=True)[:3]]
    return {"positive": positive_text, "risks": risk_text}
