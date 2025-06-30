@echo off
REM AI SEC Filing Analyzer - Interview Demo Script (Windows)
REM Quick and lightweight deployment for interviews

echo [INFO] Starting AI SEC Filing Analyzer Demo...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Try to load .env file from backend folder
if exist "backend\.env" (
    echo [INFO] Loading environment from backend\.env
    for /f "tokens=1,2 delims==" %%a in (backend\.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Check for API key (from .env or environment)
if "%GOOGLE_API_KEY%"=="" (
    echo [ERROR] GOOGLE_API_KEY not found in environment or backend\.env
    echo [INFO] Please create backend\.env file with: GOOGLE_API_KEY=your-api-key
    echo [INFO] Get a free API key at: https://aistudio.google.com/
    pause
    exit /b 1
)

echo [INFO] API key found and loaded successfully

echo Do you want to rebuild images? (y/n)
set /p rebuild=
if /i "%rebuild%"=="y" (
    docker-compose -f docker-compose.demo.yml build
)

echo Do you want to prune unused Docker resources? (y/n)
set /p prune=
if /i "%prune%"=="y" (
    docker system prune -af --volumes
)

docker-compose -f docker-compose.demo.yml up -d

echo [INFO] Waiting for services to start...
timeout /t 15 /nobreak >nul

docker-compose -f docker-compose.demo.yml ps | findstr "Up" >nul
if errorlevel 1 (
    echo [ERROR] Failed to start services. Check logs with:
    echo docker-compose -f docker-compose.demo.yml logs
    pause
    exit /b 1
)

echo [SUCCESS] Demo is ready!
echo.
echo Access the application:
echo   Frontend: http://localhost
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo To stop the demo:
echo   docker-compose -f docker-compose.demo.yml down
echo.
echo To view logs:
echo   docker-compose -f docker-compose.demo.yml logs -f
echo.
echo To clean up disk space:
echo   docker system prune -af --volumes
echo.
echo To shrink WSL disk after cleanup:
echo   1. Quit Docker Desktop
    2. Run: wsl --shutdown
    3. Run in PowerShell as Admin:
    Optimize-VHD -Path "%USERPROFILE%\AppData\Local\Docker\wsl\data\ext4.vhdx" -Mode Full
echo.
pause 