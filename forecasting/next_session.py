"""Pronóstico probabilístico de una sesión con validación expanding walk-forward."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

from backtesting.walk_forward import expanding_year_splits
from models.egarch import EGARCHModel


DEFAULT_FEATURES = (
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "volatility_20d",
    "volatility_60d",
    "distance_ma200",
    "ma20_vs_ma50",
    "drawdown",
    "vix_change_5d",
    "vix_percentile",
    "vix_z_252d",
)


@dataclass
class ForecastResult:
    history: pd.DataFrame
    current: dict[str, Any]
    validation: dict[str, Any]


@dataclass(frozen=True)
class _Preprocessor:
    columns: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame.loc[:, list(self.columns)].to_numpy(dtype=float)
        values = np.where(np.isfinite(values), values, self.medians)
        return (values - self.means) / self.scales


def _fit_preprocessor(frame: pd.DataFrame, requested: list[str], min_valid: int) -> _Preprocessor:
    selected: list[str] = []
    medians: list[float] = []
    means: list[float] = []
    scales: list[float] = []
    for column in requested:
        if column not in frame:
            continue
        values = frame[column].to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        if len(finite) < min_valid or float(np.nanstd(finite)) < 1e-12:
            continue
        median = float(np.nanmedian(finite))
        filled = np.where(np.isfinite(values), values, median)
        mean = float(np.mean(filled))
        scale = max(float(np.std(filled)), 1e-8)
        selected.append(column)
        medians.append(median)
        means.append(mean)
        scales.append(scale)
    if len(selected) < 4:
        raise ValueError("El pronóstico necesita al menos cuatro variables con historia suficiente.")
    return _Preprocessor(
        tuple(selected),
        np.asarray(medians, dtype=float),
        np.asarray(means, dtype=float),
        np.asarray(scales, dtype=float),
    )


def _with_intercept(values: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(values), dtype=float), values])


def _fit_logistic(values: np.ndarray, target: np.ndarray, l2: float, iterations: int = 60) -> np.ndarray:
    design = _with_intercept(values)
    weights = np.zeros(design.shape[1], dtype=float)
    penalty = np.eye(design.shape[1], dtype=float) * float(l2)
    penalty[0, 0] = 1e-8
    for _ in range(iterations):
        probability = expit(np.clip(design @ weights, -30.0, 30.0))
        variance = np.clip(probability * (1.0 - probability), 1e-6, None)
        gradient = design.T @ (probability - target) / len(target) + penalty @ weights
        hessian = (design.T * variance) @ design / len(target) + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        weights -= step
        if float(np.max(np.abs(step))) < 1e-7:
            break
    return weights


def _fit_ridge(values: np.ndarray, target: np.ndarray, alpha: float) -> np.ndarray:
    design = _with_intercept(values)
    penalty = np.eye(design.shape[1], dtype=float) * float(alpha)
    penalty[0, 0] = 0.0
    system = design.T @ design + penalty
    right = design.T @ target
    try:
        return np.linalg.solve(system, right)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(system) @ right


def _predict_models(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: pd.Series,
    feature_columns: list[str],
    logistic_l2: float,
    ridge_alpha: float,
) -> tuple[np.ndarray, np.ndarray, float, tuple[str, ...]]:
    valid_target = target.reindex(train.index).notna()
    train = train.loc[valid_target]
    y_return = target.reindex(train.index).to_numpy(dtype=float)
    y_positive = (y_return > 0.0).astype(float)
    preprocessor = _fit_preprocessor(train, feature_columns, min_valid=max(80, len(train) // 3))
    train_values = preprocessor.transform(train)
    test_values = preprocessor.transform(test)
    direction_model = _fit_logistic(train_values, y_positive, logistic_l2)
    return_model = _fit_ridge(train_values, y_return, ridge_alpha)
    probability = expit(np.clip(_with_intercept(test_values) @ direction_model, -30.0, 30.0))
    expected_return = _with_intercept(test_values) @ return_model
    low, high = np.quantile(y_return, [0.01, 0.99])
    expected_return = np.clip(expected_return, low, high)
    return probability, expected_return, float(np.mean(y_positive)), preprocessor.columns


def _validation_metrics(history: pd.DataFrame, interval_level: float, minimum_rows: int) -> dict[str, Any]:
    valid = history.dropna(
        subset=[
            "realized_return",
            "probability_positive",
            "expected_return",
            "baseline_probability",
            "lower_return",
            "upper_return",
        ]
    )
    observations = int(len(valid))
    if not observations:
        return {
            "observations": 0,
            "status": "Evidencia insuficiente",
            "direction_accuracy": float("nan"),
            "baseline_accuracy": float("nan"),
            "brier_score": float("nan"),
            "baseline_brier_score": float("nan"),
            "brier_skill": float("nan"),
            "mae": float("nan"),
            "baseline_mae": float("nan"),
            "mae_skill": float("nan"),
            "interval_coverage": float("nan"),
            "interval_level": float(interval_level),
        }
    realized = valid["realized_return"].to_numpy(dtype=float)
    actual_positive = realized > 0.0
    probability = valid["probability_positive"].to_numpy(dtype=float)
    baseline_probability = valid["baseline_probability"].to_numpy(dtype=float)
    expected = valid["expected_return"].to_numpy(dtype=float)
    direction_accuracy = float(np.mean((probability >= 0.5) == actual_positive))
    baseline_accuracy = float(np.mean((baseline_probability >= 0.5) == actual_positive))
    brier = float(np.mean((probability - actual_positive.astype(float)) ** 2))
    baseline_brier = float(np.mean((baseline_probability - actual_positive.astype(float)) ** 2))
    mae = float(np.mean(np.abs(expected - realized)))
    baseline_mae = float(np.mean(np.abs(realized)))
    brier_skill = float(1.0 - brier / baseline_brier) if baseline_brier > 0 else float("nan")
    mae_skill = float(1.0 - mae / baseline_mae) if baseline_mae > 0 else float("nan")
    coverage = float(np.mean((realized >= valid["lower_return"]) & (realized <= valid["upper_return"])))
    calibrated_coverage = abs(coverage - interval_level) <= 0.05
    if observations < minimum_rows:
        status = "Evidencia insuficiente"
    elif brier_skill > 0.0 and mae_skill > 0.0 and direction_accuracy >= baseline_accuracy and calibrated_coverage:
        status = "Ventaja predictiva limitada"
    else:
        status = "Sin ventaja predictiva comprobada"
    return {
        "observations": observations,
        "status": status,
        "direction_accuracy": direction_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "brier_score": brier,
        "baseline_brier_score": baseline_brier,
        "brier_skill": brier_skill,
        "mae": mae,
        "baseline_mae": baseline_mae,
        "mae_skill": mae_skill,
        "interval_coverage": coverage,
        "interval_level": float(interval_level),
    }


def _bias(probability: float, lower: float, upper: float) -> str:
    if probability >= upper:
        return "Sesgo alcista"
    if probability <= lower:
        return "Sesgo bajista"
    return "Sesgo neutral"


def _next_volatility(features: pd.DataFrame, settings: dict[str, Any]) -> float:
    fallback = float(features["volatility_20d"].dropna().iloc[-1])
    returns = features["return_1d"].dropna()
    minimum = int(settings["models"]["egarch"]["min_train_observations"])
    if len(returns) < minimum:
        return fallback
    try:
        model = EGARCHModel(max_iterations=int(settings["models"]["egarch"]["iterations"])).fit(returns)
        placeholder = pd.Series([np.nan], index=pd.DatetimeIndex([features.index.max() + pd.offsets.BDay(1)]))
        value = float(model.forecast_sequence(placeholder).iloc[0])
        return value if np.isfinite(value) and value > 0 else fallback
    except (ValueError, RuntimeError, FloatingPointError):
        return fallback


def build_next_session_forecast(
    features: pd.DataFrame,
    model_frame: pd.DataFrame,
    settings: dict[str, Any],
) -> ForecastResult:
    """Construye predicciones OOS y un pronóstico en vivo usando datos disponibles hasta t."""

    config = settings.get("forecast", {})
    feature_columns = list(config.get("features", DEFAULT_FEATURES))
    minimum_train = int(config.get("minimum_train_observations", 500))
    logistic_l2 = float(config.get("logistic_l2", 0.12))
    ridge_alpha = float(config.get("ridge_alpha", 30.0))
    interval_level = float(config.get("interval_level", 0.80))
    positive_threshold = float(config.get("positive_probability_threshold", 0.55))
    negative_threshold = float(config.get("negative_probability_threshold", 0.45))
    minimum_validation = int(config.get("minimum_validation_observations", 500))

    frame = features.copy().sort_index()
    target = frame["price"].shift(-1) / frame["price"] - 1.0
    target.name = "realized_return"
    outcome_dates = pd.Series(frame.index, index=frame.index).shift(-1)
    history_parts: list[pd.DataFrame] = []
    used_features: set[str] = set()
    splits = expanding_year_splits(
        frame.index,
        str(settings["backtest"]["train_start"]),
        int(settings["backtest"]["first_test_year"]),
        settings["backtest"].get("rolling_train_years"),
    )
    for train_index, test_index, _fold in splits:
        test_start = test_index.min()
        safe_train = train_index[outcome_dates.reindex(train_index).lt(test_start).fillna(False).to_numpy()]
        if len(safe_train) < minimum_train:
            continue
        probability, expected_return, baseline_probability, columns = _predict_models(
            frame.loc[safe_train],
            frame.loc[test_index],
            target,
            feature_columns,
            logistic_l2,
            ridge_alpha,
        )
        used_features.update(columns)
        part = pd.DataFrame(
            {
                "probability_positive": probability,
                "expected_return": expected_return,
                "baseline_probability": baseline_probability,
                "realized_return": target.reindex(test_index),
                "outcome_date": outcome_dates.reindex(test_index),
            },
            index=test_index,
        )
        history_parts.append(part)
    if not history_parts:
        raise ValueError("No se generaron pronósticos walk-forward para la próxima sesión.")
    history = pd.concat(history_parts).sort_index()

    next_annualized = model_frame["egarch_volatility_forecast"].shift(-1).reindex(history.index)
    next_annualized = next_annualized.fillna(frame["volatility_20d"].reindex(history.index))
    history["volatility_annualized"] = next_annualized
    history["volatility_daily"] = history["volatility_annualized"] / np.sqrt(252.0)
    z_score = float(norm.ppf((1.0 + interval_level) / 2.0))
    history["lower_return"] = history["expected_return"] - z_score * history["volatility_daily"]
    history["upper_return"] = history["expected_return"] + z_score * history["volatility_daily"]
    validation = _validation_metrics(history, interval_level, minimum_validation)

    latest_date = frame.index.max()
    final_train = frame.index[(frame.index >= pd.Timestamp(settings["backtest"]["train_start"])) & (frame.index < latest_date)]
    final_train = final_train[target.reindex(final_train).notna().to_numpy()]
    if len(final_train) < minimum_train:
        raise ValueError("No existe historia suficiente para el pronóstico de la próxima sesión.")
    probability, expected_return, baseline_probability, columns = _predict_models(
        frame.loc[final_train],
        frame.loc[[latest_date]],
        target,
        feature_columns,
        logistic_l2,
        ridge_alpha,
    )
    used_features.update(columns)
    probability_value = float(probability[0])
    expected_return_value = float(expected_return[0])
    annualized_volatility = _next_volatility(frame, settings)
    daily_volatility = annualized_volatility / np.sqrt(252.0)
    lower_return = expected_return_value - z_score * daily_volatility
    upper_return = expected_return_value + z_score * daily_volatility
    current_price = float(frame.loc[latest_date, "price"])
    current = {
        "as_of_date": latest_date.date().isoformat(),
        "horizon_sessions": 1,
        "bias": _bias(probability_value, negative_threshold, positive_threshold),
        "probability_positive": probability_value,
        "baseline_probability": float(baseline_probability),
        "expected_return": expected_return_value,
        "expected_price": current_price * (1.0 + expected_return_value),
        "lower_return": float(lower_return),
        "upper_return": float(upper_return),
        "lower_price": float(max(0.0, current_price * (1.0 + lower_return))),
        "upper_price": float(max(0.0, current_price * (1.0 + upper_return))),
        "volatility_annualized": annualized_volatility,
        "volatility_daily": float(daily_volatility),
        "interval_level": interval_level,
        "validation_status": validation["status"],
        "features_used": sorted(used_features),
    }
    return ForecastResult(history=history, current=current, validation=validation)
