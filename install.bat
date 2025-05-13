@echo off
echo Installing BraveVault - Brave Browser Data Migration Tool...
echo ----------------------------------------------
echo.

set SCRIPT_DIR=%~dp0

rem Create a virtual environment
echo Creating a Python virtual environment...
python -m venv "%SCRIPT_DIR%venv"
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

rem Install dependencies
echo Installing dependencies...
pip install -r "%SCRIPT_DIR%requirements.txt"

rem Create a shortcut on the desktop
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\BraveVault.lnk'); $Shortcut.TargetPath = '%SCRIPT_DIR%brave_extractor.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.Description = 'Brave Browser Data Migration Tool'; $Shortcut.Save()"

echo.
echo Installation complete!
echo.
echo You can now run BraveVault using the desktop shortcut or by running:
echo   %SCRIPT_DIR%brave_extractor.bat
echo.

pause 