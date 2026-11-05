@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto fail

set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%APP_PYTHON%" goto dependencies

set "APP_PYTHON=%~dp0..\..\..\work\venv\Scripts\python.exe"
if exist "%APP_PYTHON%" goto dependencies

set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"
py -3.11 --version >nul 2>&1
if errorlevel 1 goto localpython
py -3.11 -m venv "%~dp0.venv"
if errorlevel 1 goto fail
goto dependencies

:localpython
set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%SYSTEM_PYTHON%" goto nopython
"%SYSTEM_PYTHON%" -m venv "%~dp0.venv"
if errorlevel 1 goto fail

:dependencies
"%APP_PYTHON%" -c "from PySide6 import QtWidgets; import cv2, mediapipe, pydirectinput" >nul 2>&1
if not errorlevel 1 goto run
echo Installing BeControl dependencies...
"%APP_PYTHON%" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 goto fail
"%APP_PYTHON%" -c "from PySide6 import QtWidgets; import cv2, mediapipe, pydirectinput"
if errorlevel 1 goto fail

:run
"%APP_PYTHON%" "%~dp0app.py"
if errorlevel 1 goto fail
exit /b 0

:nopython
echo Python 3.11 was not found. Install 64-bit Python 3.11 and run Start.cmd again.
pause
exit /b 1

:fail
echo BeControl could not start. Review the error message above.
pause
exit /b 1
