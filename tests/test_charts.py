from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from app.charts.figures import market_history_figure
from data.features import build_features


def test_market_history_can_render_optional_adjusted_candles(market_frame):
    frame = build_features(market_frame)
    frame["kalman_trend"] = frame["price"]
    figure = market_history_figure(frame, "1Y", price_view="Velas")
    candles = [trace for trace in figure.data if isinstance(trace, go.Candlestick)]
    assert len(candles) == 1
    last = frame.loc[frame.index >= frame.index.max() - pd.DateOffset(years=1)].iloc[-1]
    assert abs(float(candles[0].close[-1]) - float(last["price"])) < 1e-9


def test_market_history_defaults_to_line(market_frame):
    frame = build_features(market_frame)
    frame["kalman_trend"] = frame["price"]
    figure = market_history_figure(frame, "1Y")
    assert not any(isinstance(trace, go.Candlestick) for trace in figure.data)
