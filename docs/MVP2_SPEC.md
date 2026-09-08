# S&P 500 Decision Lab — MVP 2

## 1. Objetivo general

Construir una aplicación web funcional denominada **S&P 500 Decision Lab**, orientada al análisis cuantitativo y aprendizaje aplicado sobre el S&P 500, utilizando datos históricos reales y fuentes gratuitas.

El MVP debe validar si una combinación de modelos matemáticos permite mejorar la interpretación del estado del mercado y el rendimiento ajustado por riesgo frente a una estrategia base de **Buy & Hold**.

El MVP debe desarrollarse con:

**Costo tecnológico mensual objetivo: US$0.**

No se requiere tiempo real en esta versión.

---

# 2. Filosofía del sistema

La herramienta no debe intentar predecir el mercado con certeza.

Debe trabajar bajo cuatro principios:

1. Probabilidad.
2. Riesgo.
3. Incertidumbre.
4. Validación histórica.

La lógica central será:

```math
Datos \rightarrow Estado \rightarrow Riesgo \rightarrow Régimen \rightarrow Validación \rightarrow Decisión
```

La salida nunca debe presentarse como una certeza de compra.

Utilizar estados como:

- Esperar.
- Entrada gradual.
- Condición favorable.
- Reducir exposición.
- Condición incierta.

---

# 3. Alcance del MVP 2

El MVP debe incluir:

- datos históricos reales;
- pipeline automatizado de adquisición de datos;
- almacenamiento local;
- feature engineering;
- Filtro de Kalman;
- opcionalmente UKF como comparación;
- Hidden Markov Model;
- EGARCH;
- Change Point Detection;
- Opportunity Score;
- Risk Score;
- Confidence Score;
- backtesting;
- walk-forward validation;
- comparación con Buy & Hold;
- dashboard web;
- visualización temporal;
- explicación de las señales;
- módulo básico de aprendizaje.

No incluir todavía:

- trading automático;
- conexión con broker;
- ejecución de órdenes;
- datos SIP de pago;
- infraestructura comercial;
- microservicios;
- Kafka;
- streaming tick-by-tick.

---

# 4. Arquitectura tecnológica

Utilizar inicialmente:

- Python.
- Streamlit.
- Pandas o Polars.
- NumPy.
- SciPy.
- Plotly.
- scikit-learn.
- statsmodels.
- arch.
- hmmlearn.
- ruptures.
- FilterPy o implementación propia de Kalman.
- DuckDB.
- Parquet.
- GitHub.
- Pytest.

Evitar infraestructura pagada.

La arquitectura deberá quedar preparada para migrar posteriormente a:

- FastAPI;
- PostgreSQL;
- TimescaleDB;
- Redis;
- WebSockets;
- proveedores real-time.

---

# 5. Arquitectura lógica

```text
FUENTES GRATUITAS
        │
        ▼
DATA INGESTION
        │
        ▼
RAW DATA
        │
        ▼
DATA VALIDATION
        │
        ▼
CLEAN DATA
        │
        ▼
FEATURE ENGINEERING
        │
        ▼
DUCKDB / PARQUET
        │
        ▼
┌───────────────────────────┐
│     MODEL ENGINE          │
│                           │
│ Kalman / UKF              │
│ HMM                       │
│ EGARCH                    │
│ Change Point Detection    │
└──────────────┬────────────┘
               │
               ▼
       DECISION ENGINE
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
Opportunity   Risk   Confidence
 Score       Score      Score
     │         │         │
     └─────────┼─────────┘
               ▼
           BACKTEST
               │
               ▼
         WALK FORWARD
               │
               ▼
           DASHBOARD

```

---

# 6. Fuentes de datos

Priorizar fuentes gratuitas y oficiales.

## Mercado

Utilizar principalmente:

**SPY**

como proxy operativo del S&P 500.

Variables:

- Open.
- High.
- Low.
- Close.
- Adjusted Close.
- Volume.

Siempre que sea posible, añadir SPX como referencia.

## Riesgo

Utilizar:

**VIX**

preferiblemente desde CBOE o fuente pública verificable.

## Macroeconomía

Utilizar FRED/ALFRED para:

- Fed Funds Rate.
- Treasury 2Y.
- Treasury 10Y.
- curva 10Y–2Y.
- CPI.
- desempleo.
- dólar.
- spreads de crédito.

## Energía

Incluir:

- WTI o Brent.

## Fuentes futuras

Dejar preparados conectores para:

- SEC EDGAR.
- GDELT.
- BLS.
- BEA.
- World Bank.

---

# 7. Primer conjunto de variables

No comenzar con cientos de variables.

Utilizar aproximadamente 15–25 variables.

