@echo off
title YU-GI-OH! MASTER DUEL - HEAD COACH PROFESIONAL
color 0A
chcp 65001 > nul

cd /d "%~dp0"

set PYTHON=C:\Users\msika\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PYTHON%" (
    set PYTHON=python
)

"%PYTHON%" -X utf8 coach_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrio un error al ejecutar el sistema de Coaching.
    pause
)
pause