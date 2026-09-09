# Changelog

## 0.3.0 — 2026-09-09

- Pronóstico probabilístico experimental para la próxima sesión.
- Probabilidad positiva, retorno esperado, rango del 80% y volatilidad EGARCH `t+1`.
- Validación expanding walk-forward contra referencias direccional y de retorno cero.
- Estado explícito cuando no existe ventaja predictiva comprobada.
- Selector de precio con línea predeterminada y velas ajustadas opcionales.
- Zoom, desplazamiento y restauración en gráficos temporales.
- Cuatro pruebas nuevas para pronóstico causal y gráficos de velas.

## 0.2.0 — 2026-09-08

- Primera versión funcional del MVP 2.
- Pipeline gratuito SPY/SPX, Cboe VIX y FRED.
- Validación, feature store, Kalman, HMM, EGARCH y ChangeRisk.
- Opportunity, Risk y Confidence Scores.
- Backtest y walk-forward anual 2020–2026 YTD.
- Dashboard Streamlit de cinco vistas.
- Snapshots CSV/Parquet, DuckDB y registro de experimentos.
- Suite inicial de 12 pruebas.
