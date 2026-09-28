# dhammalab

Pipeline ของช่อง ธรรมะดีดี (DhammaLab) — เก็บเฉพาะโค้ด ไม่มีคีย์ ไม่มีไฟล์สื่อ

## Gemini key

- ทุก call ไป Gemini API เรียกตรงบน Google Cloud project **DhammaLab** (`gen-lang-client-0945598805`)
- คีย์อยู่ใน API credential "DhammaLab Gemini" ของ Claude cloud environment **Default** (host `generativelanguage.googleapis.com`) — proxy ใส่ `x-goog-api-key` ให้หลัง request ออกจาก VM
- โค้ดไม่ส่งคีย์เอง: `gemini_tts.key_source()` จะเป็น `proxy:...` เมื่อไม่มี env var และไม่มีไฟล์คีย์ชั่วคราว
- ห้ามใส่คีย์ใน repo, doc, log, Discord หรือ env var ของ environment

## รันที่ไหน

- งานที่เรียก Gemini (TTS, ถอดคำ/QA, ภาพ, motion, เพลง) → **Claude Code session, environment Default, repo นี้**
- งานเบราว์เซอร์ (YouTube Studio, Discord, เช็กผล EXP) → Cowork ตามเดิม
- Session Cowork ไม่ได้รับ credential นี้ (ได้ 403) จึงห้ามย้ายขั้น Gemini กลับไปรันใน Cowork

## ตรวจระบบ

ดู [SYSTEM_SMOKE.md](SYSTEM_SMOKE.md) — `python3 smoke/system_smoke.py`

## Make.com

Normal production = 0 Make operations สคริปต์ Make อยู่ใน `pipeline/legacy/` ใช้ได้เฉพาะ rollback (`DHAMMALAB_MAKE_ROLLBACK=1` + `make_guard`)
