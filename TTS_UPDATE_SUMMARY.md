# ✅ TTS System Update Complete

## 📋 สิ่งที่ทำเสร็จแล้ว

### 1. HTML UI Updates ✅
- **อัพเดท PRODUCTION_GUIDE.html** ให้รองรับ Multi-Provider TTS
- เพิ่ม **Provider Dropdown**: 
  - Google Cloud TTS (แนะนำสำหรับภาษาไทย) - ตั้งเป็น default
  - OpenAI TTS
- เพิ่ม **Voice Selection Dropdown**: 
  - อัพเดทอัตโนมัติตาม provider ที่เลือก
  - Google: 5 เสียงไทย (Wavenet B/D, Neural2 A/C, Standard A)
  - OpenAI: 6 เสียง (alloy, echo, fable, onyx, nova, shimmer)
- เพิ่ม **Speed Slider**: 0.5x - 2.0x พร้อมแสดงค่าแบบ real-time
- **JavaScript Functions**:
  - `voiceOptions{}`: object เก็บรายการเสียงทั้งหมด
  - `updateVoiceOptions()`: อัพเดท dropdown เมื่อเปลี่ยน provider
  - `generateTTS()`: สร้างคำสั่งตาม provider/voice/speed ที่เลือก
  - `copyCommand(cmd)`: คัดลอกคำสั่งที่สร้างขึ้น
  - `openBatchFile(batchContent)`: ดาวน์โหลด .bat file พร้อมคำสั่งที่ customize
  - Auto-initialize: `DOMContentLoaded` → `updateVoiceOptions()` (โหลด default voices)

### 2. TTS Scripts ✅
- **tts_generator.py** (OpenAI TTS):
  - รองรับ long text chunking (>4096 chars)
  - Binary concatenation สำหรับ merge chunks
  - ทดสอบแล้ว: 9,757 chars → 3 chunks → 13.59 MB, $0.146
  
- **tts_generator_google.py** (Google Cloud TTS):
  - รองรับ 5 Thai voices (WaveNet, Neural2, Standard)
  - Chunking >5000 chars
  - 3 วิธีโหลด credentials (path, JSON in .env, production_config.json)
  - Calculate cost (WaveNet/Neural2: $16/1M, Standard: $4/1M)
  - Made --script/--output optional for --list-voices
  
- **tts_unified.py** (Wrapper):
  - Single interface: `--provider google|openai`
  - Fixed import paths with `sys.path.insert(0)`
  - ทดสอบ --list-voices สำเร็จ (แสดง 5 เสียงไทย)

### 3. Configuration Files ✅
- **production_config.json**:
  ```json
  {
    "tts_provider": "google",
    "tts_voice_google": "th-TH-Wavenet-B",
    "tts_voice_openai": "alloy",
    "tts_speed": 1.0,
    "tts_pitch": 0,
    "google_cloud_credentials_json": "path/to/credentials.json หรือ JSON object"
  }
  ```
  
- **.env** (ต้องมี):
  ```env
  OPENAI_API_KEY=sk-...
  GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
  # หรือ
  GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account",...}
  ```

### 4. Documentation ✅
- **GOOGLE_TTS_SETUP.md**: คู่มือ setup Google Cloud TTS ครบถ้วน
- **GOOGLE_CREDENTIALS_SETUP.md**: คู่มือ setup credentials แบบละเอียด (เพิ่งสร้าง)
- ครอบคลุม:
  - ขั้นตอนสร้าง Google Cloud Project
  - Enable API
  - สร้าง Service Account + JSON Key
  - 3 วิธีใช้ credentials
  - Troubleshooting
  - Pricing calculator
  - Test commands

### 5. Libraries Installed ✅
```
openai==2.7.1
google-cloud-texttospeech==2.33.0
python-dotenv
httpx
google-api-core
google-auth
grpcio
protobuf
```

---

## 🔜 สิ่งที่ต้องทำต่อ (รออยู่ที่ User)

### 1. Setup Google Cloud Credentials
**User ต้องทำเอง** (ต้องเข้า Google Cloud Console):
1. สร้าง Google Cloud Project
2. Enable Text-to-Speech API
3. สร้าง Service Account
4. ดาวน์โหลด JSON Key
5. เพิ่มใน `.env`:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   ```

**คู่มือ**: อ่าน `GOOGLE_CREDENTIALS_SETUP.md`

### 2. ทดสอบ Google TTS กับสคริปต์จริง

**หลังจาก setup credentials แล้ว:**

```bash
# 1. ทดสอบ list voices
python scripts/tts_unified.py --provider google --list-voices

# 2. ทดสอบสร้างเสียง (เสียงชาย WaveNet B)
python scripts/tts_unified.py ^
  --provider google ^
  --script "audio/production_complete_001/recording_script_SIMPLE.txt" ^
  --output "audio/test_google_wavenet_b.mp3" ^
  --voice th-TH-Wavenet-B ^
  --rate 1.0

# 3. ทดสอบสร้างเสียง (เสียงหญิง Neural2 A)
python scripts/tts_unified.py ^
  --provider google ^
  --script "audio/production_complete_001/recording_script_SIMPLE.txt" ^
  --output "audio/test_google_neural2_a.mp3" ^
  --voice th-TH-Neural2-A ^
  --rate 1.0
