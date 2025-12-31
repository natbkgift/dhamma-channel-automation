# การเรนเดอร์วิดีโอจากเสียง (PR5)

เอกสารนี้อธิบายขั้นตอน `video.render` สำหรับเรนเดอร์ไฟล์ MP4 จากผลลัพธ์เสียงที่ได้จากขั้นตอน TTS แบบ deterministic โดยเน้นความปลอดภัยและการทำงานที่ตรวจสอบย้อนหลังได้ง่าย

## จุดประสงค์
- แปลง `voiceover_summary.json` เป็นวิดีโอ MP4 แบบ deterministic
- เก็บสรุปผลการเรนเดอร์ไว้ที่ `video_render_summary.json` (พาธแบบ relative เท่านั้น)
- รองรับ kill switch และ dry-run ตามมาตรฐาน pipeline

## ข้อกำหนดก่อนใช้งาน
- ติดตั้ง `ffmpeg` และต้องอยู่ใน PATH
- ใช้ pipeline ตัวอย่างจาก `pipelines/video_render.yaml`

## โครงสร้างพาธที่เกี่ยวข้อง (relative เท่านั้น)
- อินพุตสรุปเสียง: `output/<run_id>/artifacts/voiceover_summary.json`
- ไฟล์เสียง: `data/voiceovers/<run_id>/<slug>_<text_sha256_12>.wav`
- เอาต์พุตวิดีโอ: `output/<run_id>/artifacts/<slug>_<text_sha256_12>.mp4`
- สรุปผลเรนเดอร์: `output/<run_id>/artifacts/video_render_summary.json`

## วิธีรัน (ตัวอย่าง)
1) เตรียมสคริปต์เสียงไว้ที่ `scripts/voiceover_script.txt`
2) รันคำสั่งจากโฟลเดอร์โปรเจกต์:

```bash
python orchestrator.py --pipeline pipelines/video_render.yaml --run-id run_demo
```

## ข้อควรระวัง
- Kill switch: ตั้ง `PIPELINE_ENABLED=false` จะเป็น no-op และไม่สร้างไฟล์ใด ๆ
- Dry-run: ตั้ง `dry_run: true` ใน step จะไม่สร้างไฟล์และไม่เรียก `ffmpeg`
- พาธทั้งหมดใน JSON จะเป็น relative เท่านั้น (ไม่มี absolute paths)
- `voiceover_summary_path` และ `image_path` ถูกจำกัดให้ไม่สามารถ traversal ออกนอก repo ได้
