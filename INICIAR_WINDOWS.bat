@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual...
  py -3.12 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt

if not exist "data\processed\experiment_latest.json" (
  python scripts\build_snapshot.py --refresh
)

streamlit run streamlit_app.py
endlocal

