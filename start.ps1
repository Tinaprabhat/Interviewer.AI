# PGAGI Interview Platform - PowerShell Start Script

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " PGAGI Interview Platform - Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Ensure Node.js is in PATH
if ((Test-Path "C:\nodejs") -and -not ($env:Path -like "*C:\nodejs*")) {
    $env:Path = "C:\nodejs;$env:Path"
    Write-Host "[Setup] Added C:\nodejs to PATH" -ForegroundColor Yellow
}

$npmCmd = if (Test-Path "C:\nodejs\npm.cmd") { "C:\nodejs\npm.cmd" } else { "npm.cmd" }

# Copy .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[Setup] Created .env - add your GROQ_API_KEY!" -ForegroundColor Yellow
}

# Create data dirs
New-Item -ItemType Directory -Force -Path "data\kb_pdfs" | Out-Null
New-Item -ItemType Directory -Force -Path "data\chroma_db" | Out-Null

# Install Python deps
Write-Host "[Backend] Installing Python dependencies..." -ForegroundColor Green
python -m pip install -r requirements.txt -q

# Start backend
Write-Host "[Backend] Starting FastAPI on http://localhost:8001 ..." -ForegroundColor Green
$backend = Start-Process powershell -ArgumentList "-NoExit -Command `"python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload`"" -PassThru

Start-Sleep -Seconds 6

# Install and start frontend
Write-Host "[Frontend] Installing Node dependencies..." -ForegroundColor Green
Set-Location frontend
& $npmCmd install --silent
Write-Host "[Frontend] Starting React on http://localhost:5173 ..." -ForegroundColor Green
$frontend = Start-Process powershell -ArgumentList "-NoExit -Command `"& '$npmCmd' run dev`"" -PassThru
Set-Location ..

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host " API docs: http://localhost:8001/docs" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Note: First run downloads KB PDFs (~50MB) + embedding model (~80MB)" -ForegroundColor Yellow
