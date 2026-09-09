from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from app.charts import PLOT_CONFIG
from app.charts.figures import market_history_figure
from app.charts.theme import PANEL
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


def test_plot_navigation_is_disabled():
    assert PLOT_CONFIG["displayModeBar"] is False
    assert PLOT_CONFIG["scrollZoom"] is False
    assert PLOT_CONFIG["doubleClick"] is False


def test_market_history_uses_dark_locked_axes(market_frame):
    frame = build_features(market_frame)
    frame["kalman_trend"] = frame["price"]
    figure = market_history_figure(frame, "1Y")
    assert figure.layout.paper_bgcolor == PANEL
    assert figure.layout.plot_bgcolor == PANEL
    assert figure.layout.dragmode is False
    assert figure.layout.xaxis.fixedrange is True
    assert figure.layout.xaxis2.fixedrange is True
    assert figure.layout.yaxis.fixedrange is True
    assert figure.layout.yaxis2.fixedrange is True
