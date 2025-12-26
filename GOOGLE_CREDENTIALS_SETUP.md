# 🔐 Google Cloud TTS Credentials Setup Guide

## ขั้นตอนการตั้งค่า Google Cloud Text-to-Speech API

### 1️⃣ สร้าง Google Cloud Project

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. คลิก **Select a project** → **NEW PROJECT**
3. ตั้งชื่อโปรเจกต์ เช่น `dhamma-tts-project`
4. คลิก **CREATE**

### 2️⃣ เปิดใช้งาน Text-to-Speech API

1. ที่ Console ค้นหา **Text-to-Speech API** ใน search bar
2. เลือก **Cloud Text-to-Speech API**
3. คลิก **ENABLE**
4. รอ 1-2 นาทีจนกว่า API จะเปิดใช้งาน

### 3️⃣ สร้าง Service Account

1. ไปที่ **IAM & Admin** → **Service Accounts**
2. คลิก **+ CREATE SERVICE ACCOUNT**
3. ตั้งค่าดังนี้:
   - **Service account name**: `dhamma-tts-service`
   - **Service account ID**: dhamma-tts-service (auto-generated)
   - **Description**: TTS for Dhamma Channel Automation
4. คลิก **CREATE AND CONTINUE**

### 4️⃣ ให้สิทธิ์ (Grant Permissions)

1. ที่หน้า **Grant this service account access to project**
2. เลือก Role: **Cloud Text-to-Speech User**
3. คลิก **CONTINUE**
4. คลิก **DONE**

### 5️⃣ สร้าง JSON Key

1. ที่หน้า Service Accounts หาตัว `dhamma-tts-service` ที่สร้างไว้
2. คลิก **⋮** (3 จุด) → **Manage keys**
3. คลิก **ADD KEY** → **Create new key**
4. เลือก **JSON** format
5. คลิก **CREATE**
6. ไฟล์ JSON จะดาวน์โหลดอัตโนมัติ (เก็บไว้ในที่ปลอดภัย!)

---

## วิธีใช้งาน Credentials

### 🅰️ วิธีที่ 1: ใช้ไฟล์ JSON โดยตรง (แนะนำ)

1. ย้ายไฟล์ JSON ที่ดาวน์โหลดมาไว้ในโฟลเดอร์โปรเจกต์
   ```
   D:\Auto Tool\dhamma-channel-automation\google-credentials.json
   ```

2. เพิ่มใน `.env`:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   ```

3. ทดสอบ:
   ```bash
   python scripts/tts_unified.py --provider google --list-voices
   ```

### 🅱️ วิธีที่ 2: ใส่ JSON Content ใน .env (สำหรับ Production)

1. เปิดไฟล์ JSON ที่ดาวน์โหลด คัดลอกเนื้อหาทั้งหมด

2. เพิ่มใน `.env` (วางทั้ง JSON object):
   ```env
   GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account","project_id":"dhamma-tts-project-123456",...}
   ```

3. ทดสอบ:
   ```bash
   python scripts/tts_unified.py --provider google --list-voices
   ```

### 🅲 วิธีที่ 3: ตั้งค่าใน production_config.json

1. เปิด `production_config.json`
2. เพิ่ม/แก้ไขฟิลด์:
   ```json
   {
     "tts_provider": "google",
     "tts_voice_google": "th-TH-Wavenet-B",
     "google_cloud_credentials_json": {"type":"service_account",...}
   }
   ```

---

## ทดสอบการทำงาน

### 1. ทดสอบแสดงรายการเสียงไทย

```bash
python scripts/tts_unified.py --provider google --list-voices
```

**ผลลัพธ์ที่ต้องการ:**
```
🎤 Available Google Cloud TTS Voices:

🇹🇭 Thai Voices:
┌────────────────────┬──────┬──────────────────────┬────────────────────┐
│ Voice Code         │ Type │ Gender               │ Price (/1M chars)  │
├────────────────────┼──────┼──────────────────────┼────────────────────┤
│ th-TH-Wavenet-B    │ WN   │ Male                 │ $16                │
│ th-TH-Wavenet-D    │ WN   │ Male                 │ $16                │
│ th-TH-Neural2-A    │ N2   │ Female               │ $16                │
│ th-TH-Neural2-C    │ N2   │ Female               │ $16                │
│ th-TH-Standard-A   │ STD  │ Female               │ $4                 │
└────────────────────┴──────┴──────────────────────┴────────────────────┘
```

### 2. ทดสอบสร้างเสียงจากสคริปต์จริง

```bash
python scripts/tts_unified.py ^
  --provider google ^
  --script "audio/production_complete_001/recording_script_SIMPLE.txt" ^
  --output "audio/test_google_wavenet_b.mp3" ^
  --voice th-TH-Wavenet-B ^
  --rate 1.0
```

**ผลลัพธ์ที่ต้องการ:**
```
📖 Loading script...
✅ Loaded 9,757 characters

🎙️ Generating TTS with Google Cloud...
   Provider: Google Cloud TTS
   Voice: th-TH-Wavenet-B (Male WaveNet)
   Rate: 1.0x

📊 Text length: 9,757 characters (>5000, will chunk)
   Chunk 1: 4,856 characters
   Chunk 2: 4,901 characters

