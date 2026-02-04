@echo off
REM =============================================================================
REM Stratum AI - Edition Build Script (Windows)
REM =============================================================================
REM Builds standalone deployable packages for each tier
REM
REM Usage:
REM   build.bat all           - Build all editions
REM   build.bat starter       - Build Starter only
REM   build.bat professional  - Build Professional only
REM   build.bat enterprise    - Build Enterprise only
REM =============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set BUILD_DIR=%SCRIPT_DIR%dist

if "%1"=="" set EDITION=all
if not "%1"=="" set EDITION=%1

echo.
echo ============================================================
echo  Stratum AI - Edition Builder
echo ============================================================
echo.

if "%EDITION%"=="clean" (
    echo Cleaning build directory...
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    echo Done!
    goto :eof
)

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

if "%EDITION%"=="starter" call :build_edition starter
if "%EDITION%"=="professional" call :build_edition professional
if "%EDITION%"=="enterprise" call :build_edition enterprise
if "%EDITION%"=="all" (
    call :build_edition starter
    call :build_edition professional
    call :build_edition enterprise
)

echo.
echo ============================================================
echo  Build Complete!
echo ============================================================
echo.
echo Output directory: %BUILD_DIR%
echo.
dir "%BUILD_DIR%\stratum-ai-*" /b 2>nul
echo.

goto :eof

REM =============================================================================
REM Build Edition Function
REM =============================================================================
:build_edition
set ED=%1
set OUTPUT=%BUILD_DIR%\stratum-ai-%ED%

echo.
echo Building %ED% edition...
echo.

REM Clean and create output directory
if exist "%OUTPUT%" rmdir /s /q "%OUTPUT%"
mkdir "%OUTPUT%"

REM Copy edition files
echo   Copying edition config...
copy "%SCRIPT_DIR%%ED%\.env.example" "%OUTPUT%\" >nul
copy "%SCRIPT_DIR%%ED%\docker-compose.yml" "%OUTPUT%\" >nul
copy "%SCRIPT_DIR%%ED%\README.md" "%OUTPUT%\" >nul

REM Copy backend
echo   Copying backend...
xcopy "%ROOT_DIR%\backend" "%OUTPUT%\backend\" /e /i /q /exclude:%SCRIPT_DIR%exclude.txt >nul 2>&1

REM Copy frontend (without node_modules)
echo   Copying frontend...
xcopy "%ROOT_DIR%\frontend" "%OUTPUT%\frontend\" /e /i /q /exclude:%SCRIPT_DIR%exclude.txt >nul 2>&1

REM Copy ML models
echo   Copying ML models...
if exist "%ROOT_DIR%\ml_service\models" (
    xcopy "%ROOT_DIR%\ml_service\models" "%OUTPUT%\ml_service\models\" /e /i /q >nul 2>&1
)

REM Copy scripts
echo   Copying scripts...
xcopy "%ROOT_DIR%\scripts" "%OUTPUT%\scripts\" /e /i /q >nul 2>&1

REM Copy docs
echo   Copying docs...
xcopy "%ROOT_DIR%\docs" "%OUTPUT%\docs\" /e /i /q >nul 2>&1

REM Create version file
echo %ED%-%date:~10,4%%date:~4,2%%date:~7,2% > "%OUTPUT%\VERSION"

REM Create start script
(
echo @echo off
echo if not exist .env ^(
echo     echo Creating .env from .env.example...
echo     copy .env.example .env
echo     echo Please edit .env with your configuration, then run this script again.
echo     pause
echo     exit /b
echo ^)
echo echo Starting Stratum AI %ED%...
echo docker compose up -d
echo echo.
echo echo Stratum AI is starting...
echo echo Frontend: http://localhost:5173
echo echo API Docs: http://localhost:8000/docs
echo pause
) > "%OUTPUT%\start.bat"

REM Create stop script
(
echo @echo off
echo echo Stopping Stratum AI...
echo docker compose down
echo pause
) > "%OUTPUT%\stop.bat"

echo   [SUCCESS] %ED% edition built: stratum-ai-%ED%
echo.

goto :eof
