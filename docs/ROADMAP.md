# Roadmap de validación

## Completado en MVP 2

- Repositorio modular y configuración central.
- Fuentes gratuitas EOD, validación y almacenamiento local.
- Feature engineering causal.
- Kalman, HMM, EGARCH y ChangeRisk.
- Tres scores explicables.
- Backtest con costos y validación walk-forward.
- Dashboard, ablación, aprendizaje y trazabilidad.
- Pruebas automatizadas y snapshot real.

## Completado en MVP 3

- Pronóstico probabilístico para la próxima sesión con validación temporal.
- Comparación contra referencias direccional y de retorno cero.
- Intervalo predictivo del 80% con volatilidad EGARCH `t+1`.
- Estado explícito cuando no se demuestra ventaja predictiva.
- Zoom y desplazamiento en series temporales.
- Velas OHLC ajustadas como vista opcional.

## Siguiente iteración recomendada

1. Añadir benchmarks de exposición y volatilidad equivalentes.
2. Comparar EGARCH contra GARCH mediante QLIKE out-of-sample; desactivar EGARCH si no mejora.
3. Añadir nested walk-forward para optimizar pesos sin tocar el período final reservado.
4. Integrar vintages ALFRED para CPI, desempleo y otras series revisables.
5. Evaluar UKF contra Kalman lineal; mantenerlo solo si mejora estabilidad o resultado fuera de muestra.
6. Medir calibración y persistencia del HMM entre folds.
7. Incorporar pruebas de estrés de costos, retraso de ejecución y datos faltantes.
8. Evaluar calibración, estabilidad y modelos alternativos para el pronóstico diario; conservarlos solo si superan las referencias fuera de muestra.

## Después de una baseline sólida

- TFT u otro modelo secuencial, siempre comparado fuera de muestra.
- FastAPI y base temporal si existe un consumidor distinto del dashboard.
- Ingestión intradía/WebSocket solo si el caso de uso lo justifica.
- Conector de broker únicamente en un proyecto separado, con controles regulatorios y operativos; nunca como parte de este MVP educativo.
