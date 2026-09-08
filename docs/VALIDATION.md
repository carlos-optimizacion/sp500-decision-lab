# Informe de validación del snapshot

## Evaluación general: compartir con salvedades

El MVP es funcional, reproducible y metodológicamente apto para aprendizaje y experimentación. La baseline reduce riesgo absoluto, pero aún no demuestra una ventaja global ajustada por riesgo. No debe utilizarse para tomar decisiones financieras reales.

## Cobertura

- Fecha de corte: 8 de septiembre de 2026.
- Mercado: 3,189 sesiones, del 2 de enero de 2014 al 8 de septiembre de 2026.
- Walk-forward: 1,679 sesiones de test, de 2020 a 2026 YTD.
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

Resultado automatizado: **12 pruebas aprobadas**.

## Resultado out-of-sample

| Métrica | DecisionLab | Buy & Hold | Lectura |
|---|---:|---:|---|
| CAGR | 4.18% | 15.52% | Inferior |
| Retorno acumulado | 31.37% | 161.43% | Inferior |
| Volatilidad | 6.25% | 20.11% | 13.86 pp menor |
| Sharpe | 0.69 | 0.82 | Inferior en 0.13 |
| Sortino | 0.92 | 1.16 | Inferior en 0.24 |
| Maximum Drawdown | -10.98% | -33.72% | Mejora de 22.74 pp |
| Calmar | 0.38 | 0.46 | Inferior |
| Recuperación máxima | 571 sesiones | 488 sesiones | 83 sesiones más lenta |

La baja exposición promedio —42.70%— explica parte de la reducción de volatilidad y retorno. Aún no puede afirmarse que la selección de fechas añada valor frente a una reducción estática comparable de exposición; esa comparación debe incorporarse en la siguiente iteración.

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
- cartera SPY/cash con exposición fija de 42.70%;
- media móvil simple con la misma estructura de costos;
- reglas sin cada modelo mediante ablación.

Solo después conviene optimizar pesos dentro de un nested walk-forward y volver a reservar un período final completamente intocado.