## Precio y retorno

```math
Return_{1d}
```

```math
Return_{5d}
```

```math
Return_{20d}
```

```math
Return_{60d}
```

## Tendencia

```math
MA20
```

```math
MA50
```

```math
MA200
```

Calcular también:

```math
DistanceMA200= \frac{Price-MA200}{MA200}
```

## Momentum

- momentum 20 días;
- momentum 60 días.

## Riesgo

- volatilidad rolling;
- VIX;
- cambio del VIX;
- percentil VIX.

## Drawdown

```math
Drawdown_t= \frac{P_t-MaxHistorical_t}{MaxHistorical_t}
```

## Macro

- Fed Funds Rate;
- Treasury 2Y;
- Treasury 10Y;
- spread 10Y–2Y;
- CPI;
- unemployment;
- Dollar Index;
- petróleo.

---

# 8. Modelo Kalman

Kalman será un componente central.

Debe utilizarse para:

- filtrar ruido;
- estimar tendencia latente;
- medir error;
- calcular innovación;
- estimar incertidumbre.

Registrar:

```math
\nu_t=z_t-H\hat{x}_{t|t-1}
```

y calcular:

```math
NIS_t= \nu_t^T S_t^{-1}\nu_t
```

El dashboard deberá mostrar:

- tendencia Kalman;
- error;
- innovación;
- NIS;
- confianza estimada.

Evaluar posteriormente:

- Kalman clásico.
- Unscented Kalman Filter.

No usar UKF si no supera al modelo simple.

---

# 9. Hidden Markov Model

El HMM debe detectar regímenes.

Inicialmente utilizar cuatro:

1. Bull.
2. Neutral.
3. Correction.
4. Stress.

Las entradas pueden incluir:

- retornos;
- volatilidad;
- VIX;
- tendencia Kalman;
- yield spread;
- crédito.

El resultado deberá mostrar probabilidades:

```text
Bull         63%
Neutral      21%
Correction   11%
Stress        5%

```

No utilizar solamente la etiqueta ganadora.

Guardar todas las probabilidades.

---

# 10. EGARCH

Utilizar EGARCH para modelar volatilidad condicional.

Debe proporcionar:

```math
\sigma_{t+1}
```

y permitir identificar:

- riesgo bajo;
- riesgo normal;
- riesgo alto;
- riesgo extremo.

Comparar eventualmente contra GARCH.

Mantener EGARCH únicamente si mejora el pronóstico de volatilidad.

---

# 11. Change Point Detection

Utilizar Change Point Detection para identificar rupturas estructurales.

Evaluar:

- PELT;
- Binary Segmentation;
- Bayesian Change Point posteriormente.

El sistema debe producir una variable equivalente a:

```math
ChangeRisk_t
```

normalizada entre:

```math
0-100
```

Un cambio estructural elevado debe reducir automáticamente el Confidence Score.

---

# 12. Decision Engine

Los modelos no deben producir directamente BUY o SELL.

Crear tres scores centrales:

## Opportunity Score

```math
OS\in[0,100]
```

Debe reflejar:

- tendencia;
- momentum;
- régimen;
- valoración de riesgo;
- condiciones macro;
- drawdown.

## Risk Score

```math
RS\in[0,100]
```

Debe considerar:

- EGARCH;
- VIX;
- drawdown;
- cambio estructural;
- régimen.

## Confidence Score

```math
CS\in[0,100]
```

Debe considerar:

- error Kalman;
- NIS;
- estabilidad del régimen;
- estabilidad del modelo;
- desempeño walk-forward.

Regla fundamental:

```math
CS<60
```

debe impedir señales fuertes.

---

# 13. Salidas del Decision Engine

No utilizar una señal binaria.

Utilizar:

```text
0–39
Esperar / Riesgo elevado

40–59
Entrada muy parcial / Condición incierta

60–79
Entrada gradual favorable

80–100
Condición históricamente muy favorable

```

Estos umbrales son inicialmente provisionales.

Deben optimizarse posteriormente mediante backtesting y walk-forward.

---

# 14. Backtesting

Crear un motor propio y transparente.

Comparar:

## Benchmark

```math
Buy\&Hold\ SPY
```

contra:

```math
S\&P500\ DecisionLab
```

Calcular:

- CAGR.
- retorno acumulado.
- volatilidad anualizada.
- Sharpe.
- Sortino.
- Maximum Drawdown.
- Calmar Ratio.
- Win Rate.
- porcentaje de tiempo invertido.
- recovery time.
- peor año.
- mejor año.

Incluir costos de transacción configurables aunque inicialmente sean:

```math
0
```

para poder incorporarlos posteriormente.

---

# 15. Walk-forward validation

