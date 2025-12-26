@echo off
REM ========================================================================
REM Full Auto Video Production - Path C
REM Complete automation: Content → TTS → Video → Thumbnail → Upload
REM ========================================================================

echo.
echo ========================================================================
echo 🚀 FULL AUTO VIDEO PRODUCTION - PATH C
echo ========================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

REM Optional: Specify topic
set TOPIC=%1

REM Run orchestrator
REM Check venv
if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    echo 💡 Create venv first: python -m venv venv
    pause
    exit /b 1
)

REM Run orchestrator
if "%TOPIC%"=="" (
    echo 📌 No topic specified - will select from database
    venv\Scripts\python.exe scripts/full_auto_orchestrator.py
) else (
    echo 📌 Topic: %TOPIC%
    venv\Scripts\python.exe scripts/full_auto_orchestrator.py --topic "%TOPIC%"
)

REM Check result
if errorlevel 1 (
    echo.
    echo ❌ Production failed!
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo ✅ FULL AUTO PRODUCTION COMPLETED!
echo ========================================================================
echo.
echo 📂 Check output/ folder for results
echo 📄 Open PRODUCTION_GUIDE.html for details
echo.
pause
