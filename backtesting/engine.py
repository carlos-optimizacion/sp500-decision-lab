"""Backtest causal: señal del cierre t se aplica al retorno de t+1."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .metrics import drawdown_series, performance_metrics


@dataclass
class BacktestResult:
    daily: pd.DataFrame
    strategy_metrics: dict
    benchmark_metrics: dict
    annual_returns: pd.DataFrame


def run_backtest(
    frame: pd.DataFrame,
    transaction_cost_bps: float = 0.0,
    annual_periods: int = 252,
) -> BacktestResult:
    required = {"return_1d", "target_exposure"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas para backtest: {sorted(missing)}")

    daily = frame[["return_1d", "target_exposure"]].copy().sort_index()
    # La exposición decidida al cierre anterior es la ejecutada durante la sesión actual.
    daily["executed_exposure"] = daily["target_exposure"].shift(1).fillna(0).clip(0, 1)
    daily["turnover"] = daily["executed_exposure"].diff().abs().fillna(daily["executed_exposure"].abs())
    daily["transaction_cost"] = daily["turnover"] * float(transaction_cost_bps) / 10_000.0
    daily["strategy_return"] = daily["executed_exposure"] * daily["return_1d"] - daily["transaction_cost"]
    daily["benchmark_return"] = daily["return_1d"]
    valid = daily["return_1d"].notna()
    daily = daily.loc[valid]
    daily["strategy_equity"] = (1 + daily["strategy_return"]).cumprod()
    daily["benchmark_equity"] = (1 + daily["benchmark_return"]).cumprod()
    daily["strategy_drawdown"] = drawdown_series(daily["strategy_equity"])
    daily["benchmark_drawdown"] = drawdown_series(daily["benchmark_equity"])

    strategy_metrics = performance_metrics(daily["strategy_return"], daily["executed_exposure"], annual_periods)
    benchmark_metrics = performance_metrics(daily["benchmark_return"], None, annual_periods)
    strategy_annual = daily["strategy_return"].groupby(daily.index.year).apply(lambda values: (1 + values).prod() - 1)
    benchmark_annual = daily["benchmark_return"].groupby(daily.index.year).apply(lambda values: (1 + values).prod() - 1)
    annual = pd.concat(
        [strategy_annual.rename("DecisionLab"), benchmark_annual.rename("Buy & Hold")], axis=1
    )
    annual.index.name = "year"
    return BacktestResult(daily, strategy_metrics, benchmark_metrics, annual)

