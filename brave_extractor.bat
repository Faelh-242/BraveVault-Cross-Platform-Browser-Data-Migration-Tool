@echo off
echo BraveVault - Brave Browser Data Migration Tool
echo -------------------------------
echo.

if not exist "%~dp0venv" (
    echo Creating virtual environment...
    python -m venv "%~dp0venv"
    call "%~dp0venv\Scripts\activate.bat"
    echo Installing dependencies...
    pip install -r "%~dp0requirements.txt"
) else (
    call "%~dp0venv\Scripts\activate.bat"
)

echo.
if "%1"=="gui" (
    echo Starting BraveVault GUI...
    python "%~dp0brave_extractor_gui.py"
) else (
    echo Running BraveVault CLI...
    echo.
    python "%~dp0brave_extractor.py" %*
)

echo.
pause 