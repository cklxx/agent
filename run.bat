@echo off

REM Check if .venv exists
IF NOT EXIST .venv (
    echo Virtual environment .venv not found.
    echo Please run the following commands to create it:
    echo   uv venv
    echo   uv sync
    goto :eof
)

REM Activate virtual environment
CALL .venv\Scriptsctivate.bat

REM Run the main application
python api_server.py

REM Deactivate virtual environment (optional, runs when script exits or window closes)
REM CALL .venv\Scripts\deactivate.bat
