"""Variables técnicas y macro calculadas solo con información disponible hasta t."""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def rolling_percentile_last(series: pd.Series, window: int = 756, min_periods: int = 126) -> pd.Series:
    """Percentil causal del valor actual dentro de su ventana pasada, en 0–100."""

    values = series.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    for index, value in enumerate(values):
        if not np.isfinite(value):
            continue
        start = max(0, index - window + 1)
        sample = values[start : index + 1]
        sample = sample[np.isfinite(sample)]
        if len(sample) >= min_periods:
            result[index] = 100.0 * (np.count_nonzero(sample <= value) - 0.5) / len(sample)
    return pd.Series(result, index=series.index, name=f"{series.name}_percentile")


def rolling_zscore(series: pd.Series, window: int = 252, min_periods: int = 80) -> pd.Series:
    mean = series.rolling(window, min_periods=min_periods).mean()
    standard = series.rolling(window, min_periods=min_periods).std(ddof=0).replace(0, np.nan)
    return ((series - mean) / standard).clip(-8, 8)


def compute_drawdown(price: pd.Series) -> pd.Series:
    return price / price.cummax() - 1.0


def build_features(market: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    config = config or {}
    moving_averages = config.get("moving_averages", [20, 50, 200])
    return_windows = config.get("return_windows", [1, 5, 20, 60])
    volatility_windows = config.get("volatility_windows", [20, 60])
    percentile_window = int(config.get("percentile_window", 756))
    percentile_min_periods = int(config.get("percentile_min_periods", 126))

    frame = market.copy().sort_index()
    price = frame["Adj Close"].astype(float)
    frame["price"] = price

    for window in return_windows:
        frame[f"return_{window}d"] = price.pct_change(int(window), fill_method=None)
    frame["log_return_1d"] = np.log(price).diff()

    for window in moving_averages:
        frame[f"ma_{window}"] = price.rolling(int(window), min_periods=int(window)).mean()
    frame["distance_ma200"] = price / frame["ma_200"] - 1.0
    frame["ma20_vs_ma50"] = frame["ma_20"] / frame["ma_50"] - 1.0

    frame["momentum_20d"] = frame["return_20d"]
    frame["momentum_60d"] = frame["return_60d"]
    for window in volatility_windows:
        frame[f"volatility_{window}d"] = frame["log_return_1d"].rolling(
            int(window), min_periods=int(window)
        ).std(ddof=0) * np.sqrt(TRADING_DAYS)

    frame["drawdown"] = compute_drawdown(price)
    frame["vix_change_5d"] = frame["vix"].pct_change(5, fill_method=None)
    frame["vix_percentile"] = rolling_percentile_last(
        frame["vix"], percentile_window, percentile_min_periods
    )
    frame["vix_z_252d"] = rolling_zscore(frame["vix"], 252, 80)

    if {"macro_treasury_10y", "macro_treasury_2y"}.issubset(frame.columns):
        frame["yield_spread"] = frame["macro_treasury_10y"] - frame["macro_treasury_2y"]
        frame["yield_spread_z_252d"] = rolling_zscore(frame["yield_spread"], 252, 80)
    else:
        frame["yield_spread"] = np.nan
        frame["yield_spread_z_252d"] = np.nan

    if "macro_credit_spread" in frame:
        frame["credit_spread_percentile"] = rolling_percentile_last(
            frame["macro_credit_spread"], percentile_window, percentile_min_periods
        )
        frame["credit_spread_z_252d"] = rolling_zscore(frame["macro_credit_spread"], 252, 80)
    else:
        frame["credit_spread_percentile"] = np.nan
        frame["credit_spread_z_252d"] = np.nan

    if "macro_wti" in frame:
        frame["oil_return_20d"] = frame["macro_wti"].pct_change(20, fill_method=None)
    if "macro_dollar_index" in frame:
        frame["dollar_return_20d"] = frame["macro_dollar_index"].pct_change(20, fill_method=None)
    if "macro_cpi" in frame:
        frame["cpi_yoy_proxy"] = frame["macro_cpi"].pct_change(252, fill_method=None)
    if "macro_fed_funds" in frame:
        frame["fed_funds_change_60d"] = frame["macro_fed_funds"].diff(60)

    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame.attrs["causality"] = "Cada fila t usa únicamente observaciones con fecha de disponibilidad <= t."
    return frame

