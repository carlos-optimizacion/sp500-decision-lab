# Datos, atribución y redistribución

El código del proyecto se entrega bajo licencia MIT. Esa licencia no transfiere derechos sobre los datos descargados de terceros.

- FRED: revisar las notas y derechos de cada serie en su página oficial.
- Cboe: revisar las condiciones de uso aplicables al histórico VIX.
- Yahoo Finance: el acceso sin costo no equivale automáticamente a una licencia de redistribución pública.

El snapshot incluido sirve para revisión privada y reproducibilidad del MVP. Antes de hacer público el repositorio o redistribuir archivos `data/raw`, `data/processed` o `database/parquet`, debe revisarse la política vigente de cada proveedor. Una alternativa prudente para un repositorio público es excluir los datos y reconstruirlos con `python scripts/build_snapshot.py --refresh` durante el despliegue.

