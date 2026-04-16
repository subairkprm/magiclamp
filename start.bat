@echo off
setlocal EnableDelayedExpansion
title MagicLamp — AI Brain

for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "RED=%ESC%[91m"
set "CYAN=%ESC%[96m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo.
echo %CYAN%%BOLD%  MagicLamp AI Brain — Starting...%RESET%
echo.

:: ─── Check setup was run ──────────────────────────────────────────────────────
if not exist "desktop\node_modules" (
    echo %RED%  ✗ Desktop dependencies not found.%RESET%
    echo    Please run %YELLOW%setup.bat%RESET% first.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo %RED%  ✗ .env not found.%RESET%
    echo    Please run %YELLOW%setup.bat%RESET% first.
    echo.
    pause
    exit /b 1
)

:: ─── Build UI if dist is missing ─────────────────────────────────────────────
if not exist "desktop\dist\index.html" (
    echo %YELLOW%  Building UI (first launch)...%RESET%
    cd desktop
    call npm run build:ui
    if %errorlevel% neq 0 (
        echo %RED%  ✗ UI build failed.%RESET%
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo %GREEN%  ✓ UI built%RESET%
    echo.
)

:: ─── Launch Electron (spawns Python backend automatically) ───────────────────
echo %GREEN%  ✓ Launching MagicLamp...%RESET%
echo    The backend will start automatically inside the app.
echo    Close this window to stop the app.
echo.

cd desktop
call npm run start
cd ..
