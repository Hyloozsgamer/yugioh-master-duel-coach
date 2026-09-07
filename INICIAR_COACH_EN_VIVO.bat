@echo off
title YU-GI-OH! MASTER DUEL - LIVE HUD COACH (1366x768)
color 0B
chcp 65001 > nul

cd /d "%~dp0"

set PYTHON=C:\Users\msika\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PYTHON%" (
    set PYTHON=python
)

echo ============================================================
echo   YU-GI-OH! MASTER DUEL - LIVE COACH OVERLAY (HUD)
echo   Acoplado al lateral izquierdo (340x768)
echo ============================================================
echo.
echo Iniciando Live HUD Coach...

"%PYTHON%" -X utf8 coach_live_overlay.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al ejecutar el Coach en vivo.
    pause
)
pause