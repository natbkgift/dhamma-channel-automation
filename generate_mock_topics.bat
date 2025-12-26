@echo off
chcp 65001 >nul
REM ========================================
REM Generate Mock Topics Database
REM สร้างหัวข้อวิดีโอธรรมะ 20 หัวข้อ
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  📚 Mock Topics Generator - Dhamma Channel                    ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM ========================================
REM Step 1: Reset Production History
REM ========================================
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 0/3: Resetting Production History                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🗑️  Clearing previous production history...

REM Backup old history if exists
if exist "data\production_history.json" (
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set backupdate=%%c%%a%%b)
    for /f "tokens=1-3 delims=:." %%a in ("%TIME%") do (set backuptime=%%a%%b%%c)
    set backuptime=%backuptime: =0%
    
    copy "data\production_history.json" "data\production_history_backup_%backupdate%_%backuptime%.json" >nul 2>&1
    echo    ✅ Backed up old history: production_history_backup_%backupdate%_%backuptime%.json
)

REM Create fresh empty history
echo {"completed": [], "in_progress": [], "failed": [], "total_produced": 0, "last_updated": ""} > "data\production_history.json"
echo    ✅ Production history reset
echo.
timeout /t 2 >nul

REM ========================================
REM Step 2: Generate Mock Topics
REM ========================================
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 1/3: Generating Mock Topics (20 หัวข้อ)                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

"D:/Auto Tool/dhamma-channel-automation/venv/Scripts/python.exe" scripts\mock_topic_generator.py --count 20

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Failed to generate mock topics!
    echo    Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ✅ Mock topics generated!
timeout /t 2 >nul

REM ========================================
REM Step 3: Generate HTML Report
REM ========================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 2/3: Generating HTML Report                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

"D:/Auto Tool/dhamma-channel-automation/venv/Scripts/python.exe" scripts\generate_mock_report.py

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  WARNING: Failed to generate HTML report
    echo    But mock topics are ready in data\mock_topics.json
)

REM ========================================
REM Completion
REM ========================================
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  🎉 MOCK TOPICS READY!                                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📂 Generated Files:
echo    • data\mock_topics.json (20 หัวข้อ)
echo    • data\production_history.json (history tracker)
echo    • reports\mock_topics_report.html (HTML report)
echo.
echo 🌐 Opening HTML Report...
echo.

REM Open HTML report
if exist "reports\mock_topics_report.html" (
    start "" "reports\mock_topics_report.html"
) else (
    echo ⚠️  Report not found. Check reports\ folder manually.
)

echo.
echo ✨ Next Steps:
echo    1. Review topics in HTML report
echo    2. Run create_video.bat to start producing videos
echo    3. Topics will be used in order (no duplicates!)
echo.
pause
