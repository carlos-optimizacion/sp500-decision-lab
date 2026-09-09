# Diccionario de datos

## Mercado y macro

| Campo | Unidad | Descripción |
|---|---|---|
| `Open`, `High`, `Low`, `Close` | USD | Precios OHLC de SPY |
| `Adj Close` / `price` | USD | Cierre ajustado usado en retornos |
| `Volume` | acciones | Volumen diario |
| `spx_close` | puntos | S&P 500 de referencia |
| `vix` | puntos | Cierre del VIX |
| `macro_fed_funds` | % | Effective Federal Funds Rate |
| `macro_treasury_2y`, `macro_treasury_10y` | % | Rendimientos Treasury |
| `macro_cpi` | índice | CPI All Urban Consumers |
| `macro_unemployment` | % | Tasa de desempleo |
| `macro_dollar_index` | índice | Dólar amplio ponderado por comercio |
| `macro_wti` | USD/barril | Petróleo WTI |
| `macro_credit_spread` | puntos % | Spread high-yield option-adjusted |

## Features

| Campo | Unidad | Definición |
|---|---|---|
| `return_1d`, `return_5d`, `return_20d`, `return_60d` | decimal | Retorno simple del cierre ajustado |
| `ma_20`, `ma_50`, `ma_200` | USD | Media móvil simple |
| `distance_ma200` | decimal | `price / ma_200 − 1` |
| `momentum_20d`, `momentum_60d` | decimal | Retorno del horizonte |
| `volatility_20d`, `volatility_60d` | decimal anual | Desviación de log-retornos × √252 |
| `vix_percentile` | 0–100 | Percentil causal rolling |
| `drawdown` | decimal ≤0 | Caída desde el máximo acumulado |
| `yield_spread` | puntos % | Treasury 10Y − 2Y |

## Modelos

| Campo | Unidad | Descripción |
|---|---|---|
| `kalman_trend` | USD | Nivel latente filtrado |
| `kalman_innovation` | log-precio | Error de predicción |
| `kalman_nis` | adimensional | Innovación normalizada al cuadrado |
| `kalman_confidence` | 0–100 | Estabilidad de NIS e incertidumbre |
| `regime_Bull`, etc. | 0–1 | Probabilidad filtrada por régimen |
| `regime_label` | categoría | Estado de mayor probabilidad |
| `egarch_volatility_forecast` | decimal anual | Volatilidad condicional para t |
| `egarch_volatility_percentile` | 0–100 | Posición frente a historia disponible |
| `change_risk` | 0–100 | Riesgo causal de cambio de distribución |

## Decisión y backtest

| Campo | Unidad | Descripción |
|---|---|---|
| `opportunity_score` | 0–100 | Condición histórica favorable |
| `risk_score` | 0–100 | Presión agregada de riesgo |
| `confidence_score` | 0–100 | Confiabilidad agregada |
| `decision_state` | texto | Banda descriptiva |
| `target_exposure` | 0–1 | Exposición teórica para la siguiente sesión |
| `executed_exposure` | 0–1 | `target_exposure.shift(1)` |
| `turnover` | 0–1 | Cambio absoluto de exposición |
| `strategy_return` | decimal | Exposición × retorno − costo |
| `strategy_equity` | índice base 1 | Curva acumulada |

## Pronóstico de una sesión

| Campo | Unidad | Descripción |
|---|---:|---|
| `probability_positive` | 0–1 | Probabilidad estimada de retorno positivo en `t+1` |
| `expected_return` | decimal | Retorno central estimado para la próxima sesión |
| `baseline_probability` | 0–1 | Frecuencia positiva observada en el train del fold |
| `volatility_annualized` | decimal anual | Volatilidad EGARCH prevista para `t+1` |
| `lower_return`, `upper_return` | decimal | Límites del intervalo predictivo del 80% |
| `realized_return` | decimal | Resultado observado posteriormente; solo se usa para validación |
| `outcome_date` | fecha | Sesión cuyo retorno permite evaluar el pronóstico originado en `t` |
