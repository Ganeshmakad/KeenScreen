@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title KeenScreen Studio — Interactive CMD Control Center

:: Run GitHub Auto-Sync first so the CLI is always on the latest version
if exist "%~dp0start.bat" (
    set "KEENSCREEN_NO_GUI=1"
    call "%~dp0start.bat"
    set "KEENSCREEN_NO_GUI="
)

:: Launch Interactive CMD Control Center (or pass CLI arguments if provided)
python "%~dp0cli.py" %*
if %errorlevel% neq 0 (
    echo.
    pause
)
