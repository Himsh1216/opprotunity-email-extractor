@echo off
rem Opportunity Mail Extractor - Windows launcher. Double-click this file.
rem Everything runs on this computer; nothing is uploaded.
setlocal
cd /d "%~dp0"
title Opportunity Mail Extractor

set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=python"
if not defined PY goto nopython

if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up. This needs internet once and takes about a minute...
  %PY% -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto novenv
".venv\Scripts\python.exe" -c "import openpyxl" >nul 2>nul || ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
".venv\Scripts\python.exe" -c "import openpyxl" >nul 2>nul || goto nopip

".venv\Scripts\python.exe" -m opportunity_extractor %*
echo.
pause
exit /b 0

:nopython
echo Python 3.9 or newer is not installed.
echo Install it from https://www.python.org/downloads/ and, on the first screen of the installer,
echo tick "Add python.exe to PATH". Then double-click this file again.
pause
exit /b 1

:novenv
echo Could not set up Python in this folder. Move the folder somewhere you can write to,
echo for example Documents, and double-click this file again.
pause
exit /b 1

:nopip
echo Could not install openpyxl. Check your internet connection and double-click this file again.
pause
exit /b 1
