@echo off
title SamadhanSetu - National Societal Innovation Platform
echo ======================================================================
echo    SAMADHAN SETU - National Societal Innovation Platform
echo    Smart India Hackathon Enterprise Web Application
echo ======================================================================
echo.

cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Activating virtual environment...
    ".venv\Scripts\python.exe" app.py
) ELSE (
    echo [INFO] Using system python...
    python app.py
)

pause

