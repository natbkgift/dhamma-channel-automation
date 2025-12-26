# 🚀 Quick Start Guide - Dhamma Channel Automation

คู่มือเริ่มต้นใช้งานอย่างรวดเร็วสำหรับระบบอัตโนมัติ ธรรมะดีดี

## 📋 ข้อกำหนดเบื้องต้น

- Python 3.11 หรือใหม่กว่า
- Git
- Windows PowerShell (หรือ Terminal ที่รองรับ)

## 🔧 การติดตั้ง (ทำแล้ว ✅)

```powershell
# 1. เปิด PowerShell และไปยังโฟลเดอร์โปรเจกต์
cd "d:\Auto Tool\dhamma-channel-automation"

# 2. เปิดใช้งาน virtual environment
.\venv\Scripts\Activate.ps1

# 3. ตรวจสอบว่าติดตั้งสำเร็จ
python -m cli.main version
```

## 🎯 การใช้งานพื้นฐาน

### 1️⃣ วิเคราะห์เทรนด์ด้วย TrendScoutAgent

```powershell
# รันคำสั่งวิเคราะห์เทรนด์
python -m cli.main trend-scout `
  --input src/agents/trend_scout/mock_input.json `
  --out output/result.json

# ดูผลลัพธ์
cat output/result.json
```

**สิ่งที่จะได้:**
- 📊 หัวข้อคอนเทนต์ 15 หัวข้อ จัดอันดับตามคะแนน
- 🎯 คะแนนรวมและคะแนนย่อย (search_intent, freshness, evergreen, brand_fit)
- 📈 การดูคาดการณ์ 14 วัน
- 💡 เหตุผลและคำแนะนำ

### 2️⃣ สร้างซับไตเติ้ลด้วย LocalizationSubtitleAgent

สร้างไฟล์ Python ใหม่ (เช่น `test_subtitle.py`):

```python
import sys
from pathlib import Path

# เพิ่ม src ไปใน Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.localization_subtitle import (
    LocalizationSubtitleAgent,
    LocalizationSubtitleInput,
    SubtitleSegment
)

# สร้าง agent
agent = LocalizationSubtitleAgent()

# เตรียมข้อมูล
input_data = LocalizationSubtitleInput(
    base_start_time="00:00:05,000",
    approved_script=[
        SubtitleSegment(
            segment_type="intro",
            text="ยินดีต้อนรับสู่ธรรมะดีดี",
            est_seconds=5
        ),
        SubtitleSegment(
            segment_type="teaching",
            text="วันนี้เราจะมาเรียนรู้เรื่องการฝึกสมาธิ",
            est_seconds=7
        ),
    ],
)

# รัน agent
result = agent.run(input_data)

# แสดงผลลัพธ์
print("📝 ไฟล์ SRT:")
print(result.srt)
print("\n🌍 สรุปภาษาอังกฤษ:")
print(result.english_summary)
print(f"\n📊 Segments: {result.meta.segments_count}")
print(f"⏱️ ระยะเวลา: {result.meta.duration_total} วินาที")
```

รันด้วยคำสั่ง:
```powershell
python test_subtitle.py
```

### 3️⃣ ดูข้อมูลระบบ

```powershell
# ดูเวอร์ชัน
python -m cli.main version

# ดูการตั้งค่า
python -m cli.main config-info

# ดูความช่วยเหลือ
python -m cli.main --help
```

## 🧪 รัน Tests

```powershell
# รัน tests ทั้งหมด
pytest

# รัน tests เฉพาะ TrendScoutAgent
pytest tests/test_trend_scout_agent.py -v

# รัน tests เฉพาะ LocalizationSubtitleAgent
pytest tests/test_localization_subtitle_agent.py -v

# รัน tests พร้อม coverage
pytest --cov=src --cov=cli --cov-report=html
```

## 📁 โครงสร้างไฟล์สำคัญ

