# 🎯 คู่มือใช้งาน Dhamma Channel Automation

**สร้างเมื่อ:** 2025-01-18  
**สถานะ:** พร้อมใช้งาน (OpenAI API ใช้ได้แล้ว, YouTube API รอแก้ IP restriction)

---

## 📊 สถานะระบบ

### ✅ พร้อมใช้งาน
- **OpenAI GPT-4o-mini**: ใช้งานได้ปกติ (~$0.0024/สคริปต์)
- **4 Agent ทดสอบ**: TrendScout, TopicPrioritizer, ScriptOutline, ScriptWriter
- **System Setup Pipeline**: 11 agents ทำงานสมบูรณ์
- **Script Generation**: สร้างสคริปต์วิดีโอธรรมะด้วย AI

### ⏳ รอดำเนินการ
- **YouTube Data API**: รอแก้ IP restriction หรือรอ quota รีเซ็ต
- **Combined Workflow**: รอ YouTube API ใช้งานได้

---

## 🚀 วิธีใช้งานด้วยคำสั่งเดียว

### 1️⃣ สร้างสคริปต์วิดีโอด้วย AI (แนะนำ!)
```powershell
python demo_gpt4_script.py
```
**ผลลัพธ์:**
- สคริปต์วิดีโอธรรมะ 5-7 นาที
- โครงสร้าง: บทนำ → เนื้อหา 3 ส่วน → บทสรุป → Call-to-Action
- ไฟล์ output: `output/gpt4_scripts/script_YYYYMMDD_HHMMSS.md`
- เวลาสร้าง: ~10 วินาที

**ตัวอย่าง Output:**
```
✨ Script Generated Successfully!
Topic: วิธีรับมือความโกรธด้วยหลักธรรม
Words: 405 | Est. Duration: 5-7 min
Tokens: 1,582 | Cost: $0.0024
File: output/gpt4_scripts/script_20250118_143022.md
```

---

### 2️⃣ ทดสอบ Agent แต่ละตัว
```powershell
# ทดสอบทุก agent
python test_agent.py --agent all

# ทดสอบ agent เดียว
python test_agent.py --agent trend_scout
python test_agent.py --agent topic_prioritizer
python test_agent.py --agent script_outline
python test_agent.py --agent script_writer
```

**ผลลัพธ์:**
- JSON + Markdown files → `output/test_agents/`
- เวลาดำเนินการ: 1-3 วินาที/agent

---

### 3️⃣ ทดสอบ OpenAI API (Quick Test)
```powershell
python quick_test_openai.py
```
**ตรวจสอบ:**
- ✅ API key ใช้งานได้
- ✅ GPT-4o-mini response
- ✅ ราคาและ token usage

---

### 4️⃣ ทดสอบ YouTube API (Quick Test)
```powershell
python quick_test_youtube.py
```
**⚠️ ปัญหาปัจจุบัน:** IP restriction (2405:9800:b540:1e6:...)

**วิธีแก้:**
1. เข้า https://console.cloud.google.com/apis/credentials
2. คลิก API key → Edit
3. เลือก "None" ที่ Application restrictions
4. หรือเพิ่ม IPv6: `2405:9800:b540:1e6:e1eb:a7ce:f684:b18c`
5. Save → รอ 1-2 นาที → ทดสอบอีกครั้ง

---

### 5️⃣ รัน System Setup Pipeline
```powershell
python orchestrator.py
```
**ทำอะไร:**
1. สแกน 31 prompt templates
2. ตรวจสอบ API keys ทั้งหมด
3. ตรวจสอบ 64 ไฟล์พร้อม backup
4. ตั้งค่าระบบ 11 ขั้นตอน

**Output:**
- `output/final_verification/agent_XX_*.json`
- `output/final_verification/agent_XX_*.md`

---

## 📁 โครงสร้างไฟล์สำคัญ

