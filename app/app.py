"""Aplicación Streamlit multipágina controlada desde un único entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components import inject_style
from app.pages import backtesting, data_quality, home, learning, models
from core.analysis import AnalysisBundle, build_analysis, load_snapshot
from core.config import load_settings


st.set_page_config(
    page_title="S&P 500 Decision Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


BUNDLE_CACHE_SCHEMA_VERSION = "0.3.0"


@st.cache_data(ttl=86_400, show_spinner=False)
def _load_bundle(cache_schema_version: str) -> AnalysisBundle:
    """Carga el snapshot con una clave que cambia cuando evoluciona su esquema."""

    del cache_schema_version
    return load_snapshot()


def _sidebar(bundle: AnalysisBundle) -> tuple[str, str, bool, float]:
    settings = load_settings()
    with st.sidebar:
        st.markdown("## Decision Lab")
        st.caption("MVP 3 · Datos EOD · Costo tecnológico US$0")
        page = st.radio(
            "Navegación",
            ["Estado actual", "Backtesting", "Modelos", "Aprendizaje", "Datos y calidad"],
            label_visibility="collapsed",
        )
        st.divider()
        range_key = st.segmented_control(
            "Ventana visual",
            options=["1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"],
            default="1Y",
        ) or "1Y"
        log_scale = st.checkbox("Escala logarítmica del precio", value=False)
        transaction_cost = st.slider(
            "Costo por cambio de exposición (bps)",
            min_value=0,
            max_value=25,
            value=int(settings["backtest"]["transaction_cost_bps"]),
            step=1,
            help="Un basis point equivale a 0.01%. Se aplica sobre el turnover.",
        )
        st.divider()
        last_date = bundle.manifest["last_date"]
        st.markdown(f"**Datos hasta:** {last_date}")
        st.caption(f"Experimento: {bundle.experiment['experiment_id']}")
        if st.button("Actualizar fuentes", width="stretch"):
            with st.spinner("Descargando, validando y reentrenando por folds…"):
                build_analysis(refresh=True)
                _load_bundle.clear()
            st.rerun()
        st.caption("La actualización puede tardar aproximadamente 1–2 minutos.")
    return page, str(range_key), log_scale, float(transaction_cost)


def main() -> None:
    inject_style()
    try:
        with st.spinner("Cargando snapshot validado…"):
            bundle = _load_bundle(BUNDLE_CACHE_SCHEMA_VERSION)
    except Exception as exc:
        st.error("No fue posible cargar el snapshot ni actualizar las fuentes.")
        st.exception(exc)
        st.info("Ejecute `python scripts/build_snapshot.py --refresh` y vuelva a abrir la aplicación.")
        return

    page, range_key, log_scale, transaction_cost = _sidebar(bundle)
    if page == "Estado actual":
        home.render(bundle, range_key, log_scale)
    elif page == "Backtesting":
        backtesting.render(bundle, transaction_cost)
    elif page == "Modelos":
        models.render(bundle, range_key, transaction_cost)
    elif page == "Aprendizaje":
        learning.render(bundle)
    else:
        data_quality.render(bundle)


if __name__ == "__main__":
    main()
