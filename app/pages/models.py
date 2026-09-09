"""Inspección de modelos y análisis de ablación."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.charts import INTERACTIVE_PLOT_CONFIG
from app.charts.figures import change_risk_figure, kalman_figure, regime_history_figure, volatility_figure
from app.components import hero, state_card
from backtesting.engine import run_backtest
from core.analysis import AnalysisBundle
from core.config import load_settings
from decision.engine import build_decision_frame
from models.change_point import offline_change_points


def _comparison(full: dict, candidate: dict) -> pd.DataFrame:
    rows = [
        ("CAGR", "cagr", "percent"),
        ("Sharpe", "sharpe", "number"),
        ("Sortino", "sortino", "number"),
        ("Maximum Drawdown", "max_drawdown", "percent"),
        ("Exposición promedio", "average_exposure", "percent"),
    ]
    records = []
    for label, key, kind in rows:
        formatter = (lambda value: f"{value:.1%}") if kind == "percent" else (lambda value: f"{value:.2f}")
        records.append({"Métrica": label, "Sistema completo": formatter(full[key]), "Selección actual": formatter(candidate[key])})
    return pd.DataFrame(records).set_index("Métrica")


def render(bundle: AnalysisBundle, range_key: str, transaction_cost_bps: float) -> None:
    hero(
        "Transparencia y ablación",
        "Modelos",
        "Inspecciona cada componente y desactívalo para medir cuánto aporta. Las probabilidades HMM son filtradas; EGARCH y HMM se reentrenan al inicio de cada fold anual.",
    )
    settings = load_settings()
    st.subheader("Análisis de ablación")
    controls = st.columns(4)
    with controls[0]:
        use_kalman = st.checkbox("Kalman", value=True)
    with controls[1]:
        use_hmm = st.checkbox("HMM", value=True)
    with controls[2]:
        use_egarch = st.checkbox("EGARCH", value=True)
    with controls[3]:
        use_change = st.checkbox("Change Point", value=True)
    flags = {"kalman": use_kalman, "hmm": use_hmm, "egarch": use_egarch, "change_point": use_change}

    oos_base = bundle.model_frame.reindex(bundle.decisions.index).copy()
    candidate = build_decision_frame(
        oos_base,
        settings["decision"],
        data_quality_score=oos_base.get(
            "fold_data_quality_score",
            pd.Series(float(bundle.manifest["quality"]["score"]), index=oos_base.index),
        ),
        walk_forward_score=bundle.decisions["confidence_walk_forward"],
        model_flags=flags,
    )
    full_backtest = run_backtest(bundle.decisions, transaction_cost_bps)
    candidate_backtest = run_backtest(candidate, transaction_cost_bps)
    latest = candidate.iloc[-1]
    state_card(
        "Estado con la selección actual",
        str(latest["decision_state"]),
        f"Opportunity {latest['opportunity_score']:.1f} · Risk {latest['risk_score']:.1f} · Confidence {latest['confidence_score']:.1f}",
    )
    st.dataframe(
        _comparison(full_backtest.strategy_metrics, candidate_backtest.strategy_metrics),
        width="stretch",
    )
    st.caption("La ablación recalcula scores y exposición sobre el mismo período out-of-sample; no reoptimiza umbrales.")

    kalman_tab, hmm_tab, egarch_tab, change_tab = st.tabs(["Kalman", "HMM", "EGARCH", "Change Point"])
    with kalman_tab:
        current = bundle.model_frame.dropna(subset=["kalman_trend"]).iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("Confianza Kalman", f"{current['kalman_confidence']:.1f}%")
        col2.metric("NIS", f"{current['kalman_nis']:.2f}")
        col3.metric("Innovación", f"{current['kalman_innovation']:.4f}")
        st.plotly_chart(kalman_figure(bundle.model_frame, range_key), width="stretch", config=INTERACTIVE_PLOT_CONFIG)
        st.markdown(
            "El filtro lineal estima nivel y pendiente del log-precio. UKF queda deliberadamente fuera de esta iteración: solo se incorporará si mejora esta referencia simple fuera de muestra."
        )
    with hmm_tab:
        current = bundle.model_frame.dropna(subset=["regime_Bull"]).iloc[-1]
        columns = st.columns(4)
        for column, name in zip(columns, ("Bull", "Neutral", "Correction", "Stress")):
            column.metric(name, f"{100 * current[f'regime_{name}']:.1f}%")
        st.plotly_chart(regime_history_figure(bundle.model_frame, range_key), width="stretch", config=INTERACTIVE_PLOT_CONFIG)
        st.caption("Los colores diferencian categorías; las cuatro áreas suman 100% cada día.")
    with egarch_tab:
        current = bundle.model_frame.dropna(subset=["egarch_volatility_forecast"]).iloc[-1]
        col1, col2 = st.columns(2)
        col1.metric("Volatilidad EGARCH t+1", f"{current['egarch_volatility_forecast']:.1%}")
        col2.metric("Percentil histórico", f"{current['egarch_volatility_percentile']:.1f}")
        st.plotly_chart(volatility_figure(bundle.model_frame, range_key), width="stretch", config=INTERACTIVE_PLOT_CONFIG)
        st.caption("La volatilidad de t se pronostica con shocks observados hasta t−1; el retorno de t actualiza recién el pronóstico siguiente.")
    with change_tab:
        current = bundle.model_frame.dropna(subset=["change_risk"]).iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("ChangeRisk", f"{current['change_risk']:.1f}")
        col2.metric("Cambio de media", f"{current['change_mean_shift']:.2f} σ")
        col3.metric("Cambio de volatilidad", f"{current['change_volatility_shift']:.2f}")
        st.plotly_chart(change_risk_figure(bundle.model_frame, range_key), width="stretch", config=INTERACTIVE_PLOT_CONFIG)
        st.caption("Este indicador causal alimenta el score. La segmentación binaria/PELT offline se reserva para diagnóstico visual y nunca alimenta retornos pasados.")
        with st.expander("Exploración retrospectiva PELT / Binary Segmentation"):
            method_label = st.selectbox("Método offline", ["PELT", "Binary Segmentation"])
            if st.button("Detectar rupturas históricas", key="offline-breaks"):
                method = "pelt" if method_label == "PELT" else "binary"
                points = offline_change_points(bundle.model_frame["return_1d"], method=method)
                st.write([point.date().isoformat() for point in points[-12:]])
                st.warning("Estas fechas se calculan mirando toda la serie y sirven solo para diagnóstico retrospectivo; no son señales de backtest.")
