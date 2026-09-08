"""Filtro de Kalman local-lineal de nivel y tendencia para log-precios."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class KalmanConfig:
    process_level: float = 2e-6
    process_trend: float = 2e-8
    measurement_noise: float = 1.2e-4
    initial_covariance: float = 0.05


class KalmanTrendFilter:
    """Modelo de estado x_t=[nivel logarítmico, pendiente diaria]."""

    def __init__(self, config: KalmanConfig | None = None):
        self.config = config or KalmanConfig()

    def filter(self, price: pd.Series) -> pd.DataFrame:
        clean_price = price.astype(float)
        observations = np.log(clean_price.to_numpy())
        length = len(observations)
        outputs = np.full((length, 7), np.nan)

        finite = np.flatnonzero(np.isfinite(observations))
        if not len(finite):
            return pd.DataFrame(index=price.index)
        first = int(finite[0])
        state = np.array([observations[first], 0.0], dtype=float)
        covariance = np.eye(2) * self.config.initial_covariance
        transition = np.array([[1.0, 1.0], [0.0, 1.0]])
        observation = np.array([[1.0, 0.0]])
        process_noise = np.diag([self.config.process_level, self.config.process_trend])
        measurement_noise = float(self.config.measurement_noise)
        identity = np.eye(2)

        for index in range(first, length):
            predicted_state = transition @ state
            predicted_covariance = transition @ covariance @ transition.T + process_noise
            value = observations[index]
            if not np.isfinite(value):
                state = predicted_state
                covariance = predicted_covariance
                continue

            innovation = float(value - (observation @ predicted_state)[0])
            innovation_variance = float((observation @ predicted_covariance @ observation.T)[0, 0] + measurement_noise)
            gain = (predicted_covariance @ observation.T)[:, 0] / innovation_variance
            state = predicted_state + gain * innovation
            # Forma de Joseph: mantiene P simétrica/semidefinida positiva.
            kh = np.outer(gain, observation[0])
            covariance = (
                (identity - kh) @ predicted_covariance @ (identity - kh).T
                + np.outer(gain, gain) * measurement_noise
            )
            nis = innovation * innovation / innovation_variance
            outputs[index] = [
                np.exp(state[0]),
                state[1],
                innovation,
                innovation_variance,
                nis,
                np.sqrt(max(covariance[0, 0], 0.0)),
                gain[0],
            ]

        result = pd.DataFrame(
            outputs,
            index=price.index,
            columns=[
                "kalman_trend",
                "kalman_daily_slope",
                "kalman_innovation",
                "kalman_innovation_variance",
                "kalman_nis",
                "kalman_level_uncertainty",
                "kalman_gain",
            ],
        )
        result["kalman_slope_20d"] = np.expm1(result["kalman_daily_slope"] * 20).clip(-1, 2)
        nis_mean = result["kalman_nis"].rolling(20, min_periods=10).mean()
        nis_stability = (100.0 * (1.0 - ((nis_mean - 1.0).abs() / 3.0).clip(0, 1))).fillna(50.0)
        uncertainty_reference = result["kalman_level_uncertainty"].rolling(252, min_periods=40).median()
        uncertainty_ratio = result["kalman_level_uncertainty"] / uncertainty_reference.replace(0, np.nan)
        uncertainty_score = (100.0 - 35.0 * (uncertainty_ratio - 1.0).clip(lower=0)).clip(0, 100).fillna(50.0)
        result["kalman_confidence"] = (0.7 * nis_stability + 0.3 * uncertainty_score).clip(0, 100)
        return result

    def check_causality(self, price: pd.Series, split: int) -> bool:
        """Comprueba que cambiar el futuro no modifica el pasado filtrado."""

        baseline = self.filter(price).iloc[:split]
        altered = price.copy()
        altered.iloc[split:] = altered.iloc[split:] * 3.0
        comparison = self.filter(altered).iloc[:split]
        return bool(np.allclose(baseline.to_numpy(), comparison.to_numpy(), equal_nan=True))
