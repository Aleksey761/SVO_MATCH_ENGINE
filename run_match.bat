@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "INPUT_DIR=%SCRIPT_DIR%data"
set "OUTPUT_DIR=%SCRIPT_DIR%output"
set "VENV_ACTIVATE=%SCRIPT_DIR%.venv\Scripts\activate.bat"
set "EXIT_CODE=0"

echo ========================================
echo SVO Match Engine - One Click Run
echo ========================================

if not exist "%VENV_ACTIVATE%" (
    echo ERROR: Virtual environment not found at .venv\Scripts\activate.bat
    set "EXIT_CODE=10"
    goto :end
)

if not exist "%INPUT_DIR%" (
    echo ERROR: Input directory not found: %INPUT_DIR%
    set "EXIT_CODE=11"
    goto :end
)

set "MASTER_COUNT=0"
for /f "usebackq delims=" %%F in (`dir /b /a-d "%INPUT_DIR%\*.xlsx" 2^>nul ^| findstr /i "master"`) do (
    set /a MASTER_COUNT+=1
)

if not "!MASTER_COUNT!"=="1" (
    echo ERROR: Expected exactly one MASTER workbook in %INPUT_DIR%, found !MASTER_COUNT!.
    set "EXIT_CODE=12"
    goto :end
)

set "ARRIVAL_COUNT=0"
for /f "usebackq delims=" %%F in (`dir /b /a-d "%INPUT_DIR%\*.xlsx" 2^>nul ^| findstr /i "arrival"`) do (
    set /a ARRIVAL_COUNT+=1
)

if not "!ARRIVAL_COUNT!"=="1" (
    echo ERROR: Expected exactly one ARRIVAL workbook in %INPUT_DIR%, found !ARRIVAL_COUNT!.
    set "EXIT_CODE=13"
    goto :end
)

if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

call "%VENV_ACTIVATE%"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    set "EXIT_CODE=14"
    goto :end
)

echo Running matcher...
python "%SCRIPT_DIR%match.py"
if errorlevel 1 (
    echo.
    echo RESULT: FAILED
    echo ERROR: Arrival pipeline execution failed.
    set "EXIT_CODE=20"
    goto :end
)

echo.
echo RESULT: SUCCESS
echo INFO: Arrival matching completed. Check output folder for ARRIVAL_MATCH_*.xlsx.
set "EXIT_CODE=0"

:end
echo Exit code: %EXIT_CODE%
echo.
pause
exit /b %EXIT_CODE%
