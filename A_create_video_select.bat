@echo off
chcp 65001 >nul
REM ========================================
REM Dhamma Video Creation - With Topic Selection
REM Path A (Manual/Free) - TOP 5 Selection
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  🎬 Dhamma Video Creation - เลือกหัวข้อ TOP 5                 ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM ========================================
REM Step 0: Check and Show TOP 5 Topics
REM ========================================
echo 🔍 กำลังโหลด Mock Topics Database...
echo.

REM Check if mock topics exist
if not exist "data\mock_topics.json" (
    echo ❌ ERROR: Mock topics not found!
    echo.
    echo 💡 Please run generate_mock_topics.bat first to create topics database.
    echo.
    pause
    exit /b 1
)

REM Show TOP 5 upcoming topics
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  📋 TOP 5 หัวข้อถัดไป (เรียงตาม Priority)                     ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

"%~dp0venv\Scripts\python.exe" scripts\topic_database.py upcoming --count 5

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: ไม่สามารถโหลดหัวข้อได้!
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo 📌 เลือกหัวข้อที่ต้องการสร้าง:
echo.
echo    1 = หัวข้ออันดับ 1 (Priority สูงสุด)
echo    2 = หัวข้ออันดับ 2
echo    3 = หัวข้ออันดับ 3
echo    4 = หัวข้ออันดับ 4
echo    5 = หัวข้ออันดับ 5
echo    N = ทำหัวข้อถัดไปอัตโนมัติ (แนะนำ)
echo    X = ยกเลิก
echo.

set /p CHOICE="เลือก (1-5, N, X): "

if /i "%CHOICE%"=="X" (
    echo ยกเลิกแล้ว
    exit /b 0
)

if /i "%CHOICE%"=="N" (
    echo.
    echo ✅ เลือกหัวข้อถัดไปอัตโนมัติ...
    goto AUTO_SELECT
)

REM Validate choice
if "%CHOICE%"=="1" goto SELECT_TOPIC
if "%CHOICE%"=="2" goto SELECT_TOPIC
if "%CHOICE%"=="3" goto SELECT_TOPIC
if "%CHOICE%"=="4" goto SELECT_TOPIC
if "%CHOICE%"=="5" goto SELECT_TOPIC

echo.
echo ❌ ตัวเลือกไม่ถูกต้อง! กรุณาเลือก 1-5, N, หรือ X
pause
exit /b 1

:AUTO_SELECT
REM Get next topic automatically (highest priority)
for /f "usebackq delims=" %%i in (`"%~dp0venv\Scripts\python.exe" scripts\topic_database.py --topics data\mock_topics.json --history data\production_history.json next --title-only`) do set "TOPIC_TITLE=%%i"

if "%TOPIC_TITLE%"=="" (
    echo 🎉 All topics completed!
    echo.
    echo 💡 Run generate_mock_topics.bat to create new topics.
    pause
    exit /b 0
)

goto START_PRODUCTION

:SELECT_TOPIC
REM Get selected topic from upcoming list
set SELECTED_INDEX=%CHOICE%

REM Use Python to get specific topic by index
for /f "delims=" %%i in ('"%~dp0venv\Scripts\python.exe" -c "import json, pathlib; base=pathlib.Path(r'%~dp0'); data=json.load(open(base/'data'/'mock_topics.json',encoding='utf-8')); hist=json.load(open(base/'data'/'production_history.json',encoding='utf-8')) if (base/'data'/'production_history.json').exists() else {'completed':[]}; completed={r['topic_id'] for r in hist['completed']}; upcoming=[t for t in sorted(data['topics'],key=lambda x:x['priority'],reverse=True) if t['id'] not in completed]; print(upcoming[%SELECTED_INDEX%-1]['title'] if len(upcoming)>=%SELECTED_INDEX% else '')"') do set TOPIC_TITLE=%%i

if "%TOPIC_TITLE%"=="" (
    echo.
    echo ❌ ไม่พบหัวข้อลำดับที่ %SELECTED_INDEX%
    pause
    exit /b 1
)

