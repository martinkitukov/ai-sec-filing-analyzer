@echo off
REM AI SEC Filing Analyzer - Deployment Script for Windows
REM This script simplifies the deployment process for both development and production

setlocal enabledelayedexpansion

REM Check if command is provided
if "%1"=="" goto help

REM Function to print colored output (Windows compatible)
:print_status
echo [INFO] %~1
goto :eof

:print_success
echo [SUCCESS] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

REM Function to check if Docker is running
:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker is not running. Please start Docker Desktop."
    exit /b 1
)
call :print_success "Docker is running"
goto :eof

REM Function to check if required environment variables are set
:check_env_vars
if "%GOOGLE_API_KEY%"=="" (
    call :print_error "GOOGLE_API_KEY environment variable is not set."
    call :print_status "Please set it with: set GOOGLE_API_KEY=your-api-key"
    call :print_status "Or create a .env file from env.example"
    exit /b 1
)
call :print_success "Environment variables are configured"
goto :eof

REM Function to build and start development environment
:start_dev
call :print_status "Starting development environment..."
call :check_docker
if errorlevel 1 exit /b 1
call :check_env_vars
if errorlevel 1 exit /b 1

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start development environment
docker-compose up --build -d

call :print_success "Development environment started!"
call :print_status "Frontend: http://localhost:3000"
call :print_status "Backend API: http://localhost:8000"
call :print_status "API Docs: http://localhost:8000/docs"
call :print_status "View logs: docker-compose logs -f"
goto :eof

REM Function to start production environment
:start_prod
call :print_status "Starting production environment..."
call :check_docker
if errorlevel 1 exit /b 1
call :check_env_vars
if errorlevel 1 exit /b 1

REM Check if ALLOWED_ORIGINS is set for production
if "%ALLOWED_ORIGINS%"=="" (
    call :print_warning "ALLOWED_ORIGINS not set. Using default localhost origins."
    set ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start production environment
docker-compose -f docker-compose.prod.yml up --build -d

call :print_success "Production environment started!"
call :print_status "Application: http://localhost (with Nginx)"
call :print_status "Direct API: http://localhost:8000"
call :print_status "View logs: docker-compose -f docker-compose.prod.yml logs -f"
goto :eof

REM Function to stop development environment
:stop_dev
call :print_status "Stopping development environment..."
docker-compose down
call :print_success "Development environment stopped"
goto :eof

REM Function to stop production environment
:stop_prod
call :print_status "Stopping production environment..."
docker-compose -f docker-compose.prod.yml down
call :print_success "Production environment stopped"
goto :eof

REM Function to show status
:show_status
call :print_status "Development containers:"
docker-compose ps

echo.
call :print_status "Production containers:"
docker-compose -f docker-compose.prod.yml ps
goto :eof

REM Function to show logs
:show_logs
if "%1"=="prod" (
    docker-compose -f docker-compose.prod.yml logs -f
) else (
    docker-compose logs -f
)
goto :eof

REM Function to clean up
:cleanup
call :print_status "Cleaning up Docker resources..."
docker-compose down -v >nul 2>&1
docker-compose -f docker-compose.prod.yml down -v >nul 2>&1
docker system prune -f
call :print_success "Cleanup completed"
goto :eof

REM Function to show help
:help
echo AI SEC Filing Analyzer - Deployment Script for Windows
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   dev     Start development environment
echo   prod    Start production environment
echo   stop    Stop development environment
echo   stop-prod Stop production environment
echo   status  Show container status
echo   logs    Show development logs
echo   logs-prod Show production logs
echo   cleanup Clean up Docker resources
echo   help    Show this help message
echo.
echo Environment Variables:
echo   GOOGLE_API_KEY    Required: Your Google AI Studio API key
echo   ALLOWED_ORIGINS   Optional: CORS allowed origins (for production)
echo.
echo Examples:
echo   set GOOGLE_API_KEY=your-api-key
echo   %0 dev
echo   %0 prod
goto :eof

REM Main script logic
if "%1"=="dev" goto start_dev
if "%1"=="prod" goto start_prod
if "%1"=="stop" goto stop_dev
if "%1"=="stop-prod" goto stop_prod
if "%1"=="status" goto show_status
if "%1"=="logs" goto show_logs
if "%1"=="logs-prod" goto show_logs_prod
if "%1"=="cleanup" goto cleanup
if "%1"=="help" goto help

REM Handle logs-prod command
if "%1"=="logs-prod" (
    call :show_logs prod
    goto :eof
)

REM Default to help
goto help 