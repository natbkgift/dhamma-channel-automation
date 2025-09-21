# 🙏 ระบบอัตโนมัติ ธรรมะดีดี (Dhamma Channel Automation)

[![CI](https://github.com/natbkgift/dhamma-channel-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/natbkgift/dhamma-channel-automation/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue)](https://natbkgift.github.io/dhamma-channel-automation)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ระบบการผลิตคอนเทนต์ช่อง YouTube "ธรรมะดีดี" ด้วย AI Agents เพื่อสร้างรายได้เป้าหมาย **100,000 บาท/เดือน** จาก YouTube AdSense โดยใช้ Automation + AI Agent ครอบคลุมตั้งแต่การวิเคราะห์เทรนด์ไปจนถึงการสร้างเนื้อหาสมบูรณ์

## 🎯 วัตถุประสงค์

- **เป้าหมายรายได้**: 100,000 บาท/เดือน จาก YouTube Partner Program
- **เนื้อหาเป้าหมาย**: 20-30 วิดีโอ/เดือน ด้วยคุณภาพสูง
- **ลดเวลาผลิต**: 70% โดยใช้ AI Automation
- **เนื้อหาคุณภาพ**: นำหลักธรรมมาประยุกต์ในชีวิตประจำวัน

## ✨ คุณสมบัติหลัก (Phase 0)

### 🔍 TrendScoutAgent
- วิเคราะห์เทรนด์จากหลายแหล่ง (Google Trends, YouTube, ความคิดเห็น)
- สร้างหัวข้อคอนเทนต์ที่น่าสนใจ 15 หัวข้อ
- ให้คะแนนตามมิติต่างๆ (search intent, freshness, evergreen, brand fit)
- จัดลำดับความสำคัญพร้อมเหตุผล

### 💻 CLI Interface
- รันคำสั่งผ่าน command line ง่ายๆ
- แสดงผลสวยงามด้วย Rich tables และสี
- Progress indicators และ error handling

### 🧪 Testing & Quality
- Unit tests ครอบคลุม 85%+
- Integration tests สำหรับ CLI
- CI/CD pipeline บน GitHub Actions
- Code linting ด้วย ruff และ mypy

### 📚 Documentation
- เอกสารครบครันเป็นภาษาไทย 15+ หน้า
- MkDocs พร้อม Material theme
- คู่มือการเพิ่ม Agent ใหม่
- Troubleshooting guide

## 🚀 เริ่มต้นใช้งาน

### ข้อกำหนดระบบ
- Python 3.11 หรือใหม่กว่า
- Git
- 512MB RAM
- 100MB disk space

### การติดตั้ง

```bash
# 1. Clone repository
git clone https://github.com/natbkgift/dhamma-channel-automation.git
cd dhamma-channel-automation

# 2. สร้าง virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# หรือ venv\Scripts\activate  # Windows

# 3. ติดตั้ง dependencies
pip install -e .

# 4. ติดตั้ง development dependencies (ถ้าต้องการ)
pip install -e ".[dev]"
```

### การใช้งานเบื้องต้น

```bash
# รัน TrendScoutAgent
python -m cli.main trend-scout \
  --input src/agents/trend_scout/mock_input.json \
  --out output/result.json

# ดูข้อมูลเวอร์ชัน
python -m cli.main version

# ดูการตั้งค่า
python -m cli.main config-info
```

### ตัวอย่างผลลัพธ์

```json
{
  "generated_at": "2024-09-21T12:00:00Z",
  "topics": [
    {
      "rank": 1,
      "title": "ปล่อยวางก่อนหลับ",
      "pillar": "ธรรมะประยุกต์",
      "predicted_14d_views": 12000,
      "scores": {
        "search_intent": 0.82,
        "freshness": 0.74,
        "evergreen": 0.65,
        "brand_fit": 0.93,
        "composite": 0.785
      },
      "reason": "ค้นสูง + ปัญหาที่คนพบบ่อยกลางคืน"
    }
  ]
}
```

## 📁 โครงสร้างโครงการ

```
dhamma-channel-automation/
├── 📄 README.md                    # เอกสารหลัก
├── ⚙️ pyproject.toml               # การตั้งค่าโครงการ
├── 📜 LICENSE                      # ใบอนุญาต MIT
├── 🔧 mkdocs.yml                   # การตั้งค่าเอกสาร
├── 📚 docs/                        # เอกสารทั้งหมด
│   ├── index.md                    # หน้าแรก
│   ├── ARCHITECTURE.md             # สถาปัตยกรรม
│   ├── AGENT_LIFECYCLE.md          # วงจรการทำงาน Agent
│   ├── PROMPTS_OVERVIEW.md         # คู่มือ Prompt
│   ├── ROADMAP.md                  # แผนงาน
│   └── TROUBLESHOOTING.md          # แก้ไขปัญหา
├── 📝 prompts/                     # Prompt templates
│   └── trend_scout_v1.txt
├── 🧠 src/                         # Source code หลัก
│   ├── automation_core/            # โมดูลหลัก
│   │   ├── __init__.py
│   │   ├── base_agent.py           # คลาสพื้นฐาน Agent
│   │   ├── config.py               # การตั้งค่า
│   │   ├── logging.py              # ระบบ logging
│   │   ├── prompt_loader.py        # โหลด prompt
│   │   └── utils/                  # ฟังก์ชันช่วยเหลือ
│   │       ├── scoring.py          # การคำนวณคะแนน
│   │       └── text.py             # ประมวลผลข้อความ
│   └── agents/                     # AI Agents
│       └── trend_scout/            # TrendScoutAgent
│           ├── __init__.py
│           ├── model.py            # Pydantic models
│           ├── agent.py            # ตัว Agent หลัก
│           ├── prompt_template.md  # คู่มือ mapping
│           └── mock_input.json     # ข้อมูลตัวอย่าง
├── 💻 cli/                         # Command line interface
│   ├── __init__.py
│   └── main.py                     # CLI หลัก
├── 🧪 tests/                       # Tests
│   ├── test_trend_scout_agent.py   # ทดสอบ Agent
│   ├── test_prompt_loading.py      # ทดสอบ prompt loading
│   └── test_scoring_utils.py       # ทดสอบการคำนวณ
├── 📤 output/                      # ไฟล์ผลลัพธ์
└── 🤖 .github/workflows/           # CI/CD
    └── ci.yml                      # GitHub Actions
```

## 🧪 การทดสอบ

```bash
# รัน tests ทั้งหมด
pytest

# รัน tests พร้อมดู coverage
pytest --cov=src --cov=cli --cov-report=html

# รัน tests เฉพาะ TrendScoutAgent
pytest tests/test_trend_scout_agent.py -v

# รัน linting
ruff check .

# รัน type checking
mypy src/ cli/
```

## 📚 สร้างเอกสาร

```bash
# ติดตั้ง MkDocs dependencies
pip install mkdocs mkdocs-material

# Preview เอกสารในเครื่อง
mkdocs serve
# เปิด http://localhost:8000

# Build เอกสารสำหรับ production
mkdocs build
```

## 🔧 การตรวจคุณภาพ (Preflight & CI)

### 🚀 Preflight Checks

ระบบตรวจสอบคุณภาพโค้ดก่อนเปิด PR:

```bash
# Preflight เต็ม (ใช้ก่อนเปิด PR)
bash scripts/preflight.sh

# หรือใช้ Makefile
make preflight
```

**ขั้นตอนที่ตรวจสอบ:**
1. ✅ Python version (≥3.11)
2. ✅ Ruff linting
3. ✅ Code formatting
4. ✅ Pytest ทั้งหมด (พร้อม coverage)
5. ✅ MkDocs documentation build
6. ✅ CLI Agent execution test
7. ✅ Output validation
8. ✅ MyPy type checking (non-strict)

### ⚡ Quick Check

สำหรับการตรวจสอบรวดเร็ว (pre-commit):

```bash
# Quick preflight
bash scripts/preflight_quick.sh

# หรือใช้ Makefile
make quick
```

### 🎯 Pre-commit Hooks (Optional)

ตั้งค่า pre-commit hooks เพื่อตรวจสอบอัตโนมัติ:

```bash
# ติดตั้ง pre-commit
pip install pre-commit

# เปิดใช้งาน hooks
pre-commit install

# ทดสอบ (รันกับไฟล์ทั้งหมด)
pre-commit run --all-files
```

### 📊 CI Pipeline

CI จะรันอัตโนมัติเมื่อ push หรือเปิด PR:

- **Lint**: ตรวจสอบ code style (Python 3.11, 3.12)
- **Test**: รัน unit tests พร้อม coverage
- **Docs**: Build documentation (skip ด้วย `[skip-docs]`)
- **Preflight**: ตรวจสอบระบบครบถ้วน

### 🛠️ Commands รวดเร็ว

```bash
# การตรวจสอบพื้นฐาน
make lint          # Ruff linting
make format        # Code formatting
make test          # Unit tests
make test-cov      # Tests + coverage

# Agent & Documentation
make agent         # รัน TrendScout
make docs          # Build docs
make serve-docs    # Serve docs locally

# ทำความสะอาด
make clean         # ลบ cache files
```

## 🗺️ แผนงานโครงการ

### ✅ Phase 0: Foundation (เสร็จแล้ว)
- [x] TrendScoutAgent พร้อม mock LLM simulation
- [x] CLI interface พร้อม Rich output
- [x] Unit testing ครอบคลุม 85%+
- [x] เอกสารภาษาไทยครบครัน
- [x] CI/CD pipeline

### 🚧 Phase 1: Topic Prioritization (ตุลาคม-พฤศจิกายน 2024)
- [ ] TopicPrioritizerAgent จัดลำดับความสำคัญ
- [ ] RetrievalAgent ค้นหาข้อมูลสนับสนุน
- [ ] การเชื่อมต่อ API ภายนอก (YouTube, Google Trends)
- [ ] ระบบ caching และ rate limiting

### 🎯 Phase 2: Content Generation (ธันวาคม 2024-มกราคม 2025)
- [ ] OutlineAgent สร้างโครงเรื่อง
- [ ] ScriptWriterAgent เขียนสคริปต์วิดีโอ
- [ ] Workflow engine จัดการ pipeline
- [ ] Template system สำหรับรูปแบบเนื้อหา

### 📊 Phase 3: Quality & Analytics (กุมภาพันธ์-มีนาคม 2025)
- [ ] ValidatorAgent ตรวจสอบคุณภาพ
- [ ] AnalyticsAgent วิเคราะห์ผลงาน
- [ ] การปรับปรุงอัตโนมัติตามผลลัพธ์
- [ ] Dashboard สำหรับติดตามผล

## 🤝 การมีส่วนร่วม

เรายินดีรับการมีส่วนร่วมจากชุมชน! 

### ขั้นตอนการ Contribute

1. **Fork repository** และ clone ไปยังเครื่องของคุณ
2. **สร้าง branch** สำหรับฟีเจอร์ใหม่: `git checkout -b feature/amazing-agent`
3. **เขียน tests** สำหรับโค้ดใหม่
4. **ตรวจสอบ code quality**: `ruff check . && pytest`
5. **Commit changes**: `git commit -m "Add amazing new agent"`
6. **Push และส่ง Pull Request**

### มาตรฐานโค้ด

- ใช้ **ภาษาไทย** ในความคิดเห็นและเอกสาร
- ตั้งชื่อ **ฟังก์ชันและตัวแปร** เป็นภาษาอังกฤษ
- ทำตาม **PEP 8** และใช้ **type hints**
- เขียน **tests** สำหรับโค้ดใหม่
- **Documentation** ครบถ้วน

### การเพิ่ม Agent ใหม่

อ่านคู่มือฉบับเต็ม: [Agent Lifecycle Guide](docs/AGENT_LIFECYCLE.md)

```bash
# 1. สร้างโฟลเดอร์ Agent
mkdir -p src/agents/my_agent

# 2. สร้างไฟล์หลัก
touch src/agents/my_agent/{__init__.py,model.py,agent.py}

# 3. สร้าง prompt template
touch prompts/my_agent_v1.txt

# 4. เขียน tests
touch tests/test_my_agent.py

# 5. อัปเดตเอกสาร
# แก้ไข docs/PROMPTS_OVERVIEW.md และ docs/ROADMAP.md
```

## 🛠️ เทคโนโลยีที่ใช้

### Core Technologies
- **Python 3.11+**: ภาษาหลัก
- **Pydantic**: Data validation และ serialization
- **Typer**: CLI framework พร้อม auto-completion
- **Rich**: Beautiful terminal output
- **pytest**: Testing framework

### Development Tools
- **ruff**: Super-fast Python linter
- **mypy**: Static type checker
- **MkDocs**: Documentation generator
- **GitHub Actions**: CI/CD pipeline

### AI & ML (สำหรับอนาคต)
- **OpenAI GPT**: Language model integration
- **Anthropic Claude**: Alternative LLM option
- **Embedding models**: สำหรับ content similarity
- **scikit-learn**: ML utilities

## 📞 ติดต่อและสนับสนุน

- **🐛 Bug Reports**: [GitHub Issues](https://github.com/natbkgift/dhamma-channel-automation/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/natbkgift/dhamma-channel-automation/discussions)
- **📖 เอกสาร**: [https://natbkgift.github.io/dhamma-channel-automation](https://natbkgift.github.io/dhamma-channel-automation)
- **🔧 Troubleshooting**: [แก้ไขปัญหา](docs/TROUBLESHOOTING.md)

## 📄 ใบอนุญาต

โครงการนี้ใช้ใบอนุญาต [MIT License](LICENSE) - ซึ่งหมายความว่า:

- ✅ ใช้งานเชิงพาณิชย์ได้
- ✅ ดัดแปลงและแจกจ่ายได้
- ✅ ใช้ใน private projects ได้
- ❌ ไม่มีการรับประกัน
- ❌ ผู้พัฒนาไม่รับผิดชอบความเสียหาย

## 🌟 ขอบคุณ

ขอบคุณทุกคนที่มีส่วนร่วมในการพัฒนาโครงการนี้:

- **Core Team**: การออกแบบสถาปัตยกรรมและการพัฒนา
- **Community**: ความคิดเห็นและการทดสอบ
- **Open Source Libraries**: เครื่องมือที่ยอดเยี่ยมที่ทำให้โครงการนี้เป็นไปได้

---

## 🎉 สถานะโครงการ

**Phase 0 Complete!** 🎊

- ✅ TrendScoutAgent ใช้งานได้เต็มประสิทธิภาพ
- ✅ CLI interface พร้อม Rich output สวยงาม
- ✅ Test coverage 85%+ พร้อม CI/CD
- ✅ เอกสารภาษาไทยครบครัน 15+ หน้า
- ✅ พร้อมสำหรับการพัฒนา Phase 1

**ตัวอย่างการใช้งานจริง**:
```bash
# ใช้งานได้ทันที!
python -m cli.main trend-scout \
  --input src/agents/trend_scout/mock_input.json \
  --out output/my_topics.json
```

💡 **หมายเหตุ**: โครงการนี้อยู่ในระยะพัฒนาอย่างต่อเนื่อง เหมาะสำหรับการทดลองและพัฒนาต่อยอด สำหรับการใช้งานจริงใน production ควรรอจนกว่า Phase 2 จะเสร็จสมบูรณ์