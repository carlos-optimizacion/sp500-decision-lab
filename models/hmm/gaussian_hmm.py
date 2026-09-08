"""HMM gaussiano diagonal con EM y probabilidades filtradas (no suavizadas)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.special import logsumexp


REGIME_NAMES = ("Bull", "Neutral", "Correction", "Stress")


@dataclass(frozen=True)
class HMMFitSummary:
    converged: bool
    iterations: int
    log_likelihood: float
    observations: int


class GaussianRegimeHMM:
    def __init__(
        self,
        n_states: int = 4,
        max_iterations: int = 80,
        tolerance: float = 1e-4,
        covariance_floor: float = 1e-4,
        transition_prior: float = 6.0,
        seed: int = 42,
    ):
        if n_states != 4:
            raise ValueError("Este MVP define exactamente cuatro regímenes interpretables.")
        self.n_states = n_states
        self.max_iterations = int(max_iterations)
        self.tolerance = float(tolerance)
        self.covariance_floor = float(covariance_floor)
        self.transition_prior = float(transition_prior)
        self.seed = int(seed)
        self.means_: np.ndarray | None = None
        self.variances_: np.ndarray | None = None
        self.transition_: np.ndarray | None = None
        self.initial_: np.ndarray | None = None
        self.center_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None
        self.state_names_: dict[int, str] | None = None
        self.summary_: HMMFitSummary | None = None

    def _emission_log_probability(self, values: np.ndarray) -> np.ndarray:
        if self.means_ is None or self.variances_ is None:
            raise RuntimeError("Modelo no ajustado.")
        differences = values[:, None, :] - self.means_[None, :, :]
        return -0.5 * np.sum(
            np.log(2 * np.pi * self.variances_[None, :, :])
            + differences * differences / self.variances_[None, :, :],
            axis=2,
        )

    def _forward_backward(self, emission: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        if self.transition_ is None or self.initial_ is None:
            raise RuntimeError("Modelo no inicializado.")
        observations = len(emission)
        log_transition = np.log(np.clip(self.transition_, 1e-15, 1))
        log_initial = np.log(np.clip(self.initial_, 1e-15, 1))
        forward = np.empty((observations, self.n_states))
        backward = np.zeros((observations, self.n_states))
        forward[0] = log_initial + emission[0]
        for time in range(1, observations):
            forward[time] = emission[time] + logsumexp(forward[time - 1][:, None] + log_transition, axis=0)
        log_likelihood = float(logsumexp(forward[-1]))
        for time in range(observations - 2, -1, -1):
            backward[time] = logsumexp(
                log_transition + emission[time + 1][None, :] + backward[time + 1][None, :],
                axis=1,
            )
        return forward, backward, log_likelihood

    def _initialize(self, values: np.ndarray) -> None:
        observations, dimensions = values.shape
        stress_axis = values[:, 0] - 0.35 * values[:, 1]
        cuts = np.quantile(stress_axis, [0.25, 0.50, 0.75])
        labels = np.digitize(stress_axis, cuts)
        global_variance = np.var(values, axis=0) + self.covariance_floor
        means = np.zeros((self.n_states, dimensions))
        variances = np.zeros_like(means)
        for state in range(self.n_states):
            group = values[labels == state]
            if len(group) < dimensions + 2:
                group = values
            means[state] = np.mean(group, axis=0)
            variances[state] = np.maximum(np.var(group, axis=0), self.covariance_floor)
        transition = np.ones((self.n_states, self.n_states))
        for left, right in zip(labels[:-1], labels[1:]):
            transition[left, right] += 1
        transition += np.eye(self.n_states) * self.transition_prior
        self.means_ = means
        self.variances_ = variances
        self.transition_ = transition / transition.sum(axis=1, keepdims=True)
        counts = np.bincount(labels[: min(60, observations)], minlength=self.n_states) + 1.0
        self.initial_ = counts / counts.sum()

    def fit(self, frame: pd.DataFrame | np.ndarray) -> "GaussianRegimeHMM":
        raw = np.asarray(frame, dtype=float)
        raw = raw[np.all(np.isfinite(raw), axis=1)]
        if len(raw) < 200:
            raise ValueError("HMM necesita al menos 200 observaciones completas.")
        self.center_ = np.mean(raw, axis=0)
        self.scale_ = np.std(raw, axis=0)
        self.scale_ = np.where(self.scale_ < 1e-8, 1.0, self.scale_)
        values = (raw - self.center_) / self.scale_
        self._initialize(values)

        previous = -np.inf
        converged = False
        iteration = 0
        for iteration in range(1, self.max_iterations + 1):
            emission = self._emission_log_probability(values)
            forward, backward, likelihood = self._forward_backward(emission)
            log_gamma = forward + backward - likelihood
            gamma = np.exp(log_gamma)
            gamma /= gamma.sum(axis=1, keepdims=True)

            log_transition = np.log(np.clip(self.transition_, 1e-15, 1))  # type: ignore[arg-type]
            xi_sum = np.zeros((self.n_states, self.n_states))
            for time in range(len(values) - 1):
                log_xi = (
                    forward[time][:, None]
                    + log_transition
                    + emission[time + 1][None, :]
                    + backward[time + 1][None, :]
                    - likelihood
                )
                xi_sum += np.exp(log_xi)

            weights = gamma.sum(axis=0) + 1e-12
            self.initial_ = (gamma[0] + 0.1) / (gamma[0].sum() + 0.1 * self.n_states)
            transition_counts = xi_sum + 0.05 + np.eye(self.n_states) * self.transition_prior
            self.transition_ = transition_counts / transition_counts.sum(axis=1, keepdims=True)
            self.means_ = (gamma.T @ values) / weights[:, None]
            differences = values[:, None, :] - self.means_[None, :, :]
            self.variances_ = np.sum(gamma[:, :, None] * differences * differences, axis=0) / weights[:, None]
            self.variances_ = np.maximum(self.variances_, self.covariance_floor)

            if np.isfinite(previous) and abs(likelihood - previous) <= self.tolerance * (1 + abs(previous)):
                converged = True
                break
            previous = likelihood

        self.state_names_ = self._name_states()
        self.summary_ = HMMFitSummary(converged, iteration, float(likelihood), len(values))
        return self

    def _name_states(self) -> dict[int, str]:
        if self.means_ is None or self.center_ is None or self.scale_ is None:
            raise RuntimeError("Modelo no ajustado.")
        raw_means = self.means_ * self.scale_[None, :] + self.center_[None, :]
        returns = raw_means[:, 0]
        volatility = raw_means[:, 1]
        score = returns - 0.35 * volatility
        bull = int(np.argmax(score))
        candidates = [state for state in range(self.n_states) if state != bull]
        stress = min(candidates, key=lambda state: returns[state] - 1.2 * volatility[state])
        remaining = [state for state in candidates if state != stress]
        correction = min(remaining, key=lambda state: score[state])
        neutral = next(state for state in remaining if state != correction)
        return {bull: "Bull", neutral: "Neutral", correction: "Correction", stress: "Stress"}

    def filter_probabilities(
        self,
        frame: pd.DataFrame | np.ndarray,
        index: pd.Index | None = None,
        initial_posterior: np.ndarray | None = None,
    ) -> pd.DataFrame:
        if any(value is None for value in (self.center_, self.scale_, self.transition_, self.initial_, self.state_names_)):
            raise RuntimeError("Primero ejecute fit().")
        raw = np.asarray(frame, dtype=float)
        values = (raw - self.center_) / self.scale_  # type: ignore[operator]
        valid = np.all(np.isfinite(values), axis=1)
        probabilities = np.zeros((len(values), self.n_states))
        prior = self.initial_.copy() if initial_posterior is None else initial_posterior @ self.transition_  # type: ignore[union-attr]
        for time, row in enumerate(values):
            if valid[time]:
                log_emission = self._emission_log_probability(row[None, :])[0]
                emission = np.exp(log_emission - np.max(log_emission))
                posterior = prior * emission
                total = posterior.sum()
                posterior = posterior / total if total > 0 and np.isfinite(total) else prior
            else:
                posterior = prior
            probabilities[time] = posterior
            prior = posterior @ self.transition_  # type: ignore[operator]

        output = pd.DataFrame(index=index if index is not None else pd.RangeIndex(len(values)))
        for state, name in self.state_names_.items():  # type: ignore[union-attr]
            output[f"regime_{name}"] = probabilities[:, state]
        output = output[[f"regime_{name}" for name in REGIME_NAMES]]
        output["regime_label"] = output.idxmax(axis=1).str.replace("regime_", "", regex=False)
        entropy = -(probabilities * np.log(np.clip(probabilities, 1e-15, 1))).sum(axis=1)
        output["regime_stability"] = 100.0 * (1.0 - entropy / np.log(self.n_states))
        output["regime_max_probability"] = probabilities.max(axis=1) * 100.0
        return output