:START_PRODUCTION
echo.
echo ══════════════════════════════════════════════════════════════
echo 🎯 หัวข้อที่เลือก: %TOPIC_TITLE%
echo ══════════════════════════════════════════════════════════════
echo.
echo กด Enter เพื่อเริ่มสร้างวิดีโอ...
pause >nul
echo.

REM Generate run ID with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-3 delims=:." %%a in ("%TIME%") do (set mytime=%%a%%b%%c)
set mytime=%mytime: =0%
set RUN_ID=production_%mydate%_%mytime%
echo 🆔 Run ID: %RUN_ID%
echo.

REM ========================================
REM Step 1: AI Content Generation (17 Agents)
REM ========================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 1/4: AI Content Generation (17 Agents)                  ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📝 Creating video content using AI agents...
echo 📌 Topic: %TOPIC_TITLE%
echo.

"%~dp0venv\Scripts\python.exe" orchestrator.py --pipeline pipelines\video_complete.yaml --run-id %RUN_ID% --topic "%TOPIC_TITLE%"

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: AI Content Generation failed!
    echo    Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ✅ AI Content Generation completed!
echo    Output: output\%RUN_ID%\
echo.
timeout /t 3 >nul

REM ========================================
REM Step 2: Production Assets Generation
REM ========================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 2/4: Production Assets Generation (Path A)              ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🔧 Generating production-ready files...
echo.

"%~dp0venv\Scripts\python.exe" scripts\production_orchestrator.py --input-dir output\%RUN_ID% --path A

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Production Assets Generation failed!
    echo    Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ✅ Production Assets Generation completed!
echo.
timeout /t 3 >nul

REM ========================================
REM Step 3: Generate HTML Report
REM ========================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 3/4: Generating Production Report                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

"%~dp0venv\Scripts\python.exe" scripts\generate_production_report.py --run-id %RUN_ID%

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  WARNING: Report generation failed, but production files are ready.
    echo    You can still proceed with manual production.
)

REM ========================================
REM Step 4: Update Production History
REM ========================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  STEP 4/4: Updating Production History                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Get topic ID by title
for /f "usebackq delims=" %%i in (`"%~dp0venv\Scripts\python.exe" -c "import json, pathlib; base=pathlib.Path(r'%~dp0'); data=json.load(open(base/'data'/'mock_topics.json',encoding='utf-8')); topic=[t for t in data['topics'] if t['title']==r'%TOPIC_TITLE%']; print(topic[0]['id'] if topic else '')"`) do set "TOPIC_ID=%%i"

if not "%TOPIC_ID%"=="" (
    "%~dp0venv\Scripts\python.exe" scripts\topic_database.py --topics data\mock_topics.json --history data\production_history.json mark --topic-id %TOPIC_ID% --status completed --run-id %RUN_ID% --output-dir output\%RUN_ID%
    
    if %errorlevel% equ 0 (
        echo ✅ Production history updated
        echo    หัวข้อ "%TOPIC_TITLE%" ถูกทำเครื่องหมายว่าเสร็จแล้ว
    ) else (
        echo ⚠️  WARNING: Failed to update history
    )
) else (
    echo ⚠️  WARNING: Cannot find topic ID
)

echo.

REM ========================================
REM Completion
REM ========================================
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  🎉 WORKFLOW COMPLETED SUCCESSFULLY!                          ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📂 Generated Files:
echo    • AI Content:     output\%RUN_ID%\
echo    • Audio Scripts:  audio\%RUN_ID%\
echo    • Video Templates: templates\%RUN_ID%\
echo    • Thumbnail Guide: templates\canva\
echo    • 📄 Production Report: output\%RUN_ID%\PRODUCTION_GUIDE.html
echo.
echo 🌐 Opening Production Report...
echo.

REM Open HTML report in default browser
if exist "output\%RUN_ID%\PRODUCTION_GUIDE.html" (
    start "" "output\%RUN_ID%\PRODUCTION_GUIDE.html"
) else (
    echo ⚠️  Report file not found. Please check output\%RUN_ID%\ folder manually.
)

echo.
echo ✨ Next: Follow the steps in PRODUCTION_GUIDE.html
echo.
echo 💡 TIP: หัวข้อนี้ทำเสร็จแล้ว - ครั้งหน้าจะเลือกหัวข้ออื่นโดยอัตโนมัติ
echo.
pause
