# Scheduler/Queue v1 (Cron-friendly)

เอกสารนี้อธิบายการทำงานของ **scheduler/queue/worker** แบบไฟล์สำหรับรันผ่าน cron/Task Scheduler  
โหมดนี้ถูกออกแบบให้ **ปลอดภัยต่อการปฏิบัติการ** (disabled-by-default) และ **deterministic**

## ภาพรวม

- **Queue**: เก็บงานเป็นไฟล์ JSON ใน `data/queue/` แยกสถานะ pending/running/done/failed
- **Scheduler**: อ่านแผนเวลา แล้ว enqueue งานที่ถึงกำหนดในช่วงเวลา (window)
- **Worker**: ดึงงานถัดไปทีละงาน แล้วเรียก `orchestrator.run_pipeline(...)` หนึ่งครั้ง
- **Kill switch**: ถ้า `PIPELINE_ENABLED=false` จะไม่ทำอะไรเลย (no-op) และไม่เขียนไฟล์ใดๆ

## การรันพร้อมกัน (Concurrency)

### Scheduler
- **ปลอดภัย**: สามารถรัน scheduler หลาย instance พร้อมกัน (ไม่แนะนำ)
- การ enqueue ใช้ `os.O_CREAT | os.O_EXCL` เพื่อป้องกัน race condition
- Job ID เป็น deterministic ทำให้ไม่มีการ enqueue ซ้ำ

### Worker
- **ไม่แนะนำให้รันพร้อมกัน**: Worker ใช้ `os.replace()` ซึ่งอาจมี race condition เล็กน้อย
- ถ้างานถูก dequeue โดย worker อื่นแล้ว จะ return None และไม่ทำงาน
- **แนะนำ**: รัน worker ทีละตัว หรือใช้ระบบ lock ภายนอก (เช่น `flock`)

### ข้อจำกัด
- ไม่มี built-in locking mechanism ระหว่าง process
- การรัน worker หลายตัวพร้อมกันอาจเกิด race condition ได้ (แม้จะมีการจัดการแล้วก็ตาม)
- ออกแบบสำหรับ single-worker execution ผ่าน cron/Task Scheduler

## โครงสร้างคิว

```
data/queue/
  pending/
  running/
  done/
  failed/
```

ชื่อไฟล์ใน pending:

```
<YYYYMMDDTHHMMSSZ>_<job_id>.json
```

## รูปแบบแผนเวลา (Schedule Plan)

ไฟล์ตัวอย่าง: `scripts/schedule_plan.yaml`

```yaml
schema_version: "v1"
timezone: "Asia/Bangkok"
entries:
  - publish_at: "2026-01-05T09:00"
    pipeline_path: "pipeline.web.yml"
    run_id_prefix: "morning"
    params:
      topic_seed: "mindfulness"
```

### กติกาเวลา

- ถ้า `publish_at` มี timezone offset อยู่แล้ว ให้ใช้ตามนั้น
- ถ้าไม่มี offset ให้ตีความด้วย `timezone` ของแผน (ค่าเริ่มต้น `Asia/Bangkok`)
- เปรียบเทียบด้วยเวลา UTC เสมอ (`now <= scheduled_for <= now + window`)

## กติกา Deterministic ID

เพื่อหลีกเลี่ยงการวนซ้ำระหว่าง `job_id` และ `run_id`:

- `run_id_base` = `<YYYYMMDD_HHMM>` หรือ `<run_id_prefix>_<YYYYMMDD_HHMM>`
- `job_id` = `sha256(scheduled_for_utc + "|" + pipeline_path + "|" + run_id_base)[:12]`
- `run_id` = `<run_id_base>_<job_id>`

> หมายเหตุ: `scheduled_for_utc` ใช้รูปแบบ ISO8601 พร้อม `Z`

## ตัวแปรแวดล้อม (Kill Switch)

- `PIPELINE_ENABLED` (ค่าเริ่มต้น `true`)
- `SCHEDULER_ENABLED` (ค่าเริ่มต้น `false`)
- `WORKER_ENABLED` (ค่าเริ่มต้น `false`)

**เมื่อ `PIPELINE_ENABLED=false` จะไม่ทำอะไรเลย**
- ไม่ enqueue/dequeue
- ไม่เขียนไฟล์ summary
- ไม่เรียก orchestrator

## Dry Run

- `schedule --dry-run`: คำนวณงานที่ถึงกำหนดและเขียน summary แต่ไม่ enqueue
- `work --dry-run`: ตรวจงานถัดไปและเขียน summary โดยไม่รัน orchestrator และไม่เปลี่ยนสถานะคิว

## คำสั่งใช้งาน

### Schedule (enqueue)

```bash
python scripts/scheduler_runner.py schedule \
  --plan scripts/schedule_plan.yaml \
  --window-minutes 10 \
  --queue-dir data/queue
```

### Worker (ทำงาน 1 งาน)

```bash
python scripts/scheduler_runner.py work --queue-dir data/queue
```

### Queue list

```bash
python scripts/scheduler_runner.py queue list --queue-dir data/queue
```

## ตัวอย่าง Cron / Task Scheduler

**cron (Linux/macOS):**

```
*/10 * * * * cd /path/to/repo && python scripts/scheduler_runner.py schedule --plan scripts/schedule_plan.yaml --window-minutes 10
*/10 * * * * cd /path/to/repo && python scripts/scheduler_runner.py work --queue-dir data/queue
```

**Task Scheduler (Windows):**

- Trigger: Every 10 minutes
- Action: `python scripts\scheduler_runner.py schedule --plan scripts\schedule_plan.yaml --window-minutes 10`
- Action: `python scripts\scheduler_runner.py work --queue-dir data\queue`

## Artifacts (Summary)

### schedule_summary.json (v1)
- พาธ: `output/scheduler/artifacts/schedule_summary_<YYYYMMDD>.json`

### worker_summary.json (v1)
- พาธ: `output/worker/artifacts/worker_summary_<job_id>.json`
  - หากไม่มีงานในคิวจะใช้ `worker_summary_none.json`

ไฟล์ทั้งสองใช้เพื่อการตรวจสอบย้อนหลัง (ops audit) และไม่กระทบ pipeline เดิม