```
dhamma-channel-automation/
├── src/agents/
│   ├── trend_scout/
│   │   ├── agent.py              # Agent หลัก
│   │   ├── model.py              # Data models
│   │   └── mock_input.json       # ข้อมูลตัวอย่าง
│   └── localization_subtitle/
│       ├── agent.py              # Agent หลัก
│       └── model.py              # Data models
├── cli/
│   └── main.py                   # CLI interface
├── output/                       # ผลลัพธ์ที่สร้าง
├── tests/                        # Unit tests
└── prompts/                      # Prompt templates
```

## 💡 เคล็ดลับการใช้งาน

### ✅ แก้ไข Input Data
แก้ไขไฟล์ `src/agents/trend_scout/mock_input.json` เพื่อทดสอบกับข้อมูลของคุณเอง:

```json
{
  "keywords": ["ธรรมะ", "สมาธิ", "ปล่อยวาง"],
  "google_trends": [...],
  "youtube_trending_raw": [...],
  ...
}
```

### ✅ บันทึกผลลัพธ์
ผลลัพธ์จะถูกบันทึกในโฟลเดอร์ `output/` อัตโนมัติ:

```powershell
# ดูไฟล์ผลลัพธ์
ls output/

# อ่านไฟล์ JSON
cat output/result.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### ✅ ปรับแต่ง Configuration
แก้ไขการตั้งค่าใน `src/automation_core/config.py`:

```python
class Config(BaseSettings):
    app_name: str = "dhamma-automation"
    log_level: str = "INFO"
    data_dir: str = "./data"
    log_file: str = "logs/app.log"
```

## 🎨 Rich Output

CLI ใช้ Rich library แสดงผลสวยงาม:
- 🎨 สีสันตามประเภทข้อมูล
- 📊 ตารางแสดงผลลัพธ์
- ⚡ Progress indicators
- ✅ สถานะความสำเร็จ/ล้มเหลว

## 🔍 การแก้ไขปัญหา

### ปัญหา: Module not found
```powershell
# ตรวจสอบว่า venv เปิดใช้งาน
.\venv\Scripts\Activate.ps1

# ติดตั้งใหม่ในโหมด editable
pip install -e .
```

### ปัญหา: SSL Certificate Error
```powershell
# ติดตั้งด้วย trusted hosts
pip install --trusted-host pypi.org `
  --trusted-host pypi.python.org `
  --trusted-host files.pythonhosted.org `
  -e .
```

### ปัญหา: Tests ไม่ผ่าน
```powershell
# ตรวจสอบว่าติดตั้ง dev dependencies
pip install -e ".[dev]"

# รัน tests แบบละเอียด
pytest -vv --tb=long
```

## 📚 เอกสารเพิ่มเติม

- 📖 [README.md](README.md) - เอกสารหลักโครงการ
- 📊 [SYSTEM_STATUS.md](SYSTEM_STATUS.md) - สถานะและผลการทดสอบ
- 🏗️ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - สถาปัตยกรรมระบบ
- 🔄 [docs/AGENT_LIFECYCLE.md](docs/AGENT_LIFECYCLE.md) - วงจรการทำงาน Agent
- 📝 [docs/PROMPTS_OVERVIEW.md](docs/PROMPTS_OVERVIEW.md) - คู่มือ Prompt

## 🆘 ขอความช่วยเหลือ

```powershell
# ดู help ของคำสั่ง
python -m cli.main --help
python -m cli.main trend-scout --help

# รัน pytest ด้วย verbose
pytest -vv

# ตรวจสอบ log files
cat logs/app.log
```

## 🎉 ขั้นตอนถัดไป

เมื่อคุณพร้อมแล้ว:

1. 📖 อ่าน [docs/ROADMAP.md](docs/ROADMAP.md) เพื่อดูแผนงานถัดไป
2. 🛠️ ลองเพิ่ม Agent ใหม่ตาม [docs/AGENT_LIFECYCLE.md](docs/AGENT_LIFECYCLE.md)
3. 🔧 ปรับแต่ง prompts ใน `prompts/` directory
4. 🧪 เขียน tests เพิ่มเติมใน `tests/` directory

---

**สนุกกับการสร้าง AI Agents! 🚀✨**