⏳ Generating chunk 1/2...
✅ Chunk 1 saved: temp_chunk_001.mp3
⏳ Generating chunk 2/2...
✅ Chunk 2 saved: temp_chunk_002.mp3

🔗 Merging 2 chunks...
✅ Merged successfully

🧹 Cleaning up temporary files...

💰 Cost Estimate:
   Characters: 9,757
   Price: $16.00 / 1,000,000 chars (WaveNet)
   Total: $0.156 (~5.3 บาท)

✅ TTS Generated Successfully!
   📄 File: audio/test_google_wavenet_b.mp3
   📊 Size: 14.23 MB
   ⏱️ Duration: ~2:15 minutes
```

### 3. ทดสอบใน Production Guide HTML

1. เปิด `output/production_complete_001/PRODUCTION_GUIDE.html`
2. เลื่อนไปที่ **Step 1: Voiceover Recording**
3. ในส่วน **🤖 สร้างเสียงบรรยายด้วย AI**:
   - เลือก **Provider**: Google Cloud TTS
   - เลือก **Voice**: th-TH-Wavenet-B (Thai Male)
   - ปรับ **Speed**: 1.0x
4. คลิก **🎙️ สร้างเสียงด้วย AI**
5. คลิก **🚀 ดาวน์โหลด Batch File**
6. ดับเบิลคลิก `generate_tts.bat` ที่ดาวน์โหลด

---

## 🐛 Troubleshooting

### ❌ Error: "ไม่พบ Google Cloud credentials"

**แก้ไข:**
1. ตรวจสอบไฟล์ JSON อยู่ในโฟลเดอร์โปรเจกต์
2. ตรวจสอบ `.env` มี `GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json`
3. ตรวจสอบชื่อไฟล์ถูกต้อง (case-sensitive)

### ❌ Error: "permission_denied" หรือ "API has not been used"

**แก้ไข:**
1. ไปที่ Google Cloud Console
2. เปิดใช้ **Cloud Text-to-Speech API** (ตามขั้นตอนที่ 2)
3. รอ 1-2 นาที แล้วลองใหม่

### ❌ Error: "quota_exceeded"

**แก้ไข:**
1. ตรวจสอบ usage ที่ [Google Cloud Console - Quotas](https://console.cloud.google.com/iam-admin/quotas)
2. Free tier: 1,000,000 chars/month (~200 videos)
3. ถ้าเกิน quota ต้อง enable billing หรือรอถึงเดือนหน้า

### ❌ ไฟล์เสียงไม่มีเสียง หรือขาดๆ หายๆ

**แก้ไข:**
1. ตรวจสอบว่า chunking ทำงานถูกต้อง (ดูใน console log)
2. ลองลดขนาดสคริปต์ลง (<5000 chars) เพื่อทดสอบ
3. ตรวจสอบ internet connection (ต้องเสถียร)

---

## 💰 ค่าใช้จ่าย

### Free Tier (ฟรีทุกเดือน)
- **1,000,000 characters/month**
- สำหรับ video 9,757 chars = **102 videos/month ฟรี**
- รีเซ็ตทุก 1 เดือน

### Paid Pricing (เมื่อเกิน Free Tier)

| Voice Type    | Price/1M chars | ประมาณการต่อ video (10K chars) |
|---------------|----------------|--------------------------------|
| WaveNet       | $16.00         | ~$0.16 (~5.4 บาท)             |
| Neural2       | $16.00         | ~$0.16 (~5.4 บาท)             |
| Standard      | $4.00          | ~$0.04 (~1.4 บาท)             |

### คำแนะนำ:
- **Development**: ใช้ Free Tier (1M chars/month)
- **Production (>102 videos/month)**: 
  - Option A: Enable billing + ใช้ WaveNet/Neural2 (~5.4฿/video)
  - Option B: ใช้ Standard voice (~1.4฿/video)
  - Option C: ผสม OpenAI TTS สำหรับบางวิดีโอ

---

## 📚 เอกสารเพิ่มเติม

- [Google Cloud TTS Documentation](https://cloud.google.com/text-to-speech/docs)
- [Thai Voice Samples](https://cloud.google.com/text-to-speech/docs/voices)
- [Pricing Calculator](https://cloud.google.com/products/calculator)
- [Python Client Library](https://googleapis.dev/python/texttospeech/latest/)

---

## ✅ Checklist

- [ ] สร้าง Google Cloud Project
- [ ] Enable Text-to-Speech API
- [ ] สร้าง Service Account
- [ ] ดาวน์โหลด JSON Key
- [ ] เพิ่ม Credentials ใน `.env` หรือ `production_config.json`
- [ ] ทดสอบ `--list-voices` สำเร็จ
- [ ] ทดสอบสร้างเสียงจากสคริปต์จริงสำเร็จ
- [ ] ทดสอบใน Production Guide HTML สำเร็จ
- [ ] เปรียบเทียบคุณภาพ Google TTS vs OpenAI TTS

---

**🎉 เมื่อทำครบทุกขั้นตอน คุณพร้อมใช้งาน Google Cloud TTS สำหรับสร้างเสียงภาษาไทยคุณภาพสูงแล้ว!**
