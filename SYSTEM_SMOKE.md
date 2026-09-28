# DhammaLab SYSTEM-SMOKE v1

Nat อนุมัติร่างนี้เมื่อ 29 ก.ย. 2026 ใช้เป็นเงื่อนไขปิด secret migration ก่อน freeze Infrastructure v1.1 และก่อนตั้งตารางงานถาวร

## รันที่ไหน

- **Claude Code session** ที่ environment = **Default** และ repo = `natbkgift/dhammalab` เท่านั้น
- ห้ามรันใน Cowork: session Cowork ไม่ได้รับ API credential ของ environment จะได้ 403 "unregistered callers" (ทดสอบแล้ว 29 ก.ย. 2026)
- ห้ามใส่คีย์ header หรือ env var เอง proxy ของ environment เป็นคนใส่ `x-goog-api-key` ให้หลัง request ออกจาก VM

## เกณฑ์ผ่าน (ต้องผ่านครบทุกข้อ)

| # | เช็ก | ผ่านเมื่อ | วิธีตรวจ |
|---|---|---|---|
| S1 | แยกคีย์ | ไม่มี `DHAMMALAB_GEMINI_API_KEY` / `GEMINI_API_KEY` ใน env และไม่มี `~/.config/dhammalab/gemini.env` | `smoke/system_smoke.py` |
| S2 | ListModels | HTTP 200 | `smoke/system_smoke.py` |
| S3 | generateContent `gemini-3.8-flash` | HTTP 200 | `smoke/system_smoke.py` |
| S4 | TTS `gemini-3.8-flash-tts` เสียง Umbriel | HTTP 200, ไฟล์เสียงถูกต้อง ยาว 1.5–20 วินาที | `smoke/system_smoke.py` |
| S5 | Transcript QA ของเสียงจาก S4 | similarity ≥ 0.90 | `smoke/system_smoke.py` |
| S6 | Pipeline จริง 1 chunk | `pipeline/build_audio.py` สร้าง chunk แรกด้วย STYLE_CHANNEL + Umbriel ผ่าน engine `direct` สำเร็จ และ `key_source()` ขึ้นต้นด้วย `proxy` | คำสั่งด้านล่าง (ต้องมีโค้ดใน `pipeline/` แล้ว) |
| S7 | Cost ledger | call ของ S6 ถูกบันทึกพร้อม model และหมวด | `python3 pipeline/costs.py --exp SMOKE` |
| S8 | นับเข้าโปรเจกต์ถูก | request ขึ้นใน Google Cloud project **DhammaLab** (`gen-lang-client-0945598805`) ใต้คีย์ "DhammaLab TTS Production" | Console > APIs & Services > Gemini API > Metrics (Methods + Traffic by credential) |
| S9 | ความปลอดภัยและต้นทุน | ไม่มีค่าคีย์หรือ header ใน output/log, ต้นทุนรวม ≤ ~฿5 | อ่าน output + ledger |

## คำสั่ง

```bash
# S1–S5 (stdlib เท่านั้น ไม่ต้องติดตั้งอะไร)
python3 smoke/system_smoke.py

# S6–S7 (หลังโค้ด pipeline อยู่ใน repo แล้ว; ติดตั้ง dependency ตาม pipeline ก่อน)
python3 -c "import sys; sys.path.insert(0,'pipeline'); import gemini_tts; print(gemini_tts.key_source())"
DHAMMALAB_EXP=SMOKE DHAMMALAB_TTS_ENGINE=direct python3 pipeline/build_audio.py smoke/smoke_script.txt /tmp/smoke_out --limit 1
DHAMMALAB_EXP=SMOKE python3 pipeline/costs.py --exp SMOKE
```

## หลังผ่านครบ (Nat ตัดสินทีละข้อ)

1. บันทึกเวลา UTC และผลทุกข้อใน `dhammalab/secret_status.md` (project Thamma) — ไม่ใส่ค่าคีย์
2. `secret_check.py --migrate` ใน session ที่ยังมีไฟล์คีย์ชั่วคราว เพื่อลบไฟล์นั้น
3. เพิกถอนคีย์ชั่วคราวใน Google Cloud (มีคีย์ชื่อ "DhammaLab TTS Production" 2 อัน ต้องระบุก่อนว่าอันไหนคืออันใน Claude environment)
4. ตั้ง routine ของ Claude Code (environment Default) แทน scheduled task Cowork "DhammaLab: ตรวจ API credential ใน session ใหม่" แล้วค่อยหยุดอันเดิม
5. ประกาศ Infrastructure v1.1 freeze