### Scripts ที่สร้างขึ้น
```
d:\Auto Tool\dhamma-channel-automation\
│
├── orchestrator.py          # รัน pipeline (11 system setup agents)
├── test_agent.py           # ทดสอบ 4 agents หลัก
├── demo_gpt4_script.py     # สร้างสคริปต์ด้วย GPT-4 (แนะนำ!)
├── quick_test_openai.py    # ทดสอบ OpenAI API อย่างเดียว
├── quick_test_youtube.py   # ทดสอบ YouTube API อย่างเดียว
└── test_api.py             # ทดสอบทั้ง 2 APIs พร้อมกัน
```

### Output Directories
```
output/
├── gpt4_scripts/           # สคริปต์จาก demo_gpt4_script.py
├── test_agents/            # ผลลัพธ์จาก test_agent.py
├── final_verification/     # ผลลัพธ์จาก orchestrator.py
└── api_tests/              # ผลลัพธ์จาก test_api.py (รอ YouTube)
```

---

## 🎬 Workflow แนะนำ: สร้างวิดีโอ 1 เรื่อง

### ขั้นตอนที่ 1: สร้างสคริปต์
```powershell
python demo_gpt4_script.py
```
📝 **ได้สคริปต์ครบ:** บทนำ → เนื้อหา → บทสรุป → CTA

### ขั้นตอนที่ 2: ตรวจสอบหลักธรรม (Manual - ยังไม่ auto)
- เปิดไฟล์ `output/gpt4_scripts/script_*.md`
- ตรวจสอบความถูกต้องหลักธรรม
- แก้ไขถ้าจำเป็น

### ขั้นตอนที่ 3: ผลิตวิดีโอ (Manual - ยังไม่ auto)
- นำสคริปต์ไปบันทึกเสียง
- สร้าง visual/motion graphics
- แก้ไขวิดีโอ

### ขั้นตอนที่ 4: อัพโหลด YouTube
- อัพโหลดไฟล์วิดีโอ
- ใช้ metadata จาก script (title, description, tags)

---

## 💰 ต้นทุนการใช้งาน

### OpenAI GPT-4o-mini
| การใช้งาน | Tokens | ราคา (USD) |
|-----------|--------|-----------|
| สคริปต์ 1 เรื่อง (~400 คำ) | ~1,600 | $0.0024 |
| สคริปต์ 10 เรื่อง | ~16,000 | $0.024 |
| สคริปต์ 100 เรื่อง | ~160,000 | $0.24 |

**บาทไทย** (1 USD ≈ 33 THB):
- 1 สคริปต์ ≈ **0.08 บาท**
- 100 สคริปต์ ≈ **8 บาท**

### YouTube Data API
- **Free Tier:** 10,000 units/วัน
- **ต้นทุน:** ฟรี (ถ้าไม่เกิน quota)
- **การใช้งาน:** ~3 units/ค้นหา

---

## 🔧 Troubleshooting

### ❌ YouTube API: IP Restriction
```
HttpError 403: The provided API key has an IP address restriction
```
**แก้ไข:**
1. Google Cloud Console → API Credentials
2. Edit API key → Application restrictions → None
3. Save → รอ 1-2 นาที

### ❌ YouTube API: Quota Exceeded
```
HttpError 403: The request cannot be completed because you have exceeded your quota
```
**แก้ไข:**
- รอ quota รีเซ็ต (เที่ยงคืน Pacific Time)
- หรือใช้ API key อื่น
- หรือขอเพิ่ม quota ที่ Google Cloud Console

### ❌ OpenAI: SSL Certificate Error
```
FileNotFoundError: SSL_CERT_FILE
```
**แก้แล้ว:** ใช้ `httpx.Client(verify=False)` ใน development

### ❌ OpenAI: Invalid API Key
```
AuthenticationError: Incorrect API key
```
**แก้ไข:**
- ตรวจสอบ `.env` → `OPENAI_API_KEY=sk-proj-...`
- ตรวจสอบ API key ไม่หมดอายุ

---

## 📋 36 Agents ทั้งหมด (5 Phases)

