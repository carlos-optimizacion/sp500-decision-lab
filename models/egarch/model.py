"""EGARCH(1,1) transparente con estimación por máxima verosimilitud."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


GAUSSIAN_ABS_MEAN = np.sqrt(2.0 / np.pi)
TRADING_DAYS = 252


@dataclass(frozen=True)
class EGARCHFit:
    omega: float
    alpha: float
    gamma: float
    beta: float
    converged: bool
    log_likelihood: float
    observations: int

    @property
    def parameters(self) -> np.ndarray:
        return np.array([self.omega, self.alpha, self.gamma, self.beta], dtype=float)


class EGARCHModel:
    """Modela log-varianza; gamma captura asimetría ante shocks negativos."""

    def __init__(self, max_iterations: int = 250):
        self.max_iterations = int(max_iterations)
        self.fit_: EGARCHFit | None = None
        self._train_returns: np.ndarray | None = None
        self._train_log_variance: np.ndarray | None = None

    @staticmethod
    def _variance_path(values_pct: np.ndarray, parameters: np.ndarray) -> np.ndarray:
        omega, alpha, gamma, beta = parameters
        values = np.clip(values_pct.astype(float), -25.0, 25.0)
        log_variance = np.empty(len(values), dtype=float)
        initial_variance = max(float(np.nanvar(values[: min(252, len(values))])), 1e-4)
        log_variance[0] = np.log(initial_variance)
        for index in range(1, len(values)):
            previous_variance = np.exp(np.clip(log_variance[index - 1], -12, 12))
            previous_shock = values[index - 1] / np.sqrt(previous_variance)
            log_variance[index] = (
                omega
                + beta * log_variance[index - 1]
                + alpha * (abs(previous_shock) - GAUSSIAN_ABS_MEAN)
                + gamma * previous_shock
            )
            log_variance[index] = np.clip(log_variance[index], -12, 12)
        return log_variance

    @classmethod
    def _negative_log_likelihood(cls, parameters: np.ndarray, values_pct: np.ndarray) -> float:
        log_variance = cls._variance_path(values_pct, parameters)
        variance = np.exp(log_variance)
        likelihood = -0.5 * (np.log(2 * np.pi) + log_variance + values_pct * values_pct / variance)
        value = -float(np.sum(likelihood[1:]))
        return value if np.isfinite(value) else 1e20

    def fit(self, returns: pd.Series | np.ndarray) -> "EGARCHModel":
        values = np.asarray(returns, dtype=float)
        values = values[np.isfinite(values)] * 100.0
        if len(values) < 120:
            raise ValueError("EGARCH necesita al menos 120 retornos válidos.")

        log_variance = np.log(max(float(np.var(values)), 1e-4))
        initial = np.array([(1 - 0.96) * log_variance, 0.12, -0.08, 0.96])
        bounds = [(-2.5, 2.5), (0.001, 0.9), (-0.9, 0.5), (0.60, 0.998)]
        result = minimize(
            self._negative_log_likelihood,
            initial,
            args=(values,),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": self.max_iterations, "ftol": 1e-9},
        )
        parameters = result.x if np.all(np.isfinite(result.x)) else initial
        path = self._variance_path(values, parameters)
        self.fit_ = EGARCHFit(
            omega=float(parameters[0]),
            alpha=float(parameters[1]),
            gamma=float(parameters[2]),
            beta=float(parameters[3]),
            converged=bool(result.success),
            log_likelihood=float(-self._negative_log_likelihood(parameters, values)),
            observations=int(len(values)),
        )
        self._train_returns = values
        self._train_log_variance = path
        return self

    def forecast_sequence(self, future_returns: pd.Series) -> pd.Series:
        """Pronóstico para t usa el shock observado hasta t-1; después incorpora retorno t."""

        if self.fit_ is None or self._train_returns is None or self._train_log_variance is None:
            raise RuntimeError("Primero ejecute fit().")
        omega, alpha, gamma, beta = self.fit_.parameters
        previous_log_variance = float(self._train_log_variance[-1])
        previous_shock = float(self._train_returns[-1] / np.sqrt(np.exp(previous_log_variance)))
        forecasts = np.full(len(future_returns), np.nan)
        for index, raw_value in enumerate(future_returns.to_numpy(dtype=float)):
            current_log_variance = (
                omega
                + beta * previous_log_variance
                + alpha * (abs(previous_shock) - GAUSSIAN_ABS_MEAN)
                + gamma * previous_shock
            )
            current_log_variance = float(np.clip(current_log_variance, -12, 12))
            current_variance = float(np.exp(current_log_variance))
            forecasts[index] = np.sqrt(current_variance) / 100.0 * np.sqrt(TRADING_DAYS)
            if np.isfinite(raw_value):
                current_pct = float(np.clip(raw_value * 100.0, -25, 25))
                previous_shock = current_pct / np.sqrt(current_variance)
                previous_log_variance = current_log_variance
        return pd.Series(forecasts, index=future_returns.index, name="egarch_volatility_forecast")

    def in_sample_volatility(self, index: pd.Index) -> pd.Series:
        if self._train_log_variance is None:
            raise RuntimeError("Primero ejecute fit().")
        volatility = np.sqrt(np.exp(self._train_log_variance)) / 100.0 * np.sqrt(TRADING_DAYS)
        return pd.Series(volatility, index=index, name="egarch_volatility")


def expanding_egarch_forecast(
    returns: pd.Series,
    first_forecast_year: int,
    max_iterations: int = 250,
) -> tuple[pd.Series, dict[int, EGARCHFit]]:
    forecasts = pd.Series(np.nan, index=returns.index, name="egarch_volatility_forecast")
    fits: dict[int, EGARCHFit] = {}
    years = sorted(year for year in returns.index.year.unique() if year >= first_forecast_year)
    for year in years:
        train = returns.loc[returns.index.year < year].dropna()
        test = returns.loc[returns.index.year == year]
        if len(train) < 120 or test.empty:
            continue
        model = EGARCHModel(max_iterations=max_iterations).fit(train)
        forecasts.loc[test.index] = model.forecast_sequence(test)
        fits[year] = model.fit_  # type: ignore[assignment]
    return forecasts, fits

