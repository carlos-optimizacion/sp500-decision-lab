# Informe de validación del snapshot

## Evaluación general: compartir con salvedades

El MVP es funcional, reproducible y metodológicamente apto para aprendizaje y experimentación. La baseline reduce riesgo absoluto, pero aún no demuestra una ventaja global ajustada por riesgo. No debe utilizarse para tomar decisiones financieras reales.

## Cobertura

- Fecha de corte: 9 de septiembre de 2026.
- Mercado: 3,190 sesiones, del 2 de enero de 2014 al 9 de septiembre de 2026.
- Walk-forward: 1,680 sesiones de test, de 2020 a 2026 YTD.
- Folds: siete; HMM y EGARCH convergieron en los siete.
- Duplicados de fecha: 0.
- Filas con OHLC faltante: 0.
- Precios no positivos: 0.
- Quality Score: 92/100.

## Incidencia de datos

La serie `BAMLH0A0HYM2` tiene 23.6% de cobertura sobre toda la ventana porque el CSV público recuperado comienza en septiembre de 2023. Severidad: **media**. El selector de features evita usarla en un fold cuyo train no tenga al menos 200 observaciones; los demás componentes siguen operativos.

Las mayores caídas y subidas diarias del snapshot corresponden a sesiones plausibles de estrés, principalmente marzo de 2020 y abril de 2025; ninguna supera el umbral de ±30% configurado como alerta de ajuste corporativo.

## Cálculos verificados

| Control | Resultado |
|---|---|
| Retornos y drawdown | Verificado con cálculo independiente |
| Kalman causal | Alterar el futuro no cambia filas pasadas |
| ChangeRisk causal | Alterar el futuro no cambia filas pasadas |
| HMM | Probabilidades suman 1 diariamente |
| EGARCH | Pronósticos finitos y positivos |
| Confidence gate | CS <60 limita exposición a 25% |
| Backtest | Señal desplazada exactamente una sesión |
| Splits | `train_end < test_start` en todos los folds |
| Snapshot integrado | Índices, scores, probabilidades y folds coherentes |

Resultado automatizado: **16 pruebas aprobadas**.

## Pronóstico de la próxima sesión

La validación reúne 1,679 pronósticos evaluables entre 2020 y 2026 YTD. El acierto direccional es 54.62%, frente a 54.85% de la referencia basada en la frecuencia positiva del train. El Brier del modelo es 0.24999, frente a 0.24813 de referencia, y el MAE del retorno es 0.866%, frente a 0.835% de predecir retorno cero. El intervalo nominal del 80% cubre 79.27% de los resultados.

La cobertura del intervalo está bien calibrada, pero los modelos de dirección y retorno no mejoran sus referencias simples. Por ello la interfaz muestra **Sin ventaja predictiva comprobada** y conserva el resultado como experimento educativo, no como señal operativa.

## Resultado out-of-sample

| Métrica | DecisionLab | Buy & Hold | Lectura |
|---|---:|---:|---|
| CAGR | 4.45% | 15.40% | Inferior |
| Retorno acumulado | 33.68% | 159.87% | Inferior |
| Volatilidad | 6.29% | 20.10% | 13.81 pp menor |
| Sharpe | 0.72 | 0.81 | Inferior en 0.09 |
| Sortino | 0.97 | 1.15 | Inferior en 0.18 |
| Maximum Drawdown | -10.98% | -33.72% | Mejora de 22.74 pp |
| Calmar | 0.41 | 0.46 | Inferior |
| Recuperación máxima | 571 sesiones | 488 sesiones | 83 sesiones más lenta |

La baja exposición promedio —43.27%— explica parte de la reducción de volatilidad y retorno. Aún no puede afirmarse que la selección de fechas añada valor frente a una reducción estática comparable de exposición; esa comparación debe incorporarse en la siguiente iteración.

## Caveats obligatorios

1. La macro no es vintage-perfect: FRED latest puede contener revisiones posteriores.
2. La comparación debe añadir un benchmark de riesgo equivalente, por ejemplo SPY/cash con la misma volatilidad o exposición promedio.
3. Los horizontes de 12 meses y tres años tienen tamaños efectivos bajos por solapamiento.
4. No se han optimizado umbrales en nested walk-forward.
5. La nomenclatura HMM es una interpretación del train, no un estado económico observable.
6. Los costos no incluyen impuestos, spreads variables ni impacto de mercado.

## Siguiente prueba decisiva

Antes de agregar TFT, comparar la baseline contra:

- Buy & Hold escalado a igual volatilidad;
- cartera SPY/cash con exposición fija de 43.27%;
- media móvil simple con la misma estructura de costos;
- reglas sin cada modelo mediante ablación.

Solo después conviene optimizar pesos dentro de un nested walk-forward y volver a reservar un período final completamente intocado.
