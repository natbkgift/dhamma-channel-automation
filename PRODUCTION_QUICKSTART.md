# 🎬 Production Phase - Quick Start Guide

ระบบนี้ช่วยคุณแปลง **AI-generated content** เป็น **วิดีโอจริง** สำหรับอัปโหลด YouTube

---

## ✅ สิ่งที่คุณมีอยู่แล้ว

หลังจากรัน pipeline สำเร็จ คุณจะได้:

```
output/production_complete_001/
├── script_validated.md          ← สคริปต์สมบูรณ์ (ผ่าน doctrine validation)
├── voiceover_guide.json         ← คำแนะนำบันทึกเสียง
├── visual_guide.json            ← Storyboard พร้อม timestamps
├── thumbnail_concepts.json      ← 3 แนวคิด thumbnail
├── metadata.json                ← SEO title, description, tags
├── subtitles_th.srt             ← ซับไตเติ้ลภาษาไทย
└── ... (และอีก 16 ไฟล์)
```

---

## 🚀 Quick Start (1 คำสั่งเดียว)

```bash
python scripts/production_orchestrator.py --input-dir output/production_complete_001 --path A
```

**ผลลัพธ์:**
- ✅ สคริปต์สำหรับบันทึกเสียง → `audio/production_complete_001/`
- ✅ Template สำหรับ DaVinci Resolve → `templates/production_complete_001/`
- ✅ คู่มือสร้าง Thumbnail ใน Canva → `templates/canva/`

---

## 📋 3 เส้นทางให้เลือก

### 🅰️ Path A: **ฟรี 100%** (แนะนำสำหรับเริ่มต้น)

**ต้นทุน:** ฟรีทั้งหมด  
**เวลา:** 3-5 ชั่วโมง/วิดีโอ  
**เครื่องมือ:** Audacity + DaVinci Resolve + Canva (ฟรีทั้งหมด)

**ขั้นตอน:**
```bash
# 1. เตรียมสคริปต์และ templates
python scripts/production_orchestrator.py --input-dir output/production_complete_001 --path A

# 2. บันทึกเสียง (manual)
# → อ่าน audio/production_complete_001/recording_script_SIMPLE.txt
# → บันทึกด้วย Audacity
# → Save เป็น audio/voiceover.mp3

# 3. Edit วิดีโอ (manual)
# → เปิด DaVinci Resolve
# → ทำตาม templates/production_complete_001/EDITING_GUIDE.md
# → Export เป็น video/final.mp4

# 4. สร้าง Thumbnail (manual)
# → เปิด Canva.com
# → ทำตาม templates/canva/CANVA_GUIDE.md
# → Download เป็น thumbnails/thumbnail.jpg

# 5. Upload YouTube (manual)
# → ไป YouTube Studio
# → Upload video พร้อม thumbnail
# → Copy metadata จาก output/production_complete_001/metadata.json
```

---

### 🅱️ Path B: **Semi-Auto** (ประหยัดเวลา)

**ต้นทุน:** ~$1.50/วิดีโอ  
**เวลา:** 1-2 ชั่วโมง/วิดีโอ  
**ต้องการ:** OpenAI API key

**ขั้นตอน:**
```bash
# 1. ตั้งค่า API key
export OPENAI_API_KEY="sk-..."  # หรือเพิ่มใน production_config.json

# 2. รัน production (voiceover อัตโนมัติ)
python scripts/production_orchestrator.py --input-dir output/production_complete_001 --path B

# Voiceover จะถูกสร้างด้วย OpenAI TTS อัตโนมัติ
# → audio/production_complete_001/voiceover.mp3

# 3-5. Edit วิดีโอ, Thumbnail, Upload (manual เหมือน Path A)
```

**⚠️ Path B ยังไม่ implement เต็มรูปแบบ** - ตอนนี้จะทำงานเหมือน Path A

---

### 🅲️ Path C: **Full Auto** (สำหรับ Scale)

**ต้นทุน:** ~$5-10/วิดีโอ  
**เวลา:** 20-30 นาที/วิดีโอ  
**ต้องการ:** ElevenLabs + DALL-E + YouTube API