Evitar entrenar y probar sobre los mismos datos.

Utilizar esquema:

```text
Train 2016–2019
Test 2020

Train 2016–2020
Test 2021

Train 2016–2021
Test 2022

```

y continuar.

También permitir ventanas móviles posteriormente.

Registrar resultados por período.

La comparación principal debe hacerse **out-of-sample**.

---

# 16. Evitar Look-Ahead Bias

Este requisito es obligatorio.

Nunca utilizar información futura en:

- indicadores;
- macroeconomía;
- modelos;
- normalizaciones;
- definición de regímenes;
- scores.

Las features del día:

```math
t
```

solo pueden utilizar información disponible:

```math
\leq t
```

Cuando se incorporen datos macro revisados, utilizar vintages históricos cuando sea posible.

---

# 17. Dashboard principal

Crear una página denominada:

# S&P 500 Decision Lab

Debe incluir selector:

```text
1M | 3M | 6M | 1Y | 3Y | 5Y | 10Y

```

## Gráfico principal

Mostrar:

- SPY / S&P 500.
- MA20.
- MA50.
- MA200.
- tendencia Kalman.
- drawdowns.

---

# 18. Condiciones actuales

Mostrar barras:

```text
Tendencia        XX
Momentum         XX
Volatilidad      XX
Riesgo global    XX
Liquidez         XX

```

---

# 19. Control del modelo

Mostrar:

```text
Confianza Kalman          XX%
Error / Innovación        Normal / Elevado
NIS                       X.XX
Cambio estructural        XX%
Confidence Score          XX%

```

---

# 20. Régimen del mercado

Mostrar visualmente:

```text
Bull
Neutral
Correction
Stress

```

con probabilidades.

---

# 21. Opportunity Score

Mostrar un gauge o barra grande:

```text
Opportunity Score
74 / 100

```

Acompañarlo siempre con:

- Risk Score.
- Confidence Score.

---

# 22. Explicación de la señal

Mostrar:

## Factores positivos

Ejemplo:

- tendencia;
- momentum;
- liquidez.

## Riesgos

Ejemplo:

- VIX;
- tasas reales;
- cambio estructural.

El usuario debe poder entender por qué cambió el score.

---

# 23. Probabilidades por horizonte

Inicialmente calcular frecuencias históricas condicionadas.

Mostrar:

```text
1 mes
3 meses
6 meses
12 meses
3 años

```

No presentar como probabilidad absoluta de futuro.

Utilizar lenguaje:

**Probabilidad histórica estimada bajo condiciones similares.**

---

# 24. Página Backtesting

Mostrar comparación gráfica:

```math
DecisionLab
```

vs.

```math
Buy\&Hold
```

Incluir:

- equity curve;
- drawdown;
- retornos anuales;
- tabla de métricas;
- períodos de crisis.

Permitir inspeccionar:

- 2020;
- 2022;
- otros drawdowns relevantes.

---

# 25. Página Modelos

Mostrar resultados separados de:

- Kalman.
- HMM.
- EGARCH.
- Change Point.

Permitir activar/desactivar cada modelo para estudiar su contribución.

Esto permitirá realizar análisis de ablación.

Ejemplo:

```text
Sistema completo
vs
Sin HMM
vs
Sin EGARCH
vs
Sin Kalman

```

---

# 26. Modo aprendizaje

Crear una sección básica que explique:

- retorno;
- volatilidad;
- drawdown;
- VIX;
- Kalman;
- régimen;
- Opportunity Score.

Utilizar los datos históricos mostrados en pantalla para explicar cada concepto.

No desarrollar todavía el sistema adaptativo completo de aprendizaje.

Dejar la arquitectura preparada.

---

# 27. Arquitectura de carpetas

```text
sp500-decision-lab/
│
├── app/
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── charts/
│
├── data/
│   ├── providers/
│   ├── ingestion/
│   ├── validation/
│   ├── raw/
│   ├── processed/
│   └── features/
│
├── models/
│   ├── kalman/
│   ├── hmm/
│   ├── egarch/
│   └── change_point/
│
├── decision/
│   ├── opportunity.py
│   ├── risk.py
│   ├── confidence.py
│   └── engine.py
│
├── backtesting/
│   ├── engine.py
│   ├── metrics.py
│   └── walk_forward.py
│
├── learning/
│
├── database/
│   ├── duckdb/
│   └── parquet/
│
├── tests/
│
├── config/
│
├── notebooks/
│
├── requirements.txt
├── README.md
└── .gitignore

```

---

# 28. Principios de ingeniería

Aplicar:

- modularidad;
- separación de responsabilidades;
- reproducibilidad;
- trazabilidad;
- tests;
- configuración centralizada;
- logging;
- versionamiento;
- documentación.

