@echo off
setlocal EnableDelayedExpansion
title MagicLamp — Setup

:: ─────────────────────────────────────────────────────────────────────────────
:: Colors  (uses ANSI — works on Windows 10 1903+ / Windows 11)
:: ─────────────────────────────────────────────────────────────────────────────
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "RED=%ESC%[91m"
set "CYAN=%ESC%[96m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo.
echo %CYAN%%BOLD%  ╔══════════════════════════════════════════╗%RESET%
echo %CYAN%%BOLD%  ║      MagicLamp AI Brain — Setup          ║%RESET%
echo %CYAN%%BOLD%  ╚══════════════════════════════════════════╝%RESET%
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: 1. Check Python
:: ─────────────────────────────────────────────────────────────────────────────
echo %YELLOW%[1/5]%RESET% Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%  ✗ Python not found.%RESET%
    echo     Download from https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo %GREEN%  ✓ %PYVER% found%RESET%

:: ─────────────────────────────────────────────────────────────────────────────
:: 2. Check Node.js
:: ─────────────────────────────────────────────────────────────────────────────
echo %YELLOW%[2/5]%RESET% Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%  ✗ Node.js not found.%RESET%
    echo     Download from https://nodejs.org/ (LTS version recommended)
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODEVER=%%i
echo %GREEN%  ✓ Node.js %NODEVER% found%RESET%

:: ─────────────────────────────────────────────────────────────────────────────
:: 3. Install Python backend dependencies
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %YELLOW%[3/5]%RESET% Installing Python backend dependencies...
echo     (this may take a few minutes)
echo.
pip install -r brain\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo %RED%  ✗ pip install failed. See errors above.%RESET%
    pause
    exit /b 1
)
echo.
echo %GREEN%  ✓ Python dependencies installed%RESET%

:: ─────────────────────────────────────────────────────────────────────────────
:: 4. Install desktop npm dependencies
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %YELLOW%[4/5]%RESET% Installing desktop dependencies...
echo     (downloading Electron + React packages)
echo.
cd desktop
call npm install
if %errorlevel% neq 0 (
    echo.
    echo %RED%  ✗ npm install failed. See errors above.%RESET%
    cd ..
    pause
    exit /b 1
)
cd ..
echo.
echo %GREEN%  ✓ Desktop dependencies installed%RESET%

:: ─────────────────────────────────────────────────────────────────────────────
:: 5. Create .env if missing
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %YELLOW%[5/5]%RESET% Setting up environment...

if not exist "brain\.env" (
    if exist "brain\.env.example" (
        copy "brain\.env.example" "brain\.env" >nul
        echo %GREEN%  ✓ Created brain\.env from .env.example%RESET%
    ) else (
        echo %YELLOW%  ! No .env.example found — creating minimal .env%RESET%
        :: Generate a random secret using Python
        for /f %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set JWT_SECRET=%%i
        for /f %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set BRAIN_SECRET=%%i
        (
            echo SUPABASE_URL=
            echo SUPABASE_SERVICE_KEY=
            echo JWT_SECRET=!JWT_SECRET!
            echo BRAIN_SECRET=!BRAIN_SECRET!
            echo OLLAMA_URL=http://localhost:11434
            echo OLLAMA_MODEL=qwen2.5:7b
            echo BRAIN_AUTO_MODE=false
            echo CORS_ORIGINS=http://localhost:5173,app://localhost
        ) > brain\.env
        echo %GREEN%  ✓ Created brain\.env with generated secrets%RESET%
    )
    echo.
    echo %YELLOW%  ⚠  IMPORTANT: Open brain\.env and fill in:%RESET%
    echo     - SUPABASE_URL
    echo     - SUPABASE_SERVICE_KEY
) else (
    echo %GREEN%  ✓ brain\.env already exists — skipping%RESET%
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Done
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %CYAN%%BOLD%  ╔══════════════════════════════════════════╗%RESET%
echo %CYAN%%BOLD%  ║         Setup complete!  ✓               ║%RESET%
echo %CYAN%%BOLD%  ╚══════════════════════════════════════════╝%RESET%
echo.
echo  %BOLD%Next steps:%RESET%
echo   1. Edit %YELLOW%brain\.env%RESET% and add your Supabase credentials
echo   2. Make sure %YELLOW%Ollama%RESET% is running  (ollama serve)
echo   3. Double-click %GREEN%start.bat%RESET% to launch MagicLamp
echo.
echo  Default login: %BOLD%admin%RESET% / %BOLD%admin123%RESET%
echo.
pause
