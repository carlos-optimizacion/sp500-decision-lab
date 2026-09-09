# Arquitectura técnica

## Decisión de diseño

El MVP usa un monolito modular en Python. Para el volumen actual —unas pocas miles de sesiones diarias— separar microservicios añadiría costo y complejidad sin mejorar la validación matemática. Los límites entre módulos permiten migrar más adelante a FastAPI, PostgreSQL/TimescaleDB, Redis y WebSockets.

## Flujo de ejecución

1. `data.providers` descarga bytes de Yahoo, Cboe y FRED.
2. `data.ingestion` normaliza fechas, aplica rezagos de publicación y ensambla por sesión SPY.
3. `data.validation` bloquea el pipeline ante errores materiales.
4. `data.features` calcula variables causales.
5. `backtesting.walk_forward` separa train y test por año.
6. En cada fold, HMM y EGARCH se ajustan solo con train; Kalman y ChangeRisk se calculan recursivamente.
7. `decision` construye Risk, Opportunity y Confidence.
8. `forecasting` ajusta modelos regularizados por año, genera pronósticos `t+1` y mide su desempeño contra referencias simples.
9. `backtesting.engine` desplaza exposición una sesión, incorpora turnover/costos y compara con Buy & Hold.
10. `core.analysis` guarda snapshots, manifiestos, experimento, Parquet y DuckDB.
11. `app` lee el snapshot y permite explorar sin volver a entrenar en cada interacción.

## Contratos entre capas

| Capa | Entrada | Salida | Regla clave |
|---|---|---|---|
| Ingestión | Respuestas HTTP | `market_daily` | Sin claves ni infraestructura pagada |
| Validación | Dataset alineado | `QualityReport` | Un error material detiene modelos |
| Features | Datos hasta `t` | Feature store | Nunca usa valores posteriores |
| Modelos | Train/test explícitos | Estados y riesgos | Probabilidad filtrada, no suavizada |
| Decision | Componentes 0–100 | Scores y estado | Confidence <60 bloquea señal fuerte |
| Forecasting | Features conocidas en `t` | Probabilidad, retorno e intervalo `t+1` | El resultado `t+1` solo evalúa el pronóstico |
| Backtest | Retorno + exposición | Curvas/métricas | Exposición se desplaza a `t+1` |
| Dashboard | Snapshot validado | Vistas interactivas | Señala fecha, fuente y caveats |

## Persistencia

- CSV: interoperabilidad y revisión humana.
- Parquet: lectura columnar eficiente.
- DuckDB: consultas locales sobre tablas materializadas.
- JSON: manifiesto de fuentes, calidad, configuración y experimentos.

## Camino hacia tiempo real

La interfaz `data.providers` puede sustituirse por un proveedor con WebSocket sin tocar scores o backtest. Una evolución razonable es:

1. FastAPI como capa de servicio.
2. PostgreSQL/TimescaleDB para series y versiones.
3. Redis para último estado y caché.
4. Workers para ingestión y reentrenamiento.
5. WebSockets solo cuando el caso de uso necesite intradía.

Kafka no se justifica mientras la escala sea una única familia de activos EOD.
