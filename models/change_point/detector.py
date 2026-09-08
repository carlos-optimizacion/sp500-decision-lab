"""Riesgo de ruptura causal y segmentación binaria para exploración histórica."""

from __future__ import annotations

import numpy as np
import pandas as pd


def causal_change_risk(
    returns: pd.Series,
    recent_window: int = 20,
    baseline_window: int = 80,
) -> pd.DataFrame:
    """Compara ventana reciente con una base estrictamente anterior; no mira el futuro."""

    recent_mean = returns.rolling(recent_window, min_periods=recent_window).mean()
    recent_std = returns.rolling(recent_window, min_periods=recent_window).std(ddof=0)
    baseline = returns.shift(recent_window)
    baseline_mean = baseline.rolling(baseline_window, min_periods=baseline_window).mean()
    baseline_std = baseline.rolling(baseline_window, min_periods=baseline_window).std(ddof=0)
    scale = baseline_std.replace(0, np.nan)
    mean_shift = ((recent_mean - baseline_mean).abs() / scale).clip(0, 6)
    volatility_shift = (np.log((recent_std + 1e-8) / (baseline_std + 1e-8)).abs()).clip(0, 3)
    # 1.5 desviaciones en media o duplicar la volatilidad ya elevan el riesgo.
    raw = 0.62 * (mean_shift / 1.5) + 0.38 * (volatility_shift / np.log(2))
    risk = (100.0 * (1.0 - np.exp(-raw))).clip(0, 100)
    return pd.DataFrame(
        {
            "change_mean_shift": mean_shift,
            "change_volatility_shift": volatility_shift,
            "change_risk": risk,
        },
        index=returns.index,
    )


def _segment_sse(prefix: np.ndarray, prefix_sq: np.ndarray, start: int, end: int) -> float:
    count = end - start
    if count <= 0:
        return 0.0
    total = prefix[end] - prefix[start]
    total_sq = prefix_sq[end] - prefix_sq[start]
    return float(max(total_sq - total * total / count, 0.0))


def binary_segmentation(
    series: pd.Series,
    max_breaks: int = 12,
    min_segment: int = 40,
    improvement_threshold: float = 0.08,
) -> list[pd.Timestamp]:
    """Segmentación offline para la página Modelos; nunca alimenta el backtest."""

    clean = series.dropna()
    values = clean.to_numpy(dtype=float)
    if len(values) < 2 * min_segment:
        return []
    prefix = np.concatenate([[0.0], np.cumsum(values)])
    prefix_sq = np.concatenate([[0.0], np.cumsum(values * values)])
    segments: list[tuple[int, int]] = [(0, len(values))]
    breaks: list[int] = []
    while len(breaks) < max_breaks:
        best: tuple[float, int, tuple[int, int]] | None = None
        for start, end in segments:
            if end - start < 2 * min_segment:
                continue
            parent_sse = _segment_sse(prefix, prefix_sq, start, end)
            if parent_sse <= 0:
                continue
            for candidate in range(start + min_segment, end - min_segment + 1):
                child_sse = _segment_sse(prefix, prefix_sq, start, candidate) + _segment_sse(
                    prefix, prefix_sq, candidate, end
                )
                gain = (parent_sse - child_sse) / parent_sse
                if best is None or gain > best[0]:
                    best = (gain, candidate, (start, end))
        if best is None or best[0] < improvement_threshold:
            break
        _, candidate, parent = best
        segments.remove(parent)
        segments.extend([(parent[0], candidate), (candidate, parent[1])])
        breaks.append(candidate)
    return sorted(pd.Timestamp(clean.index[position]) for position in breaks)


def offline_change_points(
    series: pd.Series,
    method: str = "pelt",
    max_breaks: int = 12,
    min_segment: int = 40,
    penalty: float | None = None,
) -> list[pd.Timestamp]:
    """PELT/BinSeg para explicación retrospectiva; la salida no debe entrar al backtest."""

    clean = series.dropna()
    if method not in {"pelt", "binary"}:
        raise ValueError("method debe ser 'pelt' o 'binary'.")
    try:
        import ruptures as rpt
    except (ImportError, ModuleNotFoundError):
        if method == "binary":
            return binary_segmentation(clean, max_breaks=max_breaks, min_segment=min_segment)
        raise RuntimeError("PELT requiere instalar ruptures.")

    signal = clean.to_numpy(dtype=float).reshape(-1, 1)
    if method == "pelt":
        selected_penalty = float(penalty) if penalty is not None else float(3.0 * np.log(max(len(signal), 2)))
        endpoints = rpt.Pelt(model="rbf", min_size=min_segment, jump=2).fit(signal).predict(pen=selected_penalty)
    else:
        possible = max(0, min(max_breaks, len(signal) // min_segment - 1))
        if possible == 0:
            return []
        endpoints = rpt.Binseg(model="l2", min_size=min_segment, jump=2).fit(signal).predict(n_bkps=possible)
    positions = [endpoint for endpoint in endpoints if endpoint < len(clean)]
    return [pd.Timestamp(clean.index[position]) for position in positions]
