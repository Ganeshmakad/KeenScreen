@echo off
cd /d "%~dp0"
powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command "Start-Process pythonw -ArgumentList 'app_gui.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden"
exit /b 0