**ขั้นตอน:**
```bash
# 1. ตั้งค่า API keys ทั้งหมดใน production_config.json

# 2. รัน full automation
python scripts/production_orchestrator.py --input-dir output/production_complete_001 --path C

# ทุกอย่างอัตโนมัติ:
# → Voiceover (ElevenLabs)
# → Video editing (MoviePy/FFmpeg)
# → Thumbnail (DALL-E)
# → YouTube upload (YouTube API)
```

**⚠️ Path C ยังไม่ implement** - ต้อง setup APIs ทั้งหมดก่อน

---

## 📂 โครงสร้างไฟล์ที่สร้าง

หลังรัน production orchestrator:

```
dhamma-channel-automation/
├── audio/
│   └── production_complete_001/
│       ├── recording_script_SIMPLE.txt       ← อ่านและบันทึกเสียง
│       ├── recording_script_DETAILED.txt     ← พร้อม timing markers
│       ├── recording_metadata.json           ← Technical specs
│       └── sections/
│           ├── section_01_0000-0030.txt     ← แยกทีละส่วน (14 sections)
│           └── ...
│
├── templates/
│   ├── production_complete_001/
│   │   ├── EDITING_GUIDE.md                 ← คู่มือ DaVinci Resolve
│   │   ├── timeline.edl                     ← EDL file (import ได้)
│   │   ├── timeline.csv                     ← Timeline spreadsheet
│   │   └── text_overlays.json               ← รายการ text overlays
│   │
│   └── canva/
│       ├── CANVA_GUIDE.md                   ← คู่มือสร้าง thumbnail
│       ├── canva_concept_1.json             ← Concept 1: Peaceful
│       ├── canva_concept_2.json             ← Concept 2: Modern
│       ├── canva_concept_3.json             ← Concept 3: Emotional
│       └── canva_templates.md               ← Links to templates
│
├── broll/ (ถ้าใช้ Pexels API)
│   └── production_complete_001/
│       ├── broll_01_meditation.mp4
│       ├── broll_02_nature.mp4
│       └── broll_metadata.json
│
└── production_config.json                   ← การตั้งค่า
```

---

## 🛠️ Scripts ที่มีให้ใช้

### 1. **Production Orchestrator** (Main)
```bash
python scripts/production_orchestrator.py --input-dir OUTPUT_DIR --path [A|B|C]
```
รันทุกอย่างในคำสั่งเดียว

---

### 2. **Voiceover Preparation** (Individual)
```bash
python scripts/prepare_voiceover.py \
  --input-dir output/production_complete_001 \
  --output-dir audio/my_audio
```
สร้างสคริปต์สำหรับบันทึกเสียง

**Output:**
- `recording_script_SIMPLE.txt` - อ่านง่าย
- `recording_script_DETAILED.txt` - พร้อม pause markers
- `sections/` - แยกทีละ section

---

### 3. **DaVinci Resolve Templates** (Individual)
```bash
python scripts/generate_davinci_template.py \
  --input-dir output/production_complete_001 \
  --output-dir templates/my_templates \
  --fps 30
```
สร้าง timeline templates สำหรับ video editing

**Output:**
- `EDITING_GUIDE.md` - คู่มือ step-by-step
- `timeline.edl` - Import ใน DaVinci
- `timeline.csv` - View ใน Excel
- `text_overlays.json` - รายการ text overlays

---

### 4. **B-roll Downloader** (Individual)
```bash
python scripts/download_broll.py \
  --input-dir output/production_complete_001 \
  --output-dir broll/my_broll \
  --api-key YOUR_PEXELS_API_KEY \
  --max-videos 10
```
ดาวน์โหลด B-roll videos จาก Pexels (ฟรี)

