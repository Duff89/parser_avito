@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "LOGFILE=run.log"
echo === RUN STARTED at %DATE% %TIME% === > "%LOGFILE%"

set "PYTHON_VERSION=3.11.8"
set "PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe"

REM === 1. Check if Python exists ===
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Downloading... >>"%LOGFILE%"
    curl -L -o "%PYTHON_INSTALLER%" "https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%" >>"%LOGFILE%" 2>&1
    if exist "%PYTHON_INSTALLER%" (
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >>"%LOGFILE%" 2>&1
        del "%PYTHON_INSTALLER%"
    ) else (
        echo ERROR: Failed to download Python installer. >>"%LOGFILE%"
        echo ERROR: Failed to download Python installer.
        goto END
    )
)

REM === 2. Ensure pip is available ===
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo pip not found. Installing get-pip.py... >>"%LOGFILE%"
    curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py >>"%LOGFILE%" 2>&1
    python get-pip.py >>"%LOGFILE%" 2>&1
    del get-pip.py
)

REM === 3. Create virtual environment ===
set "VENV_DIR=%SCRIPT_DIR%.venv"
if not exist "%VENV_DIR%" (
    echo Creating virtual environment... >>"%LOGFILE%"
    python -m venv "%VENV_DIR%" >>"%LOGFILE%" 2>&1
) else (
    echo Virtual environment already exists. >>"%LOGFILE%"
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
echo Activated virtual environment: >>"%LOGFILE%"
where python >>"%LOGFILE%"
python -m pip list >>"%LOGFILE%"

REM Install dependencies
if exist requirements.txt (
    echo Installing dependencies from requirements.txt... >>"%LOGFILE%"
    python -m pip install --upgrade pip >>"%LOGFILE%" 2>&1
    python -m pip install -r requirements.txt >>"%LOGFILE%" 2>&1
) else (
    echo requirements.txt not found. Installing flet manually. >>"%LOGFILE%"
    python -m pip install flet >>"%LOGFILE%" 2>&1
)

REM Run the parser
if exist AvitoParser.py (
    echo Running AvitoParser.py... >>"%LOGFILE%"
    python AvitoParser.py >>"%LOGFILE%" 2>&1
    echo AvitoParser.py finished. >>"%LOGFILE%"
) else (
    echo ERROR: AvitoParser.py not found! >>"%LOGFILE%"
    echo ERROR: AvitoParser.py not found!
)

:END
echo. >>"%LOGFILE%"
echo === RUN ENDED at %DATE% %TIME% === >>"%LOGFILE%"
echo.
echo Script finished. See run.log for details.
pause
endlocal
