# Manual simple de usuario

## Para qué sirve

S&P 500 Decision Lab ayuda a estudiar el estado reciente del mercado con datos diarios. Resume oportunidad, riesgo, confianza, régimen y resultados históricos.

No ejecuta operaciones ni sustituye una decisión financiera personal.

## Lectura rápida en tres minutos

1. Comprueba **Datos hasta** en la barra lateral.
2. En **Estado actual**, lee juntos Opportunity, Risk y Confidence.
3. Revisa el aviso del **Pronóstico experimental** antes de mirar sus cifras.
4. Observa el gráfico y cambia entre **Línea** y **Velas** si necesitas más detalle.
5. Abre **Backtesting** para comparar el sistema con Buy & Hold.
6. Consulta **Datos y calidad** para confirmar que el análisis es utilizable.

## Estado actual

- **Opportunity Score**: condiciones históricas favorables, de 0 a 100.
- **Risk Score**: presión de riesgo, de 0 a 100. Un valor alto significa mayor riesgo.
- **Confidence Score**: confianza interna de la lectura. Menos de 60 bloquea los estados fuertes.
- **Régimen**: entorno dominante estimado: Bull, Neutral, Correction o Stress.
- **ChangeRisk**: posibilidad de que el comportamiento reciente esté cambiando.

Los indicadores deben leerse en conjunto. Un Opportunity alto no elimina un Risk alto ni una Confidence baja.

## Pronóstico de la próxima sesión

El pronóstico corresponde a la siguiente sesión bursátil, no necesariamente al día calendario siguiente.

- **Sesgo estimado**: alcista, neutral o bajista según la probabilidad calculada.
- **Probabilidad positiva**: posibilidad estimada de que el próximo cierre ajustado supere al actual.
- **Retorno esperado**: centro de la estimación, no una promesa.
- **Rango probable 80%**: intervalo de precios; aproximadamente uno de cada cinco resultados puede quedar fuera incluso si está bien calibrado.
- **Volatilidad t+1**: amplitud esperada del movimiento, no su dirección.

Lee siempre el mensaje de validación. Si aparece **Sin ventaja predictiva comprobada**, el pronóstico se muestra para investigación y aprendizaje, pero no ha superado referencias simples fuera de muestra.

## Gráfico y velas

La vista inicial es **Línea**. Selecciona **Velas** cuando quieras ver apertura, máximo, mínimo y cierre ajustados de cada sesión.

En la barra del gráfico puedes:

- acercar o alejar;
- desplazar el período visible;
- ajustar automáticamente los ejes;
- restaurar la vista inicial;
- descargar una imagen del gráfico.

La ventana lateral permite elegir desde `1M` hasta `10Y` y activar la escala logarítmica.

## Backtesting

Compara la exposición teórica de Decision Lab con Buy & Hold usando años no empleados para ajustar cada modelo.

Mira especialmente:

- **CAGR**: crecimiento anual compuesto;
- **Sharpe y Sortino**: retorno obtenido en relación con el riesgo;
- **Maximum Drawdown**: peor caída acumulada;
- **Exposición promedio**: proporción media de capital teóricamente expuesta.

El control de costos permite simular el impacto de cambiar la exposición. Un buen resultado histórico no garantiza el futuro.

## Modelos

Permite desactivar Kalman, HMM, EGARCH o Change Point y observar cómo cambia el resultado. Esta prueba se llama ablación y sirve para entender el aporte de cada componente; no crea una orden de inversión.

## Aprendizaje

Explica con el último dato disponible conceptos como retorno, volatilidad, drawdown, VIX, régimen y pronóstico `t+1`.

## Datos y calidad

Muestra las fechas cubiertas, fuentes, controles y limitaciones. Antes de interpretar el sistema, confirma que el estado sea **Apto para el pipeline** y revisa la última fecha disponible.

## Actualizar la información

Pulsa **Actualizar fuentes** en la barra lateral. El sistema descargará datos EOD, validará las series y volverá a estimar los modelos. El proceso puede tardar uno o dos minutos.

## Regla práctica

Usa la aplicación para formular preguntas y comparar escenarios. No conviertas un score, una vela o un pronóstico diario aislado en una decisión automática.