**ต้องการ:** Pexels API key (ฟรีที่ https://www.pexels.com/api/)

**Output:**
- `broll_01_*.mp4` - วิดีโอ B-roll
- `broll_metadata.json` - ข้อมูล credits

---

### 5. **Canva Templates** (Individual)
```bash
python scripts/generate_canva_templates.py \
  --input-dir output/production_complete_001
```
สร้างคู่มือและ specs สำหรับ Canva

**Output:**
- `CANVA_GUIDE.md` - คู่มือสร้าง thumbnail
- `canva_concept_*.json` - Specs แต่ละ concept

---

## 📖 คู่มือแต่ละขั้นตอน

### 📄 1. บันทึกเสียง (Voiceover)

**เครื่องมือ:** Audacity (ฟรี) - https://www.audacityteam.org/

**ขั้นตอน:**
1. เปิด `audio/production_complete_001/recording_script_SIMPLE.txt`
2. อ่านผ่านครั้งหนึ่งเพื่อฝึก
3. เปิด Audacity → Record
4. อ่านตามสคริปต์ (ความเร็ว ~120 คำ/นาที)
5. Edit: Noise Reduction + Normalize to -3dB
6. Export: MP3 (192 kbps) หรือ WAV

**💡 Tips:**
- บันทึกในห้องเงียบ (ใช้ผ้าห่มลด echo)
- ดื่มน้ำก่อนบันทึก (หลีกเลี่ยงกาแฟ/นม)
- บันทึกทีละ section (`sections/` folder)
- เก็บ 2-3 takes แล้วเลือกที่ดีที่สุด

---

### 🎬 2. Edit วิดีโอ (DaVinci Resolve)

**เครื่องมือ:** DaVinci Resolve 19 (ฟรี) - https://www.blackmagicdesign.com/products/davinciresolve

**ขั้นตอน:**
1. เปิด `templates/production_complete_001/EDITING_GUIDE.md`
2. สร้าง project ใหม่: 1920x1080, 30fps
3. Import voiceover audio
4. Import B-roll videos (จาก Pexels/Pixabay)
5. ทำตาม scene-by-scene guide
6. เพิ่ม text overlays ตาม `text_overlays.json`
7. Export: MP4 (H.264, 10-15 Mbps)

**💡 B-roll ฟรี:**
- Pexels: https://www.pexels.com/
- Pixabay: https://pixabay.com/
- Mixkit: https://mixkit.co/

---

### 🎨 3. สร้าง Thumbnail (Canva)

**เครื่องมือ:** Canva (ฟรี) - https://www.canva.com/

**ขั้นตอน:**
1. เปิด `templates/canva/CANVA_GUIDE.md`
2. เลือก concept (1, 2, หรือ 3)
3. ไป Canva → Custom size: 1280x720
4. ทำตาม step-by-step guide
5. Download: JPG (<2MB)

**💡 A/B Testing:**
- สร้างทั้ง 3 concepts
- ทดสอบดูว่าอันไหนได้ CTR สูงกว่า

---

### 📺 4. Upload YouTube

**เครื่องมือ:** YouTube Studio - https://studio.youtube.com/

**ขั้นตอน:**
1. ไป YouTube Studio → Create → Upload videos
2. เลือกวิดีโอที่ export แล้ว
3. เปิด `output/production_complete_001/metadata.json`
4. Copy-paste:
   - Title (68 chars)
   - Description (เต็ม)
   - Tags (15 tags)
5. Upload thumbnail
6. Upload subtitle: `subtitles_th.srt`
7. ตั้งเวลาเผยแพร่: พรุ่งนี้ 10:00 (ตาม `publish_receipt.json`)

---

## ⚙️ Configuration

แก้ไข `production_config.json`:

```json
{
  "path": "A",                      // A, B, หรือ C
  "prepare_voiceover": true,        // สร้าง voiceover scripts
  "generate_davinci_templates": true,  // สร้าง DaVinci templates
  "download_broll": false,          // ดาวน์โหลด B-roll (ต้องมี API key)
  "generate_canva_templates": true, // สร้าง Canva guides
  
  "fps": 30,                        // Timeline framerate
  "max_broll_videos": 10,           // จำนวน B-roll สูงสุด
  
  "pexels_api_key": "",             // ใส่ถ้าต้องการดาวน์โหลด B-roll
  "openai_api_key": "",             // สำหรับ Path B (TTS)
  "elevenlabs_api_key": "",         // สำหรับ Path C
  "youtube_client_secret": ""       // สำหรับ auto upload
}
```

---

## 🔑 API Keys (สำหรับ Path B/C)

### Pexels API (ฟรี)
1. ไป https://www.pexels.com/api/
2. Sign up
3. Get API key
4. ใส่ใน `production_config.json`

### OpenAI API (Path B)
1. ไป https://platform.openai.com/
2. สร้าง API key
3. ต้นทุน: ~$0.015/นาที (TTS)

### ElevenLabs (Path C)
1. ไป https://elevenlabs.io/
2. Subscribe ($5-22/เดือน)
3. รองรับภาษาไทย

---

## 📊 เปรียบเทียบ Paths

| Feature | Path A (Free) | Path B (Semi) | Path C (Full) |
|---------|--------------|---------------|---------------|
| **ต้นทุน** | ฟรี | ~$1.50/วิดีโอ | ~$5-10/วิดีโอ |
| **เวลา** | 3-5 ชม. | 1-2 ชม. | 20-30 นาที |
| **Voiceover** | บันทึกเอง | OpenAI TTS | ElevenLabs |
| **Video Edit** | Manual | Manual | Auto (MoviePy) |
| **B-roll** | Manual download | Manual | Auto (Stock API) |
| **Thumbnail** | Canva manual | Canva manual | DALL-E auto |
| **Upload** | Manual | Manual | YouTube API |
| **คุณภาพ** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🚦 Workflow ทั้งหมด (End-to-End)

```bash
# 1. Content Creation (AI Agents) - DONE ✅
python orchestrator.py --pipeline pipelines/video_complete.yaml --run-id production_001

# 2. Production Phase (นี่!) - DOING 🔄
python scripts/production_orchestrator.py --input-dir output/production_001 --path A

# 3. Manual Tasks - TODO 📋
# → บันทึกเสียง (30-60 นาที)
# → Edit วิดีโอ (2-3 ชั่วโมง)
# → สร้าง thumbnail (15-30 นาที)
# → Upload YouTube (10 นาที)

# 4. Analytics & Optimization - FUTURE 📈
# → ดู YouTube Analytics
# → ปรับกลยุทธ์ตาม CTR/AVD
# → รันอีก production ด้วยหัวข้อใหม่
```

---

## 🎯 Next Steps

หลังจากรัน production orchestrator แล้ว:

1. **ทันที:** ลองอ่าน `audio/.../recording_script_SIMPLE.txt`
2. **วันนี้:** บันทึกเสียง section แรก (30 วินาที)
3. **สัปดาห์นี้:** Edit วิดีโอครบ
4. **สัปดาห์หน้า:** Upload YouTube!

---

## ❓ Troubleshooting

**Q: ไม่มี API keys จะทำอะไรได้บ้าง?**  
A: ใช้ Path A ได้เต็มรูปแบบ (ฟรี 100%)

**Q: B-roll หาจากไหน?**  
A: Pexels, Pixabay, Mixkit (ฟรีทั้งหมด)

**Q: DaVinci Resolve ยากไหม?**  
A: มี `EDITING_GUIDE.md` สอนทีละขั้นตอน

**Q: Canva ต้องเสียเงินไหม?**  
A: ไม่ - ใช้ free account ได้

**Q: Upload YouTube ต้องมี API ไหม?**  
A: ไม่ - Path A upload manual ใน YouTube Studio

---

## 📚 เอกสารเพิ่มเติม

- [PRODUCTION_WORKFLOW.md](PRODUCTION_WORKFLOW.md) - คู่มือเต็ม
- [AUTOMATED_WORKFLOW_GUIDE.md](AUTOMATED_WORKFLOW_GUIDE.md) - AI Agents
- [templates/canva/CANVA_GUIDE.md](templates/canva/CANVA_GUIDE.md) - Thumbnail
- [templates/.../EDITING_GUIDE.md](templates/production_complete_001/EDITING_GUIDE.md) - Video editing

---

**🎉 พร้อมผลิตวิดีโอแล้ว! ลองรันคำสั่งแรกเลย:**

```bash
python scripts/production_orchestrator.py --input-dir output/production_complete_001 --path A
```
