@echo off
title YU-GI-OH! MASTER DUEL - BOT AUTONOMO (VISUAL)
color 0B
chcp 65001 > nul

set DIR=%~dp0\..
cd /d "%DIR%"

:: Deteccion de ejecutable de Python
set PYTHON=C:\Users\msika\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PYTHON%" (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py -3
    ) else (
        set PYTHON=python
    )
)

echo ============================================================
echo   INICIANDO BOT AUTONOMO PARA YU-GI-OH! MASTER DUEL
echo ============================================================
echo.

%PYTHON% -X utf8 -m master_duel.agent_main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema ejecutando el bot.
    pause
)
