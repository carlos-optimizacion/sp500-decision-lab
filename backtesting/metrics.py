"""Métricas homogéneas para estrategia y Buy & Hold."""

from __future__ import annotations

import numpy as np
import pandas as pd


def drawdown_series(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def _max_recovery_sessions(drawdown: pd.Series) -> int:
    longest = current = 0
    for value in drawdown.fillna(0).to_numpy():
        if value < -1e-12:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def performance_metrics(
    returns: pd.Series,
    exposure: pd.Series | None = None,
    annual_periods: int = 252,
) -> dict[str, float | int | str]:
    values = returns.dropna().astype(float)
    if values.empty:
        return {key: np.nan for key in ("cagr", "total_return", "volatility", "sharpe", "sortino", "max_drawdown", "calmar")}
    equity = (1.0 + values).cumprod()
    years = max(len(values) / annual_periods, 1 / annual_periods)
    total_return = float(equity.iloc[-1] - 1.0)
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0
    volatility = float(values.std(ddof=0) * np.sqrt(annual_periods))
    mean_annual = float(values.mean() * annual_periods)
    sharpe = mean_annual / volatility if volatility > 1e-12 else np.nan
    downside = values.clip(upper=0)
    downside_deviation = float(np.sqrt(np.mean(downside * downside)) * np.sqrt(annual_periods))
    sortino = mean_annual / downside_deviation if downside_deviation > 1e-12 else np.nan
    drawdown = drawdown_series(equity)
    maximum_drawdown = float(drawdown.min())
    calmar = cagr / abs(maximum_drawdown) if maximum_drawdown < -1e-12 else np.nan
    annual = values.groupby(values.index.year).apply(lambda series: (1 + series).prod() - 1)
    invested = exposure.reindex(values.index).fillna(1.0) > 1e-9 if exposure is not None else pd.Series(True, index=values.index)
    active_returns = values[invested]
    win_rate = float((active_returns > 0).mean()) if len(active_returns) else np.nan
    return {
        "cagr": cagr,
        "total_return": total_return,
        "volatility": volatility,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": maximum_drawdown,
        "calmar": float(calmar),
        "win_rate": win_rate,
        "time_invested": float(invested.mean()),
        "average_exposure": float(exposure.reindex(values.index).fillna(0).mean()) if exposure is not None else 1.0,
        "recovery_sessions": _max_recovery_sessions(drawdown),
        "best_year": int(annual.idxmax()),
        "best_year_return": float(annual.max()),
        "worst_year": int(annual.idxmin()),
        "worst_year_return": float(annual.min()),
        "observations": int(len(values)),
    }

