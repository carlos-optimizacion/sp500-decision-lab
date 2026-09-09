# Metodología cuantitativa

## Unidad temporal

Una fila representa una sesión bursátil de SPY. Los datos técnicos del cierre `t` pueden definir una exposición teórica para la sesión `t+1`. Las variables macro se incorporan en su fecha de disponibilidad aproximada, no en la fecha nominal de observación.

## Features iniciales

- Retornos simples de 1, 5, 20 y 60 sesiones.
- MA20, MA50, MA200, distancia a MA200 y cruce MA20/MA50.
- Momentum de 20 y 60 sesiones.
- Volatilidad realizada de 20 y 60 sesiones anualizada con 252.
- VIX, cambio a cinco sesiones, z-score y percentil rolling.
- Drawdown acumulado.
- Fed Funds, Treasuries 2Y/10Y, curva 10Y–2Y, CPI, desempleo, dólar, WTI y spread de crédito.

## Filtro de Kalman

Estado de dos dimensiones sobre log-precio:

```math
x_t = [nivel_t, pendiente_t]^T
```

Transición local lineal:

```math
x_t = \begin{bmatrix}1&1\\0&1\end{bmatrix}x_{t-1}+w_t
```

El modelo guarda innovación `ν`, varianza de innovación `S`, NIS, ganancia, incertidumbre de nivel y una confianza basada en estabilidad rolling de NIS e incertidumbre relativa. La actualización de covarianza usa la forma de Joseph.

## HMM

HMM gaussiano de cuatro estados, covarianza diagonal y estimación EM. Las entradas se estandarizan exclusivamente con el train. Las probabilidades mostradas son las del filtro forward; el algoritmo backward se usa solo dentro del train para ajustar parámetros.

Los estados internos se renombran en cada fold mediante retorno y volatilidad del train:

- `Bull`: mejor combinación retorno–riesgo.
- `Stress`: peor combinación con penalización fuerte a volatilidad.
- `Correction`: estado adverso restante.
- `Neutral`: estado restante más estable.

## EGARCH(1,1)

```math
\log h_t=\omega+\beta\log h_{t-1}+\alpha(|z_{t-1}|-E|z|)+\gamma z_{t-1}
```

Los parámetros se estiman por máxima verosimilitud gaussiana en el train. El pronóstico de volatilidad para `t` usa el shock hasta `t−1`; el retorno observado en `t` solo actualiza el siguiente pronóstico.

## ChangeRisk

Indicador causal que compara los últimos 20 retornos con los 80 inmediatamente anteriores. Combina el desplazamiento absoluto de media, escalado por volatilidad base, y el cambio logarítmico de volatilidad. Una transformación exponencial lo normaliza a 0–100.

PELT/segmentación binaria pueden utilizar toda la serie para explicar rupturas históricas, pero sus puntos offline no entran al backtest.

## Scores

### Opportunity

| Componente | Peso |
|---|---:|
| Tendencia | 30% |
| Momentum | 20% |
| Régimen | 20% |
| Riesgo inverso | 15% |
| Macro/liquidez | 10% |
| Valor por drawdown | 5% |

### Risk

| Componente | Peso |
|---|---:|
| EGARCH | 30% |
| VIX | 25% |
| Drawdown | 15% |
| Cambio estructural | 15% |
| Régimen | 15% |

### Confidence

| Componente | Peso |
|---|---:|
| Kalman | 30% |
| Estabilidad del régimen | 20% |
| Estabilidad estructural | 15% |
| Convergencia/estabilidad de modelos | 10% |
| Calidad de datos | 15% |
| Validación previa walk-forward | 10% |

Todos los pesos y umbrales viven en `config/settings.yaml`. Desactivar un modelo en ablación retira su peso y renormaliza los componentes activos.

## Estados y exposición del backtest

| Opportunity / guarda | Estado | Exposición teórica |
|---|---|---:|
| 0–39 o Risk ≥80 | Esperar / Riesgo elevado | 0% |
| 40–59 | Entrada muy parcial / incierta | 25% |
| 60–79 | Entrada gradual favorable | 65% |
| 80–100 | Condición históricamente muy favorable | 100% |

Si Confidence <60, la exposición máxima queda limitada a 25%.

## Walk-forward

- Train inicial: 2016–2019; test: 2020.
- Luego el train se expande un año y el siguiente año es test.
- El score de desempeño walk-forward disponible en un fold solo resume folds anteriores.
- La calidad que alimenta Confidence se calcula con la cobertura visible en el train del fold, no con el dataset futuro completo.
- La evaluación consolidada concatena únicamente filas de test.
- Los costos se aplican al cambio absoluto de exposición ejecutada.

## Frecuencias por horizonte

Los retornos futuros se utilizan únicamente después de seleccionar condiciones históricas similares para describir sus resultados. No alimentan el score. Como las ventanas se solapan, se informa un tamaño efectivo aproximado; horizontes con evidencia escasa deben interpretarse como exploratorios.

## Pronóstico de la próxima sesión

El objetivo se define como el retorno ajustado entre el cierre `t` y el cierre de la siguiente sesión. Un modelo logístico regularizado estima la probabilidad de retorno positivo y una regresión ridge estima el retorno central. Ambos usan retornos, volatilidad, medias móviles, drawdown y VIX disponibles al cierre.

La validación sigue los mismos folds anuales expanding del sistema. Para el test de cada año, los coeficientes se estiman únicamente con observaciones anteriores y se excluye cualquier fila cuyo resultado pertenezca al período de prueba. El pronóstico visible se vuelve a ajustar con todos los resultados conocidos hasta `t`.

EGARCH aporta la volatilidad anualizada de `t+1`. Se transforma a escala diaria y se combina con el retorno central para formar un intervalo predictivo del 80%. La evaluación informa acierto direccional, Brier, error absoluto medio y cobertura del intervalo frente a referencias simples. Si el modelo no mejora esas referencias, la interfaz muestra `Sin ventaja predictiva comprobada`.
