@echo off

rem Simple Launcher for Douban Movie Spider

cls
echo ============================
echo   Douban Movie Top250 Spider
 echo     GUI Launcher
 echo ============================

rem Check Python availability
echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found!
    echo Please install Python 3.6 or higher
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

rem Show Python version
echo Python version:
python --version
echo.

rem Start the application
echo Starting GUI application...
echo If failed, error messages will be shown below
echo.

rem Run the program
python gui_app.py

rem Check exit status
if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to start application! Error code: %errorlevel%
    echo Possible solutions:
    echo 1. Install dependencies: pip install requests pandas matplotlib seaborn
    echo 2. Check Python compatibility
    echo 3. Verify gui_app.py file integrity
    pause
) else (
    echo Application exited normally
    pause
)