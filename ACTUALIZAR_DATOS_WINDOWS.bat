@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecute INICIAR_WINDOWS.bat
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python scripts\build_snapshot.py --refresh
pause
endlocal