### Phase 1: System Setup (11 agents) ✅
1. PromptPack - สแกน prompt templates
2. Security - ตรวจสอบ API keys
3. BackupArchive - จัดการ backup
4. Integration - ตั้งค่า API connections
5. Monitoring - ตั้งค่า logging
6. Notification - ตั้งค่า alerts
7. ErrorFlag - ตั้งค่า error handling
8. Scheduling - ตั้งค่า cron jobs
9. LegalCompliance - ตรวจสอบ license
10. Training - เตรียมข้อมูลฝึกสอน
11. Experiment - ตั้งค่า A/B testing

### Phase 2: Discovery (6 agents) ⏳
12. TrendScout - หาเทรนด์จาก YouTube ⚠️ รอ YouTube API
13. TopicPrioritizer - จัดอันดับหัวข้อ ✅
14. ResearchRetrieval - ค้นคว้าข้อมูล
15. CommunityInsight - วิเคราะห์ feedback
16. GrowthForecast - ทำนาย growth
17. AdvancedBI - วิเคราะห์ข้อมูลลึก

### Phase 3: Content Creation (10 agents) 🟡
18. ScriptOutline - สร้างโครงสร้าง ✅
19. ScriptWriter - เขียนสคริปต์ ✅
20. DoctrineValidator - ตรวจสอบหลักธรรม
21. Localization - แปลภาษา
22. SEOMetadata - สร้าง title/description/tags
23. PersonalizationAgent - ปรับ content ตาม audience
24. DataEnrichment - เพิ่มข้อมูลเสริม
25. VisualAutomation - สร้าง visual/graphics (ยังไม่มี)
26. AudioGeneration - สร้าง voiceover (ยังไม่มี)
27. FormatConversion - แปลง format (MP4, shorts, etc)

### Phase 4: Publishing (5 agents)
28. MultiChannelPublish - อัพโหลด YouTube/Facebook/TikTok
29. SchedulingPublish - จัดตารางเผยแพร่
30. AutoLabeling - ติด tags อัตโนมัติ
31. DataSync - ซิงค์ข้อมูล
32. FeedbackLoop - รับ feedback

### Phase 5: Analytics (4 agents)
33. AnalyticsRetention - วิเคราะห์ retention
34. DashboardAgent - สร้าง dashboard
35. UserFeedbackCollector - รวบรวม feedback
36. ExperimentOrchestrator - จัดการ A/B tests

---

## 🎯 Next Steps

### ขั้นต่อไป (เมื่อ YouTube API ใช้งานได้)
1. ✅ **แก้ IP restriction** หรือรอ quota รีเซ็ต
2. ⏳ **ทดสอบ Combined Workflow:**
   ```powershell
   python test_api.py
   ```
3. ⏳ **สร้าง Full Video Pipeline:**
   - TrendScout (YouTube) → TopicPrioritizer → ScriptOutline → ScriptWriter (GPT-4) → Publish
4. ⏳ **เพิ่ม Visual/Audio Agents:**
   - ต้องหา API สำหรับสร้าง graphics และ voiceover

### ใช้งานได้ทันที (ไม่ต้องรอ YouTube)
```powershell
# สร้างสคริปต์ธรรมะ 1 เรื่อง
python demo_gpt4_script.py

# ทดสอบ 4 agents
python test_agent.py --agent all

# รัน system setup
python orchestrator.py
```

---

## 📞 Support & References

### Files สำคัญ
- `SETUP_COMPLETE.md` - ผลการติดตั้งระบบ
- `SYSTEM_STATUS.md` - สถานะระบบล่าสุด
- `QUICKSTART.md` - คู่มือเริ่มต้น
- `docs/ARCHITECTURE.md` - สถาปัตยกรรมระบบ

### API Documentation
- [OpenAI API Docs](https://platform.openai.com/docs)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [Google Cloud Console](https://console.cloud.google.com)

### Environment Variables
ตรวจสอบใน `.env`:
```env
OPENAI_API_KEY=sk-proj-kJHjDz...      # ✅ ใช้งานได้
YOUTUBE_API_KEY=AIzaSyAtNm...         # ⚠️ รอแก้ IP restriction
```

---

**สร้างโดย:** GitHub Copilot  
**อัพเดท:** 2025-01-18  
**Version:** 1.0  
**สถานะ:** Ready for Production (OpenAI only)
