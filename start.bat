@echo off
echo ============================================
echo  PGAGI Interview Platform - Startup Script
echo ============================================

:: Copy .env if needed
if not exist ".env" (
    copy .env.example .env
    echo [Setup] Created .env from .env.example
    echo [Action] Please add your GROQ_API_KEY to .env
)

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Install Python 3.10+
    pause
    exit /b 1
)

:: Install backend deps
echo [Backend] Installing Python dependencies...
python -m pip install -r requirements.txt --quiet

:: Create data dirs
if not exist "data\kb_pdfs" mkdir data\kb_pdfs
if not exist "data\chroma_db" mkdir data\chroma_db

:: Start backend in background
echo [Backend] Starting FastAPI server on http://localhost:8001 ...
start "PGAGI Backend" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload"

:: Wait for backend
echo [Waiting] Giving backend 5 seconds to start...
timeout /t 5 /nobreak >nul

:: Install frontend deps
echo [Frontend] Installing Node dependencies...
cd frontend
if exist "C:\nodejs\npm.cmd" (
    call C:\nodejs\npm.cmd install --silent
) else (
    call npm.cmd install --silent
)

:: Start frontend
echo [Frontend] Starting React app on http://localhost:5173 ...
if exist "C:\nodejs\npm.cmd" (
    start "PGAGI Frontend" cmd /k "C:\nodejs\npm.cmd run dev"
) else (
    start "PGAGI Frontend" cmd /k "npm.cmd run dev"
)
cd ..

echo.
echo ============================================
echo  App running at: http://localhost:5173
echo  API docs at:    http://localhost:8001/docs
echo ============================================
pause
