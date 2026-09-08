"""Trazabilidad de fuentes, cobertura y restricciones de calidad."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import hero
from core.analysis import AnalysisBundle


def render(bundle: AnalysisBundle) -> None:
    manifest = bundle.manifest
    quality = manifest["quality"]
    hero(
        "Trazabilidad",
        "Datos y calidad",
        "Muestra qué entró al modelo, hasta qué fecha, qué controles pasaron y qué limitaciones deben acompañar cualquier interpretación.",
    )
    columns = st.columns(4)
    columns[0].metric("Sesiones", f"{manifest['rows']:,}")
    columns[1].metric("Primera fecha", manifest["first_date"])
    columns[2].metric("Última fecha", manifest["last_date"])
    columns[3].metric("Quality Score", f"{quality['score']:.0f} / 100")

    status = "Apto para el pipeline" if quality["passed"] else "Pipeline bloqueado"
    if quality["passed"]:
        st.success(status)
    else:
        st.error(status)

    st.subheader("Hallazgos de control")
    issues = pd.DataFrame(quality.get("issues", []))
    if issues.empty:
        st.write("No se detectaron incidencias en los controles configurados.")
    else:
        issues = issues.rename(columns={"severity": "Severidad", "code": "Código", "message": "Detalle", "count": "Casos"})
        st.dataframe(issues, width="stretch", hide_index=True)

    st.subheader("Cobertura de variables de riesgo y macro")
    null_rates = quality.get("metrics", {}).get("macro_null_rates", {})
    coverage = pd.DataFrame(
        {
            "Variable": list(null_rates.keys()),
            "Cobertura": [1 - float(value) for value in null_rates.values()],
            "Faltantes": [float(value) for value in null_rates.values()],
        }
    )
    if not coverage.empty:
        st.dataframe(
            coverage.style.format({"Cobertura": "{:.1%}", "Faltantes": "{:.1%}"}),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Fuentes")
    source_table = pd.DataFrame(
        [{"Serie": name, "Fuente": url} for name, url in manifest.get("sources", {}).items()]
    )
    st.dataframe(
        source_table,
        column_config={"Fuente": st.column_config.LinkColumn("Fuente")},
        width="stretch",
        hide_index=True,
    )

    st.subheader("Reproducibilidad")
    st.code(
        f"experiment_id: {bundle.experiment['experiment_id']}\n"
        f"data_fingerprint_sha256: {manifest['fingerprint_sha256']}\n"
        f"generated_at_utc: {bundle.experiment['generated_at_utc']}",
        language="text",
    )
    st.warning(
        "Las series macro usan un rezago conservador de disponibilidad, pero el CSV estándar de FRED puede contener revisiones realizadas después de la fecha original. Por ello macro_vintage_safe permanece en false hasta integrar vintages de ALFRED."
    )
    st.caption("Zona temporal del mercado: America/New_York. Las fechas del dashboard representan sesiones EOD.")
