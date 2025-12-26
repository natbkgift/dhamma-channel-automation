# 🤖 โหมดอัตโนมัติ - Dhamma Video Automation Pipeline

คู่มือการใช้งานระบบอัตโนมัติสำหรับสร้างวิดีโอธรรมะแบบ end-to-end

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [ขั้นตอนติดตั้ง](#ขั้นตอนติดตั้ง)
3. [วิธีใช้งาน](#วิธีใช้งาน)
4. [โครงสร้างไฟล์](#โครงสร้างไฟล์)
5. [Agents ในระบบ](#agents-ในระบบ)
6. [ตัวอย่างผลลัพธ์](#ตัวอย่างผลลัพธ์)
7. [การ Customize](#การ-customize)

---

## 🎯 ภาพรวมระบบ

ระบบนี้เป็น **AI Agent Pipeline** ที่ทำงานแบบอัตโนมัติตั้งแต่ต้นจนจบ:

```
Trend Scout → Topic Prioritizer → Research Retrieval → Script Outline 
    ↓
Script Writer → Doctrine Validator → SEO Metadata → Publishing
```

### ✨ จุดเด่น
- ✅ **ใช้งานได้ทันที** - มีข้อมูลจำลองครบ ไม่ต้องรอ API
- ✅ **ตรวจสอบหลักธรรม** - มี Doctrine Validator ตรวจสอบความถูกต้อง
- ✅ **SEO-Ready** - สร้าง metadata พร้อม tags และ description
- ✅ **เอาต์พุตมาตรฐาน** - JSON + Markdown ง่ายต่อการนำไปใช้ต่อ
- ✅ **ติดตามได้** - มี logging และ summary ชัดเจน

---

## 🛠️ ขั้นตอนติดตั้ง

### 1. เตรียม Python Environment

เปิด **PowerShell** และรันคำสั่ง:

```powershell
# เข้าโฟลเดอร์โปรเจกต์
cd "d:\Auto Tool\dhamma-channel-automation"

# สร้าง virtual environment (ถ้ายังไม่มี)
py -m venv venv

# เปิดใช้งาน venv
.\venv\Scripts\Activate.ps1

# ติดตั้ง dependencies
pip install pyyaml
```

### 2. ตรวจสอบไฟล์ที่จำเป็น

```powershell
# ตรวจสอบว่ามีไฟล์ครบ
ls pipelines\video.yaml
ls orchestrator.py
```

---

## 🚀 วิธีใช้งาน

### รันแบบพื้นฐาน (8 agents - เร็ว)

```powershell
# Activate venv (ถ้ายังไม่ได้เปิด)
.\venv\Scripts\Activate.ps1

# รัน pipeline แบบพื้นฐาน
python orchestrator.py --pipeline pipelines\video.yaml --run-id demo1
```

### รันแบบสมบูรณ์ (17 agents - ครบทุก step) ⭐ แนะนำ

```powershell
# รัน complete pipeline
python orchestrator.py --pipeline pipelines\video_complete.yaml --run-id production_v1
```

### รันแบบกำหนด Run ID เอง

```powershell
python orchestrator.py --pipeline pipelines\video_complete.yaml --run-id "mindfulness_20251104"
```

### ดูผลลัพธ์

```powershell
# เข้าโฟลเดอร์ผลลัพธ์
cd output\production_v1

# ดูไฟล์ทั้งหมด
ls

# ดูสรุป pipeline
cat pipeline_summary.json

# ดูสคริปต์ที่ผ่านการตรวจสอบแล้ว
cat script_validated.md

# ดู checklist ก่อนเผยแพร่
cat publish_checklist.md
```

---

## 📁 โครงสร้างไฟล์

### ไฟล์ Input

```
pipelines/
└── video.yaml          # นิยาม pipeline workflow
```

### ไฟล์ Output (ตัวอย่าง: output/final_complete/)

```
output/final_complete/
├── trend_candidates.json          # [1] เทรนด์ที่พบ (5 หัวข้อ)
├── topics_ranked.json             # [2] จัดอันดับเทรนด์
├── research_bundle.json           # [3] อ้างอิงจากพระไตรปิฎก
├── data_enrichment.json           # [4] ⭐ ข้อมูลเสริม (historical, research, tips)
├── outline.md                     # [5] โครงสคริปต์
├── script.md                      # [6] สคริปต์เต็ม
├── script_validated.md            # [7] สคริปต์ที่ผ่านการตรวจ
├── validation_report.json         # [7] รายงานการตรวจสอบหลักธรรม
├── compliance_report.json         # [8] ⭐ รายงานกฎหมายและข้อบังคับ
├── visual_guide.json              # [9] ⭐ คำแนะนำ B-roll, scenes, colors
├── voiceover_guide.json           # [10] ⭐ คำแนะนำพากย์เสียง
├── localization.json              # [11] ⭐ คำแนะนำคำบรรยาย
├── subtitles_th.srt               # [11] ⭐ ไฟล์ subtitle ภาษาไทย
├── metadata.json                  # [12] SEO + YouTube metadata
├── thumbnail_concepts.json        # [13] ⭐ 3 design concepts สำหรับปก
├── format_specs.json              # [14] ⭐ คำแนะนำ export formats
├── multi_channel.json             # [15] ⭐ แผนเผยแพร่หลายช่องทาง
├── publish_receipt.json           # [16] ข้อมูลการเผยแพร่
├── publish_checklist.md           # [16] Checklist ก่อนเผยแพร่
├── backup_manifest.json           # [17] ⭐ รายการไฟล์สำรอง
├── README_ARCHIVE.md              # [17] ⭐ คู่มือ archive
└── pipeline_summary.json          # สรุปการรัน pipeline
```

**รวมทั้งหมด: 22 ไฟล์** 🎉

---

## 🤖 Agents ในระบบ

### 📊 Pipeline Comparison

| Pipeline | Agents | Time | Use Case |
|----------|--------|------|----------|
| `video.yaml` | 8 | ~1 วินาที | ทดสอบเร็ว, ดู workflow พื้นฐาน |
| `video_complete.yaml` | **17** ⭐ | ~1 วินาที | Production-ready, ครบทุกขั้นตอน |

---

### 🎯 Complete Pipeline (17 Agents)

#### **PHASE 1: DISCOVERY & RESEARCH** (4 agents)

### 1️⃣ **Trend Scout**
- **หน้าที่**: หาเทรนด์/หัวข้อที่กำลังมาในสายธรรมะ
- **Input**: `niches`, `horizon_days`
- **Output**: `trend_candidates.json` (5-10 หัวข้อ)
- **ข้อมูล**: Title, Why Now, Sources, Audience, Difficulty, Risk

### 2️⃣ **Topic Prioritizer**
- **หน้าที่**: จัดอันดับหัวข้อตาม Impact × Feasibility × Alignment
- **Input**: `trend_candidates.json`
- **Output**: `topics_ranked.json`
- **เกณฑ์คะแนน**:
  - Impact (40%): ผลกระทบต่อผู้ชม
  - Feasibility (30%): ความเป็นไปได้ในการผลิต
  - Alignment (30%): สอดคล้องกับพันธกิจช่องธรรมะ

### 3️⃣ **Research Retrieval**
- **หน้าที่**: รวบรวมอ้างอิงจากพระไตรปิฎก/อรรถกถา/แหล่งเชื่อถือ
- **Input**: `topics_ranked.json` (เลือก rank 1)
- **Output**: `research_bundle.json`
- **ประกอบด้วย**:
  - Claims: ข้อความหลัก
  - Citations: แหล่งอ้างอิง (canonical, commentary, secondary)
  - Keywords: คีย์เวิร์ดสำคัญ

### 4️⃣ **Data Enrichment** ⭐ NEW
- **หน้าที่**: เพิ่มข้อมูลเสริมจากแหล่งต่างๆ
- **Input**: `research_bundle.json`
- **Output**: `data_enrichment.json`
- **เพิ่ม**:
  - Historical background
  - Modern research findings
  - Common misconceptions
  - Practical tips
  - Cultural context

---

#### **PHASE 2: CONTENT CREATION** (4 agents)

### 5️⃣ **Script Outline**
- **หน้าที่**: สร้างโครงร่างสคริปต์
- **Input**: `data_enrichment.json`
- **Output**: `outline.md`
- **โครงสร้าง**:
  - Hook (0:00-0:30)
  - Introduction (0:30-1:30)
  - Main Points (1:30-7:00)
  - Practical Application (7:00-8:30)
  - Conclusion & CTA (8:30-10:00)

### 6️⃣ **Script Writer**
- **หน้าที่**: เขียนสคริปต์เต็มรูปแบบพร้อม timestamps
- **Input**: `outline.md`
- **Output**: `script.md`
- **รายละเอียด**:
  - บทพูดทุกคำ
  - จุด B-ROLL
  - PAUSE สำหรับจังหวะ
  - CITATION แสดงแหล่งอ้างอิง
  - Production notes

### 7️⃣ **Doctrine Validator**
- **หน้าที่**: ตรวจสอบความถูกต้องตามหลักธรรม ⚠️ **สำคัญ**
- **Input**: `script.md`
- **Output**: `script_validated.md`, `validation_report.json`
- **ตรวจสอบ**:
  - ความถูกต้องตามหลักพุทธศาสนา
  - การอ้างอิงที่แม่นยำ
  - ความเหมาะสมของการตีความ
  - ข้อความที่อาจเข้าใจผิด

### 8️⃣ **Legal/Compliance** ⭐ NEW
- **หน้าที่**: ตรวจสอบด้านกฎหมายและข้อบังคับ
- **Input**: `script_validated.md`
- **Output**: `compliance_report.json`
- **ตรวจสอบ**:
  - ลิขสิทธิ์ (copyright)
  - เนื้อหาศาสนา (appropriate)
  - Medical claims
  - YouTube policy compliance
  - Required disclaimers

---

#### **PHASE 3: PRODUCTION ASSETS** (3 agents)

### 9️⃣ **Visual Asset** ⭐ NEW
- **หน้าที่**: สร้างคำแนะนำสำหรับภาพและวิดีโอประกอบ
- **Input**: `script_validated.md`
- **Output**: `visual_guide.json`
- **รายละเอียด**:
  - 12 scenes พร้อม timestamps
  - B-roll list (6+ clips)
  - Color palette
  - Fonts recommendation
  - Stock footage sources

### 🔟 **Voiceover** ⭐ NEW
- **หน้าที่**: คำแนะนำสำหรับการพากย์เสียง
- **Input**: `script_validated.md`
- **Output**: `voiceover_guide.json`
- **รายละเอียด**:
  - Voice profile (tone, pace, pitch)
  - Section-by-section direction
  - Pauses and emphasis
  - Pronunciation guide
  - Background music suggestions
  - Recording settings

### 1️⃣1️⃣ **Localization & Subtitle** ⭐ NEW
- **หน้าที่**: สร้างคำบรรยายและแปลภาษา
- **Input**: `script_validated.md`
- **Output**: `localization.json`, `subtitles_th.srt`
- **รายละเอียด**:
  - Thai SRT file (120 lines)
  - English translation guide
  - Key terminology translation
  - Accessibility features
  - Quality checklist

---

#### **PHASE 4: PUBLISHING PREPARATION** (5 agents)

### 1️⃣2️⃣ **SEO & Metadata**
- **หน้าที่**: สร้าง metadata สำหรับ YouTube
- **Input**: `script_validated.md`
- **Output**: `metadata.json`
- **ประกอบด้วย**:
  - Title (≤70 ตัวอักษร)
  - Description พร้อม timestamps
  - Tags (15-20 tags)
  - Category, Language, Visibility
  - End screen, Cards

### 1️⃣3️⃣ **Thumbnail Generator** ⭐ NEW
- **หน้าที่**: สร้างคอนเซ็ปต์ภาพปก
- **Input**: `metadata.json`
- **Output**: `thumbnail_concepts.json`
- **รายละเอียด**:
  - 3 design concepts
  - Text overlay specifications
  - Visual elements
  - Color schemes
  - Design tools recommendations

### 1️⃣4️⃣ **Format Conversion** ⭐ NEW
- **หน้าที่**: แปลงไฟล์เป็นรูปแบบต่างๆ
- **Input**: `script_validated.md`
- **Output**: `format_specs.json`
- **รายละเอียด**:
  - Video formats (YouTube, Facebook, TikTok)
  - Audio format (Podcast)
  - Document formats (PDF, DOCX)
  - Export settings

### 1️⃣5️⃣ **Multi-Channel Publish** ⭐ NEW
- **หน้าที่**: เผยแพร่หลายแพลตฟอร์ม
- **Input**: `metadata.json`
- **Output**: `multi_channel.json`
- **รายละเอียด**:
  - YouTube (primary)
  - Facebook (page + groups)
  - LINE Broadcast
  - Website embed
  - Cross-promotion schedule

### 1️⃣6️⃣ **Scheduling & Publishing**
- **หน้าที่**: จัดการเผยแพร่และกำหนดเวลา
- **Input**: `multi_channel.json`
- **Output**: `publish_receipt.json`, `publish_checklist.md`
- **ฟีเจอร์**:
  - กำหนดเวลาเผยแพร่
  - Analytics tracking
  - Complete checklist

---

#### **PHASE 5: BACKUP & ARCHIVE** (1 agent)

### 1️⃣7️⃣ **Backup/Archive** ⭐ NEW
- **หน้าที่**: แพ็กและสำรองไฟล์ทั้งหมด
- **Output**: `backup_manifest.json`, `README_ARCHIVE.md`
- **รายละเอียด**:
  - รวบรวมไฟล์ทั้งหมด (19+ files)
  - จัดหมวดหมู่
  - Archive metadata
  - Restore instructions
  - Retention policy

---

## 📊 ตัวอย่างผลลัพธ์

### 1. Trend Candidates (trend_candidates.json)

```json
{
  "scouted_at": "2025-11-04T08:54:15",
  "niches": ["dhamma", "mindfulness", "Buddhism (TH)"],
  "horizon_days": 30,
  "total_candidates": 5,
  "candidates": [
    {
      "title": "เจริญสติในชีวิตประจำวัน 5 นาที",
      "why_now": "Short-form mindfulness กำลังเป็นเทรนด์",
      "sources": ["YouTube Trending", "Google Trends TH"],
      "audience": "คนทำงาน, ผู้เริ่มต้น",
      "difficulty": "ง่าย",
      "risk": "ต่ำ - เนื้อหาพื้นฐาน ไม่ขัดแย้ง"
    }
  ]
}
```

### 2. Topics Ranked (topics_ranked.json)

```json
{
  "prioritized_at": "2025-11-04T08:54:15",
  "total_evaluated": 5,
  "selected_top": 3,
  "ranked": [
    {
      "rank": 1,
      "title": "เจริญสติในชีวิตประจำวัน 5 นาที",
      "scores": {
        "impact": 8,
        "feasibility": 10,
        "alignment": 10,
        "total": 8.4
      },
      "reason": "Short-form mindfulness กำลังเป็นเทรนด์"
    }
  ]
}
```

### 3. Validation Report (validation_report.json)

```json
{
  "validated_at": "2025-11-04T08:54:15",
  "status": "approved",
  "issues": [],
  "approved_sections": [
    {
      "section": "00:00-02:30",
      "status": "approved",
      "note": "คำนิยามสติถูกต้อง"
    }
  ],
  "citations_verified": [
    {
      "citation": "อนาปานสติสูตร (มัชฌิมนิกาย)",
      "status": "verified"
    }
  ],
  "overall_feedback": "✅ สคริปต์ถูกต้องตามหลักธรรม"
}
```

### 4. Metadata (metadata.json)

```json
{
  "title": "เจริญสติในชีวิตประจำวัน 5 นาที | ฝึกอานาปานสติแบบง่ายๆ",
  "title_length": 68,
  "description": "🙏 เจริญสติง่ายๆ แค่ 5 นาที...",
  "tags": ["สติ", "อานาปานสติ", "ธรรมะ", "mindfulness"],
  "category": "Education",
  "visibility": "public"
}
```

---

## 🔧 การ Customize

### 1. เพิ่ม Agent ใหม่

แก้ไข `orchestrator.py`:

```python
def agent_my_custom_agent(step, run_dir: Path):
    """My Custom Agent - คำอธิบาย"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]
    
    # โค้ดของคุณ
    data = read_json(in_path)
    result = {"status": "success"}
    
    write_json(out, result)
    log(f"✓ My Custom Agent completed")
    return out

# เพิ่มใน AGENTS registry
AGENTS = {
    # ... existing agents ...
    "MyCustomAgent": agent_my_custom_agent,
}
```

### 2. สร้าง Pipeline ใหม่

สร้างไฟล์ `pipelines/custom.yaml`:

```yaml
pipeline: custom-workflow
version: 0.1
steps:
  - id: step1
    uses: MyCustomAgent
    input:
      param1: "value"
    output: result.json

  - id: step2
    uses: AnotherAgent
    needs: [step1]
    input_from: result.json
    output: final.json
```

รัน:

```powershell
python orchestrator.py --pipeline pipelines\custom.yaml --run-id test1
```

### 3. เชื่อมต่อ API จริง

แทนที่ข้อมูลจำลองด้วย API calls:

```python
def agent_trend_scout(step, run_dir: Path):
    import requests
    
    # เรียก YouTube Data API
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": "ธรรมะ mindfulness",
            "type": "video",
            "order": "viewCount",
            "key": os.getenv("YOUTUBE_API_KEY")
        }
    )
    
    data = response.json()
    # ประมวลผล...
```

---

## 📝 Best Practices

### 1. ตั้งชื่อ Run ID อย่างมีระเบียบ

```powershell
# แนะนำ: ใช้รูปแบบ topic_date
python orchestrator.py --pipeline pipelines\video.yaml --run-id "mindfulness_20251104"
python orchestrator.py --pipeline pipelines\video.yaml --run-id "noble_truths_20251105"
```

### 2. สำรอง Output ก่อนรันใหม่

```powershell
# Backup ก่อนรันใหม่
cp -r output\demo1 output\backups\demo1_20251104
```

### 3. ตรวจสอบ Validation Report เสมอ

```powershell
# อ่านรายงานการตรวจสอบ
cat output\demo1\validation_report.json
```

### 4. ใช้ Checklist ก่อนเผยแพร่

```powershell
# เปิด checklist
cat output\demo1\publish_checklist.md
```

---

## 🐛 Troubleshooting

### ปัญหา: ModuleNotFoundError: No module named 'yaml'

**แก้ไข**:
```powershell
.\venv\Scripts\Activate.ps1
pip install pyyaml
```

### ปัญหา: Pipeline file not found

**แก้ไข**: ตรวจสอบ path
```powershell
# ใช้ backslash ใน Windows
--pipeline pipelines\video.yaml

# หรือ forward slash
--pipeline pipelines/video.yaml
```

### ปัญหา: Agent not implemented

**แก้ไข**: ตรวจสอบว่า Agent ใน YAML ตรงกับ AGENTS registry ใน orchestrator.py

```yaml
# ใน video.yaml
uses: TrendScout  # ต้องตรงกับ key ใน AGENTS dict
```

```python
# ใน orchestrator.py
AGENTS = {
    "TrendScout": agent_trend_scout,  # ต้องมี
}
```

---

## 🎓 ตัวอย่างการใช้งานจริง

### Workflow 1: สร้างวิดีโอธรรมะรายสัปดาห์

```powershell
# วันจันทร์: หาเทรนด์
python orchestrator.py --pipeline pipelines\video.yaml --run-id "weekly_$(Get-Date -Format 'yyyyMMdd')"

# ตรวจสอบผลลัพธ์
cat output\weekly_20251104\topics_ranked.json

# อ่านสคริปต์
cat output\weekly_20251104\script_validated.md

# ใช้ metadata สร้างวิดีโอ
cat output\weekly_20251104\metadata.json

# เผยแพร่ตาม checklist
cat output\weekly_20251104\publish_checklist.md
```

### Workflow 2: ทดลองหลายหัวข้อ

```powershell
# รันหลายครั้งด้วย run-id ต่างกัน
python orchestrator.py --pipeline pipelines\video.yaml --run-id "test_mindfulness"
python orchestrator.py --pipeline pipelines\video.yaml --run-id "test_meditation"
python orchestrator.py --pipeline pipelines\video.yaml --run-id "test_precepts"

# เปรียบเทียบผลลัพธ์
cat output\test_mindfulness\topics_ranked.json
cat output\test_meditation\topics_ranked.json
cat output\test_precepts\topics_ranked.json
```

---

## 📚 ขั้นตอนต่อไป

1. **เพิ่ม Real Data**: เชื่อมต่อ YouTube API, Google Trends API จริง
2. **Visual Assets**: เพิ่ม agent สร้าง B-roll suggestions, thumbnail designs
3. **Voiceover**: เพิ่ม text-to-speech integration
4. **Subtitles**: สร้าง SRT file อัตโนมัติ
5. **Analytics**: ติดตามผลวิดีโอหลังเผยแพร่
6. **Feedback Loop**: ปรับปรุง pipeline จากข้อมูล analytics

---

## 🙏 สรุป

ระบบ **Dhamma Video Automation Pipeline** ช่วยให้คุณ:

✅ **ประหยัดเวลา** - จาก 2-3 วัน → 15 นาที  
✅ **คุณภาพสม่ำเสมอ** - ตรวจสอบหลักธรรมทุกครั้ง  
✅ **ง่ายต่อการขยาย** - เพิ่ม agent ใหม่ได้ตลอด  
✅ **Trackable** - ติดตามทุก step ได้ชัดเจน  

**เริ่มต้นได้เลยตอนนี้!** 🚀

```powershell
python orchestrator.py --pipeline pipelines\video.yaml --run-id demo1
```

---

**📧 ติดต่อ/สอบถาม**: สร้าง Issue ใน GitHub หรือดูเพิ่มเติมใน [README.md](README.md)
