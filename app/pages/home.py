"""Vista principal: estado actual, explicación y contexto temporal."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.charts import PLOT_CONFIG
from app.charts.figures import conditions_figure, market_history_figure, regime_probability_figure, score_gauge
from app.components import hero, soft_card, state_card
from core.analysis import AnalysisBundle
from decision.engine import explain_latest_signal


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _signed_pct(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}%}"


def _render_forecast(bundle: AnalysisBundle) -> None:
    forecast = bundle.forecast
    validation = bundle.forecast_validation
    if not forecast:
        st.info("El pronóstico de la próxima sesión todavía no está disponible.")
        return
    st.subheader("Pronóstico experimental para la próxima sesión")
    st.caption(
        "Estimación probabilística generada al cierre. No es un precio objetivo ni una instrucción de compra o venta."
    )
    columns = st.columns(5)
    cards = [
        ("Sesgo estimado", str(forecast["bias"]), "Umbrales probabilísticos 45% y 55%."),
        ("Probabilidad positiva", _pct(float(forecast["probability_positive"])), "Probabilidad de retorno mayor que cero."),
        ("Retorno esperado", _signed_pct(float(forecast["expected_return"])), "Cambio cierre a cierre estimado."),
        (
            "Rango probable 80%",
            f"US$ {float(forecast['lower_price']):,.2f} – {float(forecast['upper_price']):,.2f}",
            "El resultado puede quedar fuera del intervalo.",
        ),
        ("Volatilidad t+1", _pct(float(forecast["volatility_annualized"])), "Pronóstico EGARCH anualizado."),
    ]
    for column, (label, value, note) in zip(columns, cards):
        with column:
            soft_card(label, value, note)

    status = str(validation.get("status", forecast.get("validation_status", "Evidencia insuficiente")))
    observations = int(validation.get("observations", 0))
    accuracy = float(validation.get("direction_accuracy", float("nan")))
    baseline = float(validation.get("baseline_accuracy", float("nan")))
    coverage = float(validation.get("interval_coverage", float("nan")))
    summary = (
        f"{status}. Validación fuera de muestra: {observations:,} pronósticos; "
        f"acierto direccional {_pct(accuracy)} frente a {_pct(baseline)} de referencia; "
        f"cobertura del rango {_pct(coverage)}."
    )
    if status == "Ventaja predictiva limitada":
        st.info(summary)
    else:
        st.warning(summary)
    with st.expander("Cómo se valida este pronóstico"):
        metrics = pd.DataFrame(
            [
                ("Acierto direccional", _pct(accuracy)),
                ("Referencia direccional", _pct(baseline)),
                ("Brier del modelo", f"{float(validation.get('brier_score', float('nan'))):.4f}"),
                ("Brier de referencia", f"{float(validation.get('baseline_brier_score', float('nan'))):.4f}"),
                ("MAE del retorno", _pct(float(validation.get("mae", float("nan"))), 3)),
                ("MAE con retorno cero", _pct(float(validation.get("baseline_mae", float("nan"))), 3)),
                ("Cobertura del rango", _pct(coverage)),
            ],
            columns=["Control", "Resultado"],
        )
        st.dataframe(metrics, width="stretch", hide_index=True)
        st.caption(
            "Cada año se pronostica con coeficientes ajustados únicamente con años anteriores. "
            "El resultado de la sesión siguiente nunca entra en las variables de su propio pronóstico."
        )


def render(bundle: AnalysisBundle, range_key: str, log_scale: bool) -> None:
    latest = bundle.decisions.dropna(subset=["opportunity_score"]).iloc[-1]
    data_date = latest.name.strftime("%d %b %Y")
    hero(
        "Laboratorio cuantitativo · EOD",
        "S&P 500 Decision Lab",
        "Convierte datos históricos en estado, riesgo, régimen y validación. La salida expresa condiciones observadas; no promete predecir el mercado.",
    )
    state_card(
        f"Condición al cierre del {data_date}",
        str(latest["decision_state"]),
        f"Régimen dominante: {latest['regime_label']} · exposición teórica usada solo en el backtest: {_pct(float(latest['target_exposure']), 0)}",
    )

    left, middle, right = st.columns([1.35, 1, 1])
    with left:
        st.plotly_chart(score_gauge(float(latest["opportunity_score"])), width="stretch", config=PLOT_CONFIG)
    with middle:
        soft_card("Risk Score", f"{latest['risk_score']:.1f} / 100", "100 indica mayor presión de riesgo.")
        st.write("")
        soft_card("SPY ajustado", f"US$ {latest['price']:,.2f}", f"Último cierre disponible: {data_date}.")
    with right:
        soft_card("Confidence Score", f"{latest['confidence_score']:.1f} / 100", "Menos de 60 bloquea estados fuertes.")
        st.write("")
        soft_card("ChangeRisk", f"{latest['change_risk']:.1f} / 100", "Una ruptura elevada reduce la confianza.")

    _render_forecast(bundle)

    price_view = st.segmented_control(
        "Vista del precio",
        options=["Línea", "Velas"],
        default="Línea",
        help="Las velas son opcionales y utilizan OHLC ajustado para coincidir con las medias móviles.",
    ) or "Línea"
    st.plotly_chart(
        market_history_figure(bundle.model_frame, range_key, log_scale=log_scale, price_view=price_view),
        width="stretch",
        config=PLOT_CONFIG,
    )
    st.caption(
        "Fuente: SPY ajustado de Yahoo Finance. Cálculos propios EOD; el drawdown se mide desde el máximo acumulado. "
        "Use Ventana visual en la barra lateral para elegir el período mostrado."
    )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(conditions_figure(latest), width="stretch", config=PLOT_CONFIG)
    with right:
        st.plotly_chart(regime_probability_figure(latest), width="stretch", config=PLOT_CONFIG)

    st.subheader("Control del modelo")
    control_columns = st.columns(5)
    innovation_status = "Normal" if float(latest["kalman_nis"]) <= 3.84 else "Elevada"
    controls = [
        ("Confianza Kalman", f"{latest['kalman_confidence']:.1f}%"),
        ("Innovación", innovation_status),
        ("NIS", f"{latest['kalman_nis']:.2f}"),
        ("Cambio estructural", f"{latest['change_risk']:.1f}%"),
        ("Confianza total", f"{latest['confidence_score']:.1f}%"),
    ]
    for column, (label, value) in zip(control_columns, controls):
        with column:
            st.metric(label, value)
    st.caption("NIS se contrasta de forma orientativa con 3.84, percentil 95% de χ² con un grado de libertad.")

    st.subheader("Por qué cambió la condición")
    explanations = explain_latest_signal(bundle.decisions)
    positive, risks = st.columns(2)
    with positive:
        st.markdown("**Factores favorables**")
        for item in explanations["positive"]:
            st.markdown(f"- {item}")
    with risks:
        st.markdown("**Riesgos que limitan el puntaje**")
        for item in explanations["risks"]:
            st.markdown(f"- {item}")

    st.subheader("Probabilidad histórica estimada bajo condiciones similares")
    st.markdown(
        '<div class="section-note">Frecuencias descriptivas calculadas después de la señal; no son probabilidades absolutas del futuro.</div>',
        unsafe_allow_html=True,
    )
    horizons = bundle.horizons.copy()
    if not horizons.empty:
        view = pd.DataFrame(index=horizons.index)
        view["Frecuencia positiva"] = horizons["positive_frequency"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "—")
        view["Retorno mediano"] = horizons["median_return"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "—")
        view["Rango P25–P75"] = [
            f"{low:.1%} a {high:.1%}" if pd.notna(low) and pd.notna(high) else "—"
            for low, high in zip(horizons["p25_return"], horizons["p75_return"])
        ]
        view["Observaciones"] = horizons["observations"].astype(int)
        if "effective_observations" in horizons:
            view["N efectivo aprox."] = horizons["effective_observations"].astype(int)
        st.dataframe(view, width="stretch")
        condition = str(horizons["condition"].iloc[0])
        st.caption(
            f"Condición de similitud: {condition}. Los retornos se solapan; N efectivo aproxima cuánta evidencia independiente contiene la muestra."
        )

    st.markdown(
        '<div class="warning-strip"><b>Uso educativo.</b> No es asesoría financiera ni una instrucción de compra o venta. Los resultados históricos, incluso fuera de muestra, no garantizan resultados futuros.</div>',
        unsafe_allow_html=True,
    )