```

**Expected Output:**
- ไฟล์ MP3 ขนาดประมาณ 14-15 MB
- ระยะเวลา ~2:15 นาที
- ค่าใช้จ่าย ~$0.16 (~5.4฿)

### 3. ทดสอบผ่าน HTML UI

1. เปิด `output/production_complete_001/PRODUCTION_GUIDE.html`
2. เลื่อนไปที่ **Step 1: Voiceover Recording**
3. ในส่วน **🤖 สร้างเสียงบรรยายด้วย AI**:
   - Provider: Google Cloud TTS ✅ (default)
   - Voice: th-TH-Wavenet-B ✅
   - Speed: 1.0x ✅
4. คลิก **สร้างเสียงด้วย AI**
5. คลิก **ดาวน์โหลด Batch File**
6. ดับเบิลคลิก `generate_tts.bat`
7. ตรวจสอบไฟล์ `audio/production_complete_001/voiceover_ai.mp3`

### 4. เปรียบเทียบคุณภาพ

**A/B Testing**:
1. สร้างเสียงด้วย Google TTS (th-TH-Wavenet-B)
2. สร้างเสียงด้วย OpenAI TTS (alloy)
3. เปรียบเทียบ:
   - การออกเสียงภาษาไทย (ชัดเจน, tone ถูกต้อง)
   - ความเป็นธรรมชาติ
   - ความเหมาะสมกับเนื้อหาธรรมะ

**สมมติฐาน**: 
- Google TTS จะออกเสียงไทยชัดเจนกว่า
- OpenAI TTS เสียงเหมือนคนต่างชาติพูดไทย

---

## 📊 สรุปความสามารถของระบบ

### TTS Providers
| Provider | Voices | Thai Quality | Price/1M | Chunking | Status |
|----------|--------|--------------|----------|----------|--------|
| Google Cloud | 5 Thai | ⭐⭐⭐⭐⭐ Native | $16 (WN/N2), $4 (STD) | 5000 chars | ✅ Ready (needs credentials) |
| OpenAI | 6 English | ⭐⭐ Poor Thai | $15 | 4096 chars | ✅ Tested & Working |

### Thai Voices (Google)
| Voice | Type | Gender | Recommended For |
|-------|------|--------|-----------------|
| th-TH-Wavenet-B | WaveNet | Male | 🎯 **ธรรมะ (เสียงครู/พระ)** |
| th-TH-Wavenet-D | WaveNet | Male (ต่ำ) | เนื้อหาจริงจัง |
| th-TH-Neural2-A | Neural2 | Female | บรรยายเบา/สดใส |
| th-TH-Neural2-C | Neural2 | Female (สูง) | เนื้อหาเยาวชน |
| th-TH-Standard-A | Standard | Female | ทดสอบ/ประหยัดต้นทุน |

### Features
- ✅ Multi-provider support (Google + OpenAI)
- ✅ Dynamic voice selection UI
- ✅ Long text chunking (อ่าน >10,000 chars ได้)
- ✅ Binary MP3 merging (ไร้รอยต่อ)
- ✅ Batch file generation (double-click to run)
- ✅ Cost calculation
- ✅ Free tier support (1M chars/month = 102 videos)

---

## 🎯 Next Steps

### Immediate (รอ User)
1. **Setup Google Cloud Credentials** (ตาม `GOOGLE_CREDENTIALS_SETUP.md`)
2. **ทดสอบสร้างเสียงจริง** (3 voices: Wavenet-B, Neural2-A, OpenAI alloy)
3. **เปรียบเทียบคุณภาพ** และเลือก default voice

### Future Enhancements (Optional)
1. **Create TTS Agent** (ใน `app/core/agents/`) - สำหรับ automation pipeline
2. **Add SSML Support** - ปรับ pitch, speed per section
3. **Background Music Mixing** - ใส่เพลงพื้นหลังอัตโนมัติ
4. **Batch Processing** - สร้างหลาย videos พร้อมกัน
5. **Voice Preview** - ฟังตัวอย่างก่อนสร้างจริง

---

## 📁 Files Modified/Created

### Modified
- ✅ `scripts/generate_production_report.py` - เพิ่ม provider/voice selection UI
- ✅ `scripts/tts_generator.py` - OpenAI TTS with chunking
- ✅ `scripts/tts_generator_google.py` - Google TTS with Thai voices
- ✅ `scripts/tts_unified.py` - Unified wrapper
- ✅ `production_config.json` - TTS configuration fields

### Created
- ✅ `GOOGLE_TTS_SETUP.md` - Setup guide overview
- ✅ `GOOGLE_CREDENTIALS_SETUP.md` - **Detailed credentials setup** (NEW)
- ✅ `templates/tts_ai_section.html` - Standalone UI template (reference)
- ✅ `audio/test_google_tts.txt` - Test script

### Generated
- ✅ `output/production_complete_001/PRODUCTION_GUIDE.html` - Updated with new UI

---

**🎉 ระบบพร้อมใช้งาน! ขั้นตอนถัดไป: User ต้อง setup Google Cloud Credentials แล้วทดสอบสร้างเสียง**
