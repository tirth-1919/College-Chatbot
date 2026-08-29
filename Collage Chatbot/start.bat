@echo off
setlocal enabledelayedexpansion

echo ================================================================================
echo        AHMEDABAD INSTITUTE OF TECHNOLOGY (AIT) AI ASSISTANT
echo        Unified Single-Port Localhost Application Server
echo ================================================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python runtime...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is required but was not found.
    pause
    exit /b 1
)

echo [2/4] Verifying React / Vite Frontend...
if not exist "frontend\dist\index.html" (
    echo Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo [3/4] Initializing Database and AI services...
python -c "from backend.app.database import Base, engine; from database.seed.seed_data import seed_database; Base.metadata.create_all(bind=engine); seed_database()"

echo [4/4] Starting Unified Server on http://localhost:5000...
echo.
echo --------------------------------------------------------------------------------
echo   AIT AI Assistant is running at:
echo   http://localhost:5000
echo --------------------------------------------------------------------------------
echo.

start http://localhost:5000
python run.py

pause