Evitar hardcodear:

- fechas;
- tickers;
- umbrales;
- pesos;
- rutas;
- API keys.

Utilizar configuración.

---

# 29. Reproducibilidad

Cada ejecución del backtest debe registrar:

- fecha;
- versión de datos;
- configuración;
- parámetros;
- versión del modelo;
- resultados.

Idealmente generar un identificador:

```text
experiment_id

```

---

# 30. Validación de datos

Antes de ejecutar modelos verificar:

- duplicados;
- valores faltantes;
- timestamps;
- continuidad;
- outliers;
- frecuencia;
- timezone;
- ajustes corporativos.

Si existen errores de datos, detener el modelo o marcar baja confianza.

---

# 31. Testing

Crear pruebas para:

- cálculo de retornos;
- drawdown;
- indicadores;
- Kalman;
- scoring;
- backtesting;
- ausencia de look-ahead;
- walk-forward.

El sistema no debe aceptar una estrategia cuyo backtest utilice información futura.

---

# 32. TFT

No implementar TFT en la primera iteración del MVP.

Primero validar:

```math
Kalman+HMM+EGARCH+ChangePoint
```

Cuando exista una baseline sólida:

1. incorporar TFT;
2. comparar out-of-sample;
3. mantenerlo únicamente si mejora resultados.

---

# 33. Métrica de éxito

La herramienta no tiene que necesariamente superar Buy & Hold en retorno absoluto.

Debe evaluarse principalmente mediante:

```math
Rentabilidad\ ajustada\ por\ riesgo
```

y reducción de:

```math
Maximum\ Drawdown
```

Un resultado puede considerarse interesante si:

- Sharpe mejora;
- Sortino mejora;
- drawdown disminuye;
- recuperación es más rápida;

aunque CAGR sea ligeramente menor.

---

# 34. Entregables del MVP

El proyecto deberá entregar:

1. repositorio GitHub organizado;
2. README completo;
3. aplicación Streamlit funcional;
4. pipeline de datos;
5. dataset histórico;
6. feature store;
7. modelos Kalman/HMM/EGARCH/Change Point;
8. Decision Engine;
9. backtesting;
10. walk-forward validation;
11. comparación Buy & Hold;
12. dashboard;
13. pruebas básicas;
14. documentación de arquitectura;
15. instrucciones de ejecución local.

---

# 35. Orden de construcción

Desarrollar en este orden:

### Fase 1

Repositorio + estructura + configuración.

### Fase 2

Data providers.

### Fase 3

Data validation.

### Fase 4

Feature engineering.

### Fase 5

Dashboard base.

### Fase 6

Kalman.

### Fase 7

EGARCH.

### Fase 8

HMM.

### Fase 9

Change Point.

### Fase 10

Decision Engine.

### Fase 11

Backtesting.

### Fase 12

Walk-forward.

### Fase 13

Optimización de scores.

### Fase 14

Página de explicación/aprendizaje.

### Fase 15

Testing final.

---

# 36. Restricciones

No realizar trading.

No enviar órdenes.

No conectar broker en este MVP.

No presentar resultados como asesoría financiera personalizada.

No utilizar datos futuros en backtesting.

No utilizar modelos complejos si no superan modelos más simples fuera de muestra.

---

# 37. Evolución futura

El diseño debe permitir una futura migración:

```text
HistoricalProvider
        ↓
RealTimeProvider
        ↓
WebSocket
        ↓
Event Stream
        ↓
Online Kalman
        ↓
Decision Engine
        ↓
Live Dashboard

```

Sin reescribir los modelos centrales.

---

# 38. Nombre del producto

Nombre de trabajo:

# S&P 500 Decision Lab

Descripción:

**Laboratorio cuantitativo para aprender, analizar y evaluar condiciones del S&P 500 mediante modelos matemáticos, riesgo, validación histórica y control permanente del error.**

---

# 39. Principio rector

La herramienta debe responder continuamente:

```math
\boxed{¿Qué está pasando?}
```

```math
\boxed{¿Qué nivel de riesgo existe?}
```

```math
\boxed{¿En qué régimen estamos?}
```

```math
\boxed{¿Cuánto se está equivocando el modelo?}
```

```math
\boxed{¿Qué ocurrió históricamente bajo condiciones similares?}
```

```math
\boxed{¿La estrategia funciona fuera de muestra?}
```

La prioridad no es predecir perfectamente el futuro.

La prioridad es:

```math
\boxed{ Tomar\ decisiones\ mejor\ informadas }
```

mediante:

```math
\boxed{ Datos + Matemática + Riesgo + Error + Validación }
```