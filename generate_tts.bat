@echo off
cd /d "D:Auto Tooldhamma-channel-automation"
call venv\Scripts\activate.bat
python scripts\tts_generator.py --script "D:Auto Tooldhamma-channel-automationaudioproduction_20251104_165031ecording_script_SIMPLE.txt" --output "D:Auto Tooldhamma-channel-automationaudioproduction_20251104_165031oiceover_ai.mp3" --voice alloy --speed 1.0
if %errorlevel% equ 0 (
    echo.
    echo ===================================
    echo    ✅ สร้างเสียง AI สำเร็จ!
    echo ===================================
    echo    📄 ไฟล์: voiceover_ai.mp3
    echo    📁 ที่: D:Auto Tooldhamma-channel-automationaudioproduction_20251104_165031
    echo ===================================
) else (
    echo.
    echo ===================================
    echo    ❌ เกิดข้อผิดพลาด
    echo ===================================
)
echo.
pause