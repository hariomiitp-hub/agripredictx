@echo off
REM AgriPredictX Deployment Script for Windows
REM Usage: deploy.bat [dev|prod|local|stop|restart|logs|cleanup|build]

setlocal enabledelayedexpansion

set "PROJECT_NAME=AgriPredictX"
set "COMPOSE_FILE=docker-compose.yml"

REM Colors (using color codes)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

goto :entrypoint

:log_info
echo %BLUE%[INFO]%RESET% %~1
goto :eof

:log_success
echo %GREEN%[SUCCESS]%RESET% %~1
goto :eof

:log_warning
echo %YELLOW%[WARNING]%RESET% %~1
goto :eof

:log_error
echo %RED%[ERROR]%RESET% %~1
goto :eof

REM Check if Docker is installed
:check_docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    call :log_error "Docker is not installed."
    call :log_info "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    call :log_info "After installation, restart your terminal and run this script again."
    exit /b 1
)

REM Try both docker-compose and docker compose
where docker-compose >nul 2>nul
if %errorlevel% equ 0 (
    set "DOCKER_COMPOSE=docker-compose"
) else (
    where docker >nul 2>nul
    if %errorlevel% equ 0 (
        docker compose version >nul 2>nul
        if %errorlevel% equ 0 (
            set "DOCKER_COMPOSE=docker compose"
        ) else (
            call :log_error "Docker Compose is not available. Please install Docker Desktop."
            exit /b 1
        )
    ) else (
        call :log_error "Docker is not installed."
        exit /b 1
    )
)
goto :eof

REM Check if Python is installed for local mode
:check_python
where python >nul 2>nul
if %errorlevel% neq 0 (
    call :log_error "Python is not installed. Please install Python 3.9+ from: https://python.org"
    exit /b 1
)
goto :eof

REM Check if local Python environment already has required packages
:check_local_dependencies
python -c "import flask, joblib, numpy, pandas, sklearn, xgboost" >nul 2>nul
goto :eof

REM Create necessary directories
:create_directories
call :log_info "Creating necessary directories..."
if not exist "models" mkdir models
if not exist "data" mkdir data
if not exist "logs" mkdir logs
call :log_success "Directories created"
goto :eof

REM Build the application
:build_app
call :log_info "Building Docker images..."
%DOCKER_COMPOSE% -f %COMPOSE_FILE% build --no-cache
if %errorlevel% neq 0 (
    call :log_error "Failed to build Docker images"
    exit /b 1
)
call :log_success "Docker images built"
goto :eof

REM Start the application
:start_app
set "profile="
if "%1"=="prod" set "profile=--profile production"

call :log_info "Starting %PROJECT_NAME%..."
%DOCKER_COMPOSE% -f %COMPOSE_FILE% %profile% up -d
if %errorlevel% neq 0 (
    call :log_error "Failed to start application"
    exit /b 1
)
call :log_success "%PROJECT_NAME% started"

REM Wait for health check
call :log_info "Waiting for application to be healthy..."
timeout /t 10 /nobreak >nul

REM Check health
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/health' -TimeoutSec 10; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if %errorlevel% equ 0 (
    call :log_success "Application is healthy!"
    echo.
    echo 🌾 AgriPredictX is running!
    echo 📡 API: http://localhost:5000
    if "%1"=="prod" echo 🌐 Web: http://localhost
    echo.
    echo 📚 API Documentation:
    echo   GET  /health          - Health check
    echo   POST /predict         - Single prediction
    echo   POST /predict-batch   - Batch predictions
    echo   GET  /model-info      - Model information
) else (
    call :log_error "Application failed health check"
    call :show_logs
    exit /b 1
)
goto :eof

REM Stop the application
:stop_app
call :log_info "Stopping %PROJECT_NAME%..."
%DOCKER_COMPOSE% -f %COMPOSE_FILE% down
call :log_success "%PROJECT_NAME% stopped"
goto :eof

REM Restart the application
:restart_app
call :log_info "Restarting %PROJECT_NAME%..."
call :stop_app
call :start_app %1
goto :eof

REM Show logs
:show_logs
call :log_info "Showing application logs..."
%DOCKER_COMPOSE% -f %COMPOSE_FILE% logs -f
goto :eof

REM Clean up
:cleanup
call :log_warning "Cleaning up Docker resources..."
%DOCKER_COMPOSE% -f %COMPOSE_FILE% down -v --rmi all
docker system prune -f
call :log_success "Cleanup completed"
goto :eof

REM Run locally with Python
:run_local
call :log_info "Starting %PROJECT_NAME% locally..."

REM Check if requirements are installed
if not exist "venv" (
    call :check_local_dependencies
    if %errorlevel% equ 0 (
        call :log_info "Using existing Python environment..."
    ) else (
        call :log_info "Creating virtual environment..."
        python -m venv venv
        call venv\Scripts\activate.bat
        pip install -r requirements.txt
    )
) else (
    call venv\Scripts\activate.bat
)

REM Start the API server
call :log_info "Starting API server..."
if not exist "logs" mkdir logs
powershell -Command "Start-Process -FilePath 'python' -ArgumentList 'api_server.py' -WorkingDirectory '%CD%' -RedirectStandardOutput 'logs\\local-server.log' -RedirectStandardError 'logs\\local-server.err.log' | Out-Null"

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Check if server is running
curl.exe -s http://127.0.0.1:5000/health >nul 2>nul
if %errorlevel% equ 0 (
    call :log_success "Local server started successfully!"
    echo.
    echo 🌾 AgriPredictX is running locally!
    echo 📡 API: http://localhost:5000
    echo.
    echo 📚 API Documentation:
    echo   GET  /health          - Health check
    echo   POST /predict         - Single prediction
    echo   POST /predict-batch   - Batch predictions
    echo   GET  /model-info      - Model information
    echo.
    echo Press Ctrl+C in the server window to stop.
) else (
    call :log_error "Failed to start local server"
    exit /b 1
)
goto :eof

REM Show usage
:show_usage
echo AgriPredictX Deployment Script
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   dev      - Deploy in development mode (API only)
echo   prod     - Deploy in production mode (with nginx)
echo   local    - Run locally without Docker (requires Python)
echo   stop     - Stop the application
echo   restart  - Restart the application
echo   logs     - Show application logs
echo   cleanup  - Remove all Docker resources
echo   build    - Build Docker images only
echo.
echo Examples:
echo   %0 dev      # Start development deployment
echo   %0 prod     # Start production deployment
echo   %0 local    # Run locally with Python
echo   %0 stop     # Stop all services
echo   %0 logs     # View logs
goto :eof

REM Script entrypoint
:entrypoint
if "%~1"=="" (
    set "command=dev"
) else (
    set "command=%~1"
)

if /I "%command%"=="local" (
    call :check_python
    call :run_local
    goto :eof
)

call :main %*
goto :eof

REM Main script
:main
call :check_docker

set "command=%~1"
if "%command%"=="" set "command=dev"

if "%command%"=="dev" (
    call :create_directories
    call :build_app
    call :start_app dev
) else if "%command%"=="prod" (
    call :create_directories
    call :build_app
    call :start_app prod
) else if "%command%"=="local" (
    call :check_python
    call :run_local
) else if "%command%"=="stop" (
    call :stop_app
) else if "%command%"=="restart" (
    if "%2"=="" (
        call :restart_app dev
    ) else (
        call :restart_app %2
    )
) else if "%command%"=="logs" (
    call :show_logs
) else if "%command%"=="cleanup" (
    call :cleanup
) else if "%command%"=="build" (
    call :build_app
) else (
    call :show_usage
    exit /b 1
)

goto :eof
