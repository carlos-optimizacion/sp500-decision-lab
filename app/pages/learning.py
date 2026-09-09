"""Modo de aprendizaje contextual con los valores visibles del último cierre."""

from __future__ import annotations

import streamlit as st

from app.components import hero
from core.analysis import AnalysisBundle


def render(bundle: AnalysisBundle) -> None:
    latest = bundle.decisions.iloc[-1]
    hero(
        "Aprender con el dato observado",
        "Modo aprendizaje",
        "Cada concepto se conecta con el último estado calculado. El objetivo es entender qué mide el sistema antes de interpretar un puntaje.",
    )
    concept = st.radio(
        "Elige un concepto",
        ["Retorno", "Volatilidad", "Drawdown", "VIX", "Kalman", "Régimen", "Opportunity Score", "Pronóstico t+1"],
        horizontal=True,
    )

    if concept == "Retorno":
        st.subheader("Retorno: cambio relativo del precio")
        st.latex(r"R_t = \frac{P_t}{P_{t-1}}-1")
        st.write(
            f"En el último cierre, el retorno diario de SPY fue {latest['return_1d']:.2%}. DecisionLab usa retornos de 1, 5, 20 y 60 sesiones para separar un movimiento diario del momentum persistente."
        )
    elif concept == "Volatilidad":
        st.subheader("Volatilidad: dispersión, no dirección")
        st.latex(r"\sigma_{anual}=\operatorname{std}(r_{1:t})\sqrt{252}")
        st.write(
            f"La volatilidad realizada a 20 sesiones fue {latest['volatility_20d']:.1%}; EGARCH estimó {latest['egarch_volatility_forecast']:.1%} anualizada para la siguiente sesión. Una cifra alta indica mayor amplitud probable, no necesariamente una caída."
        )
    elif concept == "Drawdown":
        st.subheader("Drawdown: pérdida desde el máximo previo")
        st.latex(r"DD_t=\frac{P_t-\max(P_1,\ldots,P_t)}{\max(P_1,\ldots,P_t)}")
        st.write(
            f"SPY se encuentra en un drawdown de {latest['drawdown']:.1%}. El backtest usa Maximum Drawdown para medir la peor caída acumulada y no confundir baja volatilidad diaria con bajo riesgo total."
        )
    elif concept == "VIX":
        st.subheader("VIX: volatilidad implícita esperada por el mercado")
        st.write(
            f"El último VIX disponible es {latest['vix']:.2f}, en el percentil {latest['vix_percentile']:.0f} de su ventana causal. DecisionLab combina nivel, cambio y percentil; no interpreta un umbral aislado como regla universal."
        )
    elif concept == "Kalman":
        st.subheader("Kalman: tendencia latente e innovación")
        st.latex(r"\nu_t=z_t-H\hat{x}_{t|t-1},\qquad NIS_t=\nu_t^TS_t^{-1}\nu_t")
        st.write(
            f"La tendencia filtrada es US$ {latest['kalman_trend']:,.2f}; NIS vale {latest['kalman_nis']:.2f} y la confianza Kalman {latest['kalman_confidence']:.1f}%. Un NIS persistentemente alejado de su escala esperada advierte que el modelo está explicando peor las observaciones."
        )
    elif concept == "Régimen":
        st.subheader("Régimen: distribución de estados, no etiqueta absoluta")
        st.write(
            f"El estado dominante es {latest['regime_label']}. Las probabilidades son Bull {latest['regime_Bull']:.1%}, Neutral {latest['regime_Neutral']:.1%}, Correction {latest['regime_Correction']:.1%} y Stress {latest['regime_Stress']:.1%}. Conservar la distribución muestra cuándo la clasificación es ambigua."
        )
    elif concept == "Opportunity Score":
        st.subheader("Opportunity Score: síntesis con guardas")
        st.latex(r"OS=\sum_i w_i s_i,\quad OS\in[0,100]")
        st.write(
            f"El Opportunity Score actual es {latest['opportunity_score']:.1f}; Risk Score {latest['risk_score']:.1f} y Confidence Score {latest['confidence_score']:.1f}. Si la confianza cae por debajo de 60, el motor impide una condición fuerte aunque Opportunity sea alto."
        )
    else:
        forecast = bundle.forecast
        validation = bundle.forecast_validation
        st.subheader("Pronóstico t+1: una distribución, no un precio seguro")
        st.latex(r"r_{t+1}=\mu_{t+1}+\sigma_{t+1}\varepsilon_{t+1}")
        st.write(
            f"Para la próxima sesión, el modelo estima una probabilidad positiva de {forecast['probability_positive']:.1%}, "
            f"un retorno central de {forecast['expected_return']:+.2%} y un rango del 80% entre "
            f"US$ {forecast['lower_price']:,.2f} y US$ {forecast['upper_price']:,.2f}. "
            f"La validación usa {validation['observations']:,} pronósticos fuera de muestra y su estado actual es: "
            f"{validation['status']}."
        )
        st.write(
            "El modelo direccional y el retorno esperado se estiman con variables conocidas al cierre. EGARCH aporta la "
            "volatilidad de la sesión siguiente. El retorno real de t+1 se utiliza después, únicamente para evaluar el pronóstico."
        )

    st.divider()
    st.subheader("Cómo leer la herramienta")
    st.markdown(
        """
1. Observa **Opportunity**, pero no lo leas solo.
2. Contrástalo con **Risk** y **Confidence**.
3. Revisa las probabilidades de régimen y los factores explicativos.
4. Comprueba el resultado **out-of-sample** frente a Buy & Hold.
5. Considera las limitaciones de datos y la incertidumbre antes de extraer conclusiones.
        """
    )
    with st.expander("Qué no hace este MVP"):
        st.markdown(
            "No ejecuta operaciones, no se conecta con brokers, no usa datos tick-by-tick, no ofrece asesoría personalizada y no presenta una frecuencia histórica como garantía futura."
        )
