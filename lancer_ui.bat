@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3.12 -m uvicorn api.app:create_default_app --factory --reload
) else (
    python -m uvicorn api.app:create_default_app --factory --reload
)

if errorlevel 1 (
    echo.
    echo Le lancement a echoue. Verifiez Python 3.12 et les dependances du projet.
    pause
)
