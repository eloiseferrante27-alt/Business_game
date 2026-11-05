@echo off
setlocal
cd /d "%~dp0"

docker compose up --build -d
if errorlevel 1 (
    echo Failed to start the game with Docker Compose.
    exit /b 1
)

echo Waiting for the game API...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline = (Get-Date).AddSeconds(30); do { try { if ((Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo The game did not become ready. Recent container logs:
    docker compose logs --tail 40 backend
    exit /b 1
)

echo Game ready at http://localhost:8000
start "" "http://localhost:8000"
endlocal
