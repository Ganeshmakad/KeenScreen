@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title KeenScreen Studio - One-Time Team Dependency Setup

echo ============================================================================
echo   KeenScreen Studio Green Screen Remover - One-Time Team Setup
echo   Repository: https://github.com/Ganeshmakad/KeenScreen
echo ============================================================================
echo.

:: ----------------------------------------------------------------------------
:: 1. Check / Install Python 3
:: ----------------------------------------------------------------------------
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found on PATH. Installing Python 3.12 via Windows Package Manager ^(winget^)...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"` ) do set "PATH=%%P"
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python could not be found after installation.
    echo Please install Python 3.10+ from https://www.python.org/downloads/ ^(check "Add Python to PATH"^) and re-run setup.bat.
    pause
    exit /b 1
)
for /f "delims=" %%V in ('python --version 2^>^&1') do echo     Found: %%V

:: ----------------------------------------------------------------------------
:: 2. Check / Install FFmpeg & FFprobe
:: ----------------------------------------------------------------------------
echo.
echo [2/4] Checking FFmpeg and FFprobe installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] FFmpeg not found on PATH. Installing FFmpeg via winget...
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"` ) do set "PATH=%%P;%LOCALAPPDATA%\Microsoft\WinGet\Links"
)

python -c "import keyer_engine, shutil; p=shutil.which('ffmpeg'); print('    Found FFmpeg:', p if p else 'Will auto-discover on launch')"

:: ----------------------------------------------------------------------------
:: 3. Install Python Libraries (opencv-python, numpy, Pillow)
:: ----------------------------------------------------------------------------
echo.
echo [3/4] Checking / Installing required Python libraries ^(opencv-python, numpy, Pillow^)...
python -c "import cv2, numpy, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    python -m pip install --upgrade pip --quiet
    python -m pip install -r "%~dp0requirements.txt"
    if !errorlevel! neq 0 (
        echo [!] Retrying pip install with --user flag...
        python -m pip install --user -r "%~dp0requirements.txt"
    )
) else (
    echo     Python libraries ^(opencv-python, numpy, Pillow^) are already installed.
)

:: ----------------------------------------------------------------------------
:: 4. Verify Environment
:: ----------------------------------------------------------------------------
echo.
echo [4/4] Verifying Studio Green Screen Engine dependencies...
python -c "import cv2, numpy, PIL, keyer_engine; print('    [OK] OpenCV:', cv2.__version__, '| NumPy:', numpy.__version__, '| Pillow:', PIL.__version__)"
if %errorlevel% neq 0 (
    echo [ERROR] Dependency verification failed. Please check the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   SETUP COMPLETED SUCCESSFULLY!
echo   From now on, simply double-click "start.bat" to auto-sync the latest
echo   version from GitHub and open the Studio Green Screen Remover GUI!
echo ============================================================================
echo.
if "%KEENSCREEN_NO_GUI%"=="1" exit /b 0
choice /C YN /M "Would you like to launch the GUI now"
if errorlevel 2 goto :eof
call "%~dp0start.bat"
