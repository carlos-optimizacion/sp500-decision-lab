"""Comparación honesta DecisionLab vs Buy & Hold fuera de muestra."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.charts.figures import annual_returns_figure, drawdown_figure, equity_figure
from app.components import hero
from backtesting.engine import run_backtest
from core.analysis import AnalysisBundle


PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


def _fmt_percent(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.1%}"


def _fmt_number(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.2f}"


def _metric_table(strategy: dict, benchmark: dict) -> pd.DataFrame:
    definitions = [
        ("CAGR", "cagr", _fmt_percent),
        ("Retorno acumulado", "total_return", _fmt_percent),
        ("Volatilidad anualizada", "volatility", _fmt_percent),
        ("Sharpe", "sharpe", _fmt_number),
        ("Sortino", "sortino", _fmt_number),
        ("Maximum Drawdown", "max_drawdown", _fmt_percent),
        ("Calmar", "calmar", _fmt_number),
        ("Win rate diario invertido", "win_rate", _fmt_percent),
        ("Tiempo invertido", "time_invested", _fmt_percent),
        ("Exposición promedio", "average_exposure", _fmt_percent),
        ("Recuperación máxima (sesiones)", "recovery_sessions", lambda value: f"{int(value):,}"),
    ]
    return pd.DataFrame(
        {
            "Métrica": [label for label, _, _ in definitions],
            "DecisionLab": [formatter(strategy[key]) for _, key, formatter in definitions],
            "Buy & Hold": [formatter(benchmark[key]) for _, key, formatter in definitions],
        }
    ).set_index("Métrica")


def render(bundle: AnalysisBundle, transaction_cost_bps: float) -> None:
    hero(
        "Validación histórica · Walk-forward",
        "Backtesting fuera de muestra",
        "Compara la exposición teórica de DecisionLab con Buy & Hold. Cada señal se desplaza una sesión y cada año se estima con modelos entrenados únicamente en años anteriores.",
    )
    result = run_backtest(bundle.decisions, transaction_cost_bps=transaction_cost_bps)
    strategy = result.strategy_metrics
    benchmark = result.benchmark_metrics
    period = f"{result.daily.index.min().date()} — {result.daily.index.max().date()}"

    columns = st.columns(4)
    cards = [
        ("Sharpe", f"{strategy['sharpe']:.2f}", f"Buy & Hold {benchmark['sharpe']:.2f}"),
        ("Maximum Drawdown", _fmt_percent(strategy["max_drawdown"]), f"Buy & Hold {_fmt_percent(benchmark['max_drawdown'])}"),
        ("CAGR", _fmt_percent(strategy["cagr"]), f"Buy & Hold {_fmt_percent(benchmark['cagr'])}"),
        ("Exposición promedio", _fmt_percent(strategy["average_exposure"]), f"Costo {transaction_cost_bps:.0f} bps por cambio"),
    ]
    for column, (label, value, help_text) in zip(columns, cards):
        with column:
            st.metric(label, value, help=help_text)

    sharpe_improves = strategy["sharpe"] > benchmark["sharpe"]
    sortino_improves = strategy["sortino"] > benchmark["sortino"]
    drawdown_improves = abs(strategy["max_drawdown"]) < abs(benchmark["max_drawdown"])
    if sharpe_improves and sortino_improves and drawdown_improves:
        st.success("En esta ventana out-of-sample, el sistema mejora Sharpe, Sortino y Maximum Drawdown frente al benchmark.")
    elif drawdown_improves:
        st.info(
            "Resultado mixto: el sistema reduce el Maximum Drawdown, pero todavía no supera simultáneamente a Buy & Hold en Sharpe y Sortino. Es evidencia para iterar, no para declarar victoria."
        )
    else:
        st.warning("La configuración actual no mejora el riesgo ajustado ni el drawdown de forma suficiente; debe revisarse antes de considerar una siguiente fase.")
    st.caption(f"Período evaluado: {period} · Datos diarios EOD · Costos configurables: {transaction_cost_bps:.0f} bps.")

    st.plotly_chart(equity_figure(result.daily), width="stretch", config=PLOT_CONFIG, key="equity-main")
    st.plotly_chart(drawdown_figure(result.daily), width="stretch", config=PLOT_CONFIG, key="drawdown-main")
    st.plotly_chart(annual_returns_figure(result.annual_returns), width="stretch", config=PLOT_CONFIG, key="annual-main")

    st.subheader("Tabla de métricas")
    st.dataframe(_metric_table(strategy, benchmark), width="stretch")

    st.subheader("Inspección de crisis y años")
    years = [int(year) for year in sorted(result.daily.index.year.unique())]
    selected = st.selectbox("Período", ["Todo el out-of-sample", *years], index=0)
    detail = result.daily if isinstance(selected, str) else result.daily.loc[result.daily.index.year == selected]
    if not detail.empty:
        st.plotly_chart(equity_figure(detail.assign(
            strategy_equity=(1 + detail["strategy_return"]).cumprod(),
            benchmark_equity=(1 + detail["benchmark_return"]).cumprod(),
        )), width="stretch", config=PLOT_CONFIG, key="equity-detail")

    st.subheader("Resultados por fold")
    folds = bundle.fold_metrics.copy()
    display_columns = [
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "strategy_return",
        "benchmark_return",
        "strategy_sharpe",
        "benchmark_sharpe",
        "strategy_max_drawdown",
        "benchmark_max_drawdown",
        "hmm_converged",
        "egarch_converged",
    ]
    folds = folds[[column for column in display_columns if column in folds]]
    st.dataframe(
        folds.style.format(
            {
                "strategy_return": "{:.1%}",
                "benchmark_return": "{:.1%}",
                "strategy_sharpe": "{:.2f}",
                "benchmark_sharpe": "{:.2f}",
                "strategy_max_drawdown": "{:.1%}",
                "benchmark_max_drawdown": "{:.1%}",
            }
        ),
        width="stretch",
    )
    st.caption("Los parámetros y umbrales no se optimizan usando los años de prueba mostrados. El último año puede ser parcial.")
