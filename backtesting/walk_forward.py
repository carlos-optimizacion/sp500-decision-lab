"""Validación expanding walk-forward con ajuste aislado en cada período."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterator

import numpy as np
import pandas as pd

from data.features import rolling_percentile_last
from decision.engine import build_decision_frame
from models.change_point import causal_change_risk
from models.egarch.model import EGARCHModel
from models.hmm.gaussian_hmm import GaussianRegimeHMM
from models.kalman import KalmanConfig, KalmanTrendFilter

from .engine import run_backtest


@dataclass(frozen=True)
class WalkForwardFold:
    test_year: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str


@dataclass
class WalkForwardResult:
    model_frame: pd.DataFrame
    decisions: pd.DataFrame
    fold_metrics: pd.DataFrame


def expanding_year_splits(
    index: pd.DatetimeIndex,
    train_start: str = "2016-01-01",
    first_test_year: int = 2020,
    rolling_train_years: int | None = None,
) -> Iterator[tuple[pd.DatetimeIndex, pd.DatetimeIndex, WalkForwardFold]]:
    eligible = index[index >= pd.Timestamp(train_start)]
    if eligible.empty:
        return
    for year in sorted(int(value) for value in eligible.year.unique() if value >= first_test_year):
        test = eligible[eligible.year == year]
        if test.empty:
            continue
        if rolling_train_years:
            lower = pd.Timestamp(year=year - rolling_train_years, month=1, day=1)
        else:
            lower = pd.Timestamp(train_start)
        train = eligible[(eligible < test.min()) & (eligible >= lower)]
        if train.empty:
            continue
        fold = WalkForwardFold(
            test_year=year,
            train_start=train.min().date().isoformat(),
            train_end=train.max().date().isoformat(),
            test_start=test.min().date().isoformat(),
            test_end=test.max().date().isoformat(),
        )
        yield train, test, fold


def _prior_validation_score(decisions: list[pd.DataFrame], transaction_cost_bps: float) -> float:
    if not decisions:
        return 50.0
    history = pd.concat(decisions).sort_index()
    result = run_backtest(history, transaction_cost_bps)
    strategy = result.strategy_metrics
    benchmark = result.benchmark_metrics
    sharpe_delta = float(strategy["sharpe"] - benchmark["sharpe"])
    drawdown_delta = float(abs(benchmark["max_drawdown"]) - abs(strategy["max_drawdown"]))
    sortino_delta = float(strategy["sortino"] - benchmark["sortino"])
    score = 50 + 18 * np.tanh(sharpe_delta) + 18 * np.tanh(drawdown_delta / 0.12) + 9 * np.tanh(sortino_delta)
    return float(np.clip(score, 20, 90))


def _training_percentile(reference: pd.Series, forecast: pd.Series) -> pd.Series:
    reference_values = reference.dropna().tail(756).to_numpy(dtype=float)
    output = []
    history = list(reference_values)
    for value in forecast.to_numpy(dtype=float):
        sample = np.asarray(history[-756:], dtype=float)
        sample = sample[np.isfinite(sample)]
        if np.isfinite(value) and len(sample):
            output.append(100.0 * (np.count_nonzero(sample <= value) - 0.5) / len(sample))
            history.append(float(value))
        else:
            output.append(np.nan)
    return pd.Series(output, index=forecast.index, name="egarch_volatility_percentile")


def _select_hmm_features(frame: pd.DataFrame, requested: list[str], train_index: pd.Index) -> list[str]:
    selected = []
    for column in requested:
        if column in frame and frame.loc[train_index, column].notna().sum() >= 200:
            selected.append(column)
    if len(selected) < 3:
        fallback = [column for column in ("return_1d", "volatility_20d", "vix_z_252d", "kalman_slope_20d") if column in frame]
        selected = list(dict.fromkeys(selected + fallback))
    return selected


def _point_in_time_quality(frame: pd.DataFrame) -> float:
    """Calidad observable al cierre del train; no usa cobertura de años futuros."""

    score = 100.0
    core = [column for column in ("Open", "High", "Low", "Close", "Adj Close", "Volume", "vix") if column in frame]
    if frame.index.duplicated().any() or not frame.index.is_monotonic_increasing:
        score -= 35
    if core and float(frame[core].isna().any(axis=1).mean()) > 0.01:
        score -= 35
    macro = [column for column in frame if column.startswith("macro_")]
    if any(float(frame[column].isna().mean()) > 0.35 for column in macro):
        score -= 8
    return float(np.clip(score, 0, 100))


def run_walk_forward(
    features: pd.DataFrame,
    settings: dict[str, Any],
    data_quality_score: float,
    model_flags: dict[str, bool] | None = None,
) -> WalkForwardResult:
    flags = {"kalman": True, "hmm": True, "egarch": True, "change_point": True, **(model_flags or {})}
    model_config = settings["models"]
    backtest_config = settings["backtest"]
    frame = features.copy().sort_index()

    kalman_settings = model_config["kalman"]
    kalman = KalmanTrendFilter(KalmanConfig(**kalman_settings))
    frame = frame.join(kalman.filter(frame["price"]))
    change_settings = model_config["change_point"]
    frame = frame.join(
        causal_change_risk(
            frame["return_1d"],
            int(change_settings["recent_window"]),
            int(change_settings["baseline_window"]),
        )
    )

    decision_parts: list[pd.DataFrame] = []
    model_parts: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []
    transaction_cost = float(backtest_config["transaction_cost_bps"])
    splits = expanding_year_splits(
        frame.index,
        str(backtest_config["train_start"]),
        int(backtest_config["first_test_year"]),
        backtest_config.get("rolling_train_years"),
    )

    for train_index, test_index, fold in splits:
        test_frame = frame.loc[test_index].copy()
        hmm_converged = False
        egarch_converged = False

        if flags["hmm"]:
            hmm_settings = model_config["hmm"]
            columns = _select_hmm_features(frame, list(hmm_settings["features"]), train_index)
            train_complete = frame.loc[train_index, columns].dropna()
            if len(train_complete) >= 200:
                hmm = GaussianRegimeHMM(
                    n_states=int(hmm_settings["states"]),
                    max_iterations=int(hmm_settings["iterations"]),
                    tolerance=float(hmm_settings["tolerance"]),
                    covariance_floor=float(hmm_settings["covariance_floor"]),
                    transition_prior=float(hmm_settings["transition_prior"]),
                    seed=int(settings["project"]["seed"]),
                ).fit(train_complete)
                train_probabilities = hmm.filter_probabilities(frame.loc[train_index, columns], train_index)
                last_named = train_probabilities.iloc[-1]
                initial_state = np.array(
                    [last_named[f"regime_{hmm.state_names_[state]}"] for state in range(hmm.n_states)]
                )
                probabilities = hmm.filter_probabilities(
                    test_frame[columns], test_index, initial_posterior=initial_state
                )
                test_frame = test_frame.join(probabilities)
                hmm_converged = bool(hmm.summary_ and hmm.summary_.converged)
        if "regime_Bull" not in test_frame:
            for name in ("Bull", "Neutral", "Correction", "Stress"):
                test_frame[f"regime_{name}"] = 0.25
            test_frame["regime_label"] = "Neutral"
            test_frame["regime_stability"] = 0.0
            test_frame["regime_max_probability"] = 25.0

        if flags["egarch"]:
            egarch_settings = model_config["egarch"]
            train_returns = frame.loc[train_index, "return_1d"].dropna()
            if len(train_returns) >= int(egarch_settings["min_train_observations"]):
                egarch = EGARCHModel(max_iterations=int(egarch_settings["iterations"])).fit(train_returns)
                forecast = egarch.forecast_sequence(test_frame["return_1d"])
                test_frame["egarch_volatility_forecast"] = forecast
                test_frame["egarch_volatility_percentile"] = _training_percentile(
                    frame.loc[train_index, "volatility_20d"], forecast
                )
                egarch_converged = bool(egarch.fit_ and egarch.fit_.converged)
        if "egarch_volatility_percentile" not in test_frame:
            test_frame["egarch_volatility_forecast"] = test_frame["volatility_20d"]
            test_frame["egarch_volatility_percentile"] = rolling_percentile_last(
                pd.concat([frame.loc[train_index, "volatility_20d"], test_frame["volatility_20d"]]),
                window=756,
                min_periods=126,
            ).reindex(test_index)

        convergence_scores = []
        if flags["hmm"]:
            convergence_scores.append(100.0 if hmm_converged else 55.0)
        if flags["egarch"]:
            convergence_scores.append(100.0 if egarch_converged else 55.0)
        test_frame["model_fit_confidence"] = float(np.mean(convergence_scores)) if convergence_scores else 70.0

        prior_score = _prior_validation_score(decision_parts, transaction_cost)
        fold_quality_score = _point_in_time_quality(frame.loc[train_index])
        test_frame["fold_data_quality_score"] = fold_quality_score
        decisions = build_decision_frame(
            test_frame,
            settings["decision"],
            data_quality_score=test_frame["fold_data_quality_score"],
            walk_forward_score=prior_score,
            model_flags=flags,
        )
        decision_parts.append(decisions)
        model_parts.append(test_frame)
        fold_backtest = run_backtest(decisions, transaction_cost, int(backtest_config["annual_periods"]))
        rows.append(
            {
                **asdict(fold),
                "train_observations": int(len(train_index)),
                "test_observations": int(len(test_index)),
                "hmm_converged": hmm_converged,
                "egarch_converged": egarch_converged,
                "prior_validation_score": prior_score,
                "point_in_time_quality_score": fold_quality_score,
                "strategy_return": fold_backtest.strategy_metrics["total_return"],
                "benchmark_return": fold_backtest.benchmark_metrics["total_return"],
                "strategy_sharpe": fold_backtest.strategy_metrics["sharpe"],
                "benchmark_sharpe": fold_backtest.benchmark_metrics["sharpe"],
                "strategy_max_drawdown": fold_backtest.strategy_metrics["max_drawdown"],
                "benchmark_max_drawdown": fold_backtest.benchmark_metrics["max_drawdown"],
                "mean_opportunity": float(decisions["opportunity_score"].mean()),
                "mean_risk": float(decisions["risk_score"].mean()),
                "mean_confidence": float(decisions["confidence_score"].mean()),
            }
        )

    if not decision_parts:
        raise ValueError("No se generaron folds walk-forward. Revise fechas e historia mínima.")
    oos_model_frame = pd.concat(model_parts).sort_index()
    model_frame = frame.copy()
    for column in oos_model_frame.columns:
        if column not in model_frame.columns:
            model_frame[column] = oos_model_frame[column].reindex(model_frame.index)
    decisions = pd.concat(decision_parts).sort_index()
    fold_metrics = pd.DataFrame(rows).set_index("test_year")
    return WalkForwardResult(model_frame, decisions, fold_metrics)
