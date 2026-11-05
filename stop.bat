@echo off
setlocal
cd /d "%~dp0"

docker compose down
if errorlevel 1 (
    echo Failed to stop the game with Docker Compose.
    exit /b 1
)

echo Game stopped. Saved data has been preserved.
endlocal
