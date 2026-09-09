"""Contratos de gráficos Plotly del dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .theme import BLUE, BLUE_LIGHT, GOLD, GRID, INK, MUTED, ORANGE, PALE, REGIME_COLORS, WHITE, axis, layout


def _range_start(index: pd.DatetimeIndex, range_key: str) -> pd.Timestamp:
    latest = index.max()
    offsets = {
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "5Y": pd.DateOffset(years=5),
        "10Y": pd.DateOffset(years=10),
    }
    return latest - offsets.get(range_key, pd.DateOffset(years=1))


def select_range(frame: pd.DataFrame, range_key: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame.loc[frame.index >= _range_start(frame.index, range_key)]


def _adjusted_ohlc(data: pd.DataFrame) -> pd.DataFrame:
    required = {"Open", "High", "Low", "Close", "price"}
    if not required.issubset(data.columns):
        return pd.DataFrame(index=data.index)
    factor = data["price"].div(data["Close"].replace(0, np.nan))
    adjusted = pd.DataFrame(index=data.index)
    for column in ("Open", "High", "Low", "Close"):
        adjusted[column] = data[column].mul(factor)
    return adjusted.replace([np.inf, -np.inf], np.nan)


def market_history_figure(
    frame: pd.DataFrame,
    range_key: str,
    log_scale: bool = False,
    price_view: str = "Línea",
) -> go.Figure:
    data = select_range(frame, range_key)
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.76, 0.24], vertical_spacing=0.07)
    use_candles = price_view == "Velas"
    adjusted = _adjusted_ohlc(data) if use_candles else pd.DataFrame(index=data.index)
    if use_candles and not adjusted.empty:
        figure.add_trace(
            go.Candlestick(
                x=adjusted.index,
                open=adjusted["Open"],
                high=adjusted["High"],
                low=adjusted["Low"],
                close=adjusted["Close"],
                name="SPY ajustado",
                increasing={"line": {"color": BLUE, "width": 1}, "fillcolor": BLUE_LIGHT},
                decreasing={"line": {"color": ORANGE, "width": 1}, "fillcolor": "#F7C9B4"},
                whiskerwidth=0.35,
            ),
            row=1,
            col=1,
        )
    else:
        figure.add_trace(
            go.Scatter(x=data.index, y=data["price"], name="SPY ajustado", mode="lines", line={"color": INK, "width": 2.4}),
            row=1,
            col=1,
        )
    series = [
        ("ma_20", "MA20", BLUE_LIGHT, 1.2, "dot"),
        ("ma_50", "MA50", BLUE, 1.3, "dash"),
        ("ma_200", "MA200", MUTED, 1.4, "dashdot"),
        ("kalman_trend", "Tendencia Kalman", GOLD, 2.0, None),
    ]
    for column, name, color, width, dash in series:
        if column in data:
            figure.add_trace(
                go.Scatter(x=data.index, y=data[column], name=name, mode="lines", line={"color": color, "width": width, "dash": dash}),
                row=1,
                col=1,
            )
    figure.add_trace(
        go.Scatter(
            x=data.index,
            y=data["drawdown"],
            name="Drawdown",
            mode="lines",
            line={"color": ORANGE, "width": 1.2},
            fill="tozeroy",
            fillcolor="rgba(229,122,68,0.16)",
        ),
        row=2,
        col=1,
    )
    figure.update_layout(**layout("Precio, tendencia y drawdown", f"SPY EOD ajustado · ventana {range_key}", 590))
    figure.update_yaxes(**axis("USD"), type="log" if log_scale else "linear", row=1, col=1)
    figure.update_yaxes(**axis("Drawdown", percent=True), row=2, col=1)
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB", row=2, col=1)
    figure.update_xaxes(rangeslider_visible=False, row=1, col=1)
    return figure


def score_gauge(value: float, title: str = "Opportunity Score") -> go.Figure:
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(value),
            number={"suffix": " / 100", "font": {"size": 34, "color": INK}},
            title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": INK}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": MUTED},
                "bar": {"color": BLUE, "thickness": 0.32},
                "bgcolor": WHITE,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "#F2F4F7"},
                    {"range": [40, 60], "color": "#E8ECF3"},
                    {"range": [60, 80], "color": "#DDE6FF"},
                    {"range": [80, 100], "color": "#CAD9FF"},
                ],
                "threshold": {"line": {"color": GOLD, "width": 3}, "thickness": 0.8, "value": 60},
            },
        )
    )
    figure.update_layout(height=300, margin={"l": 30, "r": 30, "t": 50, "b": 18}, paper_bgcolor=WHITE)
    return figure


def conditions_figure(row: pd.Series) -> go.Figure:
    names = ["Tendencia", "Momentum", "Volatilidad", "Riesgo global", "Liquidez/macro"]
    values = [
        row.get("score_trend", 50),
        row.get("score_momentum", 50),
        row.get("condition_volatility", 50),
        row.get("condition_global_risk", 50),
        row.get("condition_liquidity", 50),
    ]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker={"color": BLUE, "line": {"color": "#1647C7", "width": 1}},
            text=[f"{value:.0f}" for value in values],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f}/100<extra></extra>",
        )
    )
    figure.update_layout(**layout("Condiciones actuales", "Escala común: 100 = condición más favorable", 330))
    figure.update_xaxes(range=[0, 105], **axis("Puntaje"))
    figure.update_yaxes(autorange="reversed", showgrid=False, linecolor="#CBD1DB")
    figure.update_layout(showlegend=False, margin={"l": 118, "r": 38, "t": 76, "b": 42})
    return figure


def regime_probability_figure(row: pd.Series) -> go.Figure:
    names = ["Bull", "Neutral", "Correction", "Stress"]
    values = [100 * float(row.get(f"regime_{name}", 0.25)) for name in names]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker={"color": [REGIME_COLORS[name] for name in names], "line": {"color": INK, "width": 0.7}},
            text=[f"{value:.1f}%" for value in values],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(**layout("Régimen de mercado", "Probabilidades filtradas del HMM; no solo la etiqueta ganadora", 330))
    figure.update_xaxes(range=[0, 105], ticksuffix="%", **axis("Probabilidad"))
    figure.update_yaxes(autorange="reversed", showgrid=False, linecolor="#CBD1DB")
    figure.update_layout(showlegend=False, margin={"l": 98, "r": 42, "t": 76, "b": 42})
    return figure


def equity_figure(daily: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=daily.index, y=daily["strategy_equity"], name="DecisionLab", mode="lines", line={"color": BLUE, "width": 2.2}))
    figure.add_trace(go.Scatter(x=daily.index, y=daily["benchmark_equity"], name="Buy & Hold", mode="lines", line={"color": INK, "width": 1.7, "dash": "dash"}))
    figure.update_layout(**layout("Curva de capital fuera de muestra", "Base 1.00 · señal t ejecutada en t+1", 430))
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB")
    figure.update_yaxes(**axis("Crecimiento de US$1"))
    return figure


def drawdown_figure(daily: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=daily.index, y=daily["strategy_drawdown"], name="DecisionLab", mode="lines", line={"color": BLUE, "width": 2}))
    figure.add_trace(go.Scatter(x=daily.index, y=daily["benchmark_drawdown"], name="Buy & Hold", mode="lines", line={"color": ORANGE, "width": 1.7, "dash": "dash"}))
    figure.update_layout(**layout("Drawdown", "Caída desde el máximo acumulado de cada estrategia", 370))
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB")
    figure.update_yaxes(**axis("Drawdown", percent=True))
    return figure


def annual_returns_figure(annual: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Bar(x=annual.index.astype(str), y=annual["DecisionLab"], name="DecisionLab", marker={"color": BLUE, "line": {"color": "#1647C7", "width": 0.8}}))
    figure.add_trace(go.Bar(x=annual.index.astype(str), y=annual["Buy & Hold"], name="Buy & Hold", marker={"color": "#C5CAD3", "line": {"color": INK, "width": 0.8}}))
    figure.update_layout(**layout("Retornos por año", "Comparación out-of-sample; años parciales se muestran con lo disponible", 390), barmode="group")
    figure.update_xaxes(title="Año", showgrid=False, linecolor="#CBD1DB")
    return_axis = axis("Retorno", percent=True)
    return_axis.update({"zeroline": True, "zerolinecolor": INK, "zerolinewidth": 1})
    figure.update_yaxes(**return_axis)
    return figure


def kalman_figure(frame: pd.DataFrame, range_key: str) -> go.Figure:
    data = select_range(frame, range_key)
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.08)
    figure.add_trace(go.Scatter(x=data.index, y=data["price"], name="SPY", line={"color": INK, "width": 1.5}), row=1, col=1)
    figure.add_trace(go.Scatter(x=data.index, y=data["kalman_trend"], name="Tendencia Kalman", line={"color": GOLD, "width": 2.2}), row=1, col=1)
    figure.add_trace(go.Scatter(x=data.index, y=data["kalman_nis"], name="NIS", line={"color": BLUE, "width": 1.4}), row=2, col=1)
    figure.add_hline(y=3.84, line_dash="dash", line_color=ORANGE, annotation_text="Umbral χ² 95%", row=2, col=1)
    figure.update_layout(**layout("Filtro de Kalman", "Tendencia latente e innovación normalizada (NIS)", 530))
    figure.update_yaxes(**axis("USD"), row=1, col=1)
    figure.update_yaxes(**axis("NIS"), row=2, col=1)
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB", row=2, col=1)
    return figure


def regime_history_figure(frame: pd.DataFrame, range_key: str) -> go.Figure:
    data = select_range(frame.dropna(subset=["regime_Bull"]), range_key)
    figure = go.Figure()
    for name in ("Bull", "Neutral", "Correction", "Stress"):
        figure.add_trace(
            go.Scatter(
                x=data.index,
                y=data[f"regime_{name}"] * 100,
                name=name,
                mode="lines",
                stackgroup="one",
                line={"color": REGIME_COLORS[name], "width": 0.9},
                hovertemplate=f"{name}: %{{y:.1f}}%<extra></extra>",
            )
        )
    figure.update_layout(**layout("Probabilidades de régimen", "Distribución filtrada HMM; suma diaria = 100%", 400))
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB")
    figure.update_yaxes(range=[0, 100], ticksuffix="%", **axis("Probabilidad"))
    return figure


def volatility_figure(frame: pd.DataFrame, range_key: str) -> go.Figure:
    data = select_range(frame.dropna(subset=["egarch_volatility_forecast"]), range_key)
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=data.index, y=data["egarch_volatility_forecast"], name="EGARCH t+1", line={"color": BLUE, "width": 1.8}))
    figure.add_trace(go.Scatter(x=data.index, y=data["volatility_20d"], name="Realizada 20d", line={"color": MUTED, "width": 1.3, "dash": "dash"}))
    figure.update_layout(**layout("Volatilidad", "Pronóstico EGARCH anualizado frente a volatilidad realizada móvil", 390))
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB")
    figure.update_yaxes(**axis("Volatilidad anualizada", percent=True))
    return figure


def change_risk_figure(frame: pd.DataFrame, range_key: str) -> go.Figure:
    data = select_range(frame, range_key)
    figure = go.Figure(
        go.Scatter(
            x=data.index,
            y=data["change_risk"],
            name="ChangeRisk",
            mode="lines",
            line={"color": ORANGE, "width": 1.8},
            fill="tozeroy",
            fillcolor="rgba(229,122,68,0.13)",
        )
    )
    figure.add_hline(y=70, line_dash="dash", line_color=INK, annotation_text="Riesgo alto")
    figure.update_layout(**layout("Riesgo de cambio estructural", "Comparación causal: últimos 20 días vs. 80 días anteriores", 360))
    figure.update_xaxes(showgrid=False, linecolor="#CBD1DB")
    figure.update_yaxes(range=[0, 100], **axis("Riesgo 0–100"))
    return figure
