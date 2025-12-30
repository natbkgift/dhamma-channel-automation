# BLUEPRINT.md

**Single Source of Truth (แหล่งข้อมูลหลักเดียว)** สำหรับขอบเขตโครงการ กฎหลัก และเส้นทางพัฒนาของ Dhamma Channel Automation

---

## 1. วัตถุประสงค์ (Purpose)

- **ภารกิจ**: ระบบอัตโนมัติการผลิตคอนเทนต์ YouTube สำหรับช่อง "ธรรมะดีดี" โดยใช้ AI agents สร้างวิดีโอธรรมะ/สติปัญญาคุณภาพสูง 20-30 วิดีโอต่อเดือน
- **เป้าหมายรายได้**: 100,000 บาท/เดือน จาก YouTube AdSense
- **เป้าหมาย Automation**: ลดเวลาการผลิตแบบแมนนวล 70% โดยยังรักษาคุณภาพเนื้อหาและความเหมาะสมทางวัฒนธรรม
- **ความปลอดภัยเป็นอันดับแรก**: Pipeline ที่เชื่อถือได้ ตรวจสอบได้ มี human oversight gates; AI สร้าง มนุษย์ตัดสินใจ

## 2. ขอบเขต (Scope)

### Core Pipeline (แบบกำหนดไว้)
ขั้นตอนการทำงานที่ orchestrator รันตามลำดับ:
- **Discovery**: TrendScout, TopicPrioritizer, ResearchRetrieval
- **Content**: ScriptOutline, ScriptWriter, DoctrineValidator, LegalCompliance
- **Production**: VoiceoverAgent (TTS), VisualAsset, Localization/Subtitle
- **Publishing**: SEOMetadata, ThumbnailGenerator, SchedulingPublishing
- **Analytics**: KPI tracking, performance monitoring

### Extensions (Event-Driven, เสริมเพิ่มเติม)
n8n workflows สำหรับเสริมการทำงานของ orchestration:
- การแจ้งเตือน LINE หลังเผยแพร่วิดีโอ
- กำหนดเวลารัน pipeline อัตโนมัติ
- Retry logic สำหรับขั้นตอนที่ล้มเหลว
- Alert routing สำหรับการตรวจสอบโดยมนุษย์

## 3. สิ่งที่ไม่อยู่ในเป้าหมาย (Non-goals)

- **ไม่มีการเพิ่มประสิทธิภาพอัตโนมัติแบบวงปิด**: AI อ่าน KPIs แต่จะไม่เปลี่ยน prompts, agent parameters หรือกลยุทธ์เนื้อหาเอง; มนุษย์/กฎเท่านั้นที่ตัดสินใจเปลี่ยนแปลง
- **n8n ไม่จำเป็น**: Core pipeline ต้องทำงานได้เต็มที่โดยไม่ต้องมี n8n workflows; extensions เป็นสิ่งอำนวยความสะดวก ไม่ใช่ dependency
- **ไม่รองรับหลายช่อง (multi-tenant)**: ช่องเดียว ผู้ดูแลเดียว; การขยายไปยังช่องอื่นๆ เป็นงานในอนาคต (หลัง PR11)

## 4. กฎหลักที่ต้องไม่ละเมิด (Core Invariants - Must-Not-Break)

1. **Kill Switch Safety**: `PIPELINE_ENABLED=false` หยุดการทำงานของ pipeline อย่างสะอาด; orchestrator และ web runner บังคับใช้; exit code 0 (no-op, ไม่ใช่ error)
2. **Extensions ถอดออกได้**: การปิด/ลบ n8n, webhooks หรือระบบแจ้งเตือนต้องไม่ทำให้ core pipeline พัง
3. **Idempotent Upload**: YouTube publish agent ต้องตรวจจับวิดีโอที่มีอยู่แล้ว เพื่อป้องกันการอัพโหลดซ้ำ; รันซ้ำได้อย่างปลอดภัย
4. **Localhost-Only Ports**: บริการทั้งหมด bind ที่ `127.0.0.1:PORT` เท่านั้น; System Nginx เป็น reverse proxy หน้าบ้านเพียงตัวเดียว (FlowBiz pattern)
5. **Green Main Branch**: ทุก PR ต้องรักษา `main` branch ให้ deploy ได้; การเปลี่ยนแปลงน้อยที่สุด, tests ผ่านทั้งหมด, ไม่มี breaking changes
6. **Audit Trail**: ทุก pipeline run สร้าง output directories พร้อม timestamp, logs, artifacts และ metadata ครบถ้วน

## 5. รูปแบบระบบ (System Shape - Core vs Extensions)

```
┌─────────────────────────────────────────────────────┐
│             CORE (Deterministic Pipeline)           │
│  orchestrator.py ──▶ Agent1 ──▶ Agent2 ──▶ AgentN  │
│  - Sequential execution                             │
│  - Enforces PIPELINE_ENABLED kill switch            │
│  - Pure functions (agents read/write files only)    │
│  - Logged, reproducible, auditable                  │
└─────────────────────────────────────────────────────┘
           │ (optional webhook/event)
           ▼
┌─────────────────────────────────────────────────────┐
│        EXTENSIONS (Event-Driven, Optional)          │
│  n8n workflows:                                     │
│  - Schedule pipeline runs                           │
│  - Notify LINE on completion                        │
│  - Retry failed stages                              │
│  - Alert on errors                                  │
│  (Core works without these)                         │
└─────────────────────────────────────────────────────┘
```

**Port Configuration Pattern**: แหล่งข้อมูลเดียว (single source of truth) อยู่ใน `config/flowbiz_port.env` (`FLOWBIZ_ALLOCATED_PORT=3007`); บริการทั้งหมดอ้างอิงตัวแปรนี้; System Nginx proxy จาก public domain ไปยัง `127.0.0.1:3007`

## 6. Control Flow ระดับสูง (High Level)

```
┌─────────┐    ┌────────┐    ┌───────┐    ┌───────┐    ┌──────┐    ┌────────┐    ┌────────┐    ┌─────┐
│  Idea   │───▶│ Script │───▶│ Voice │───▶│ Video │───▶│  QA  │───▶│ Upload │───▶│ Notify │───▶│ KPI │
│ (Scout) │    │(Writer)│    │ (TTS) │    │(Render│    │(Valid│    │(YouTube│    │(LINE)  │    │Track│
└─────────┘    └────────┘    └───────┘    └───────┘    └──────┘    └────────┘    └────────┘    └─────┘
   CORE           CORE          CORE         CORE         CORE         CORE         EXTENSION     CORE

Legend:
  CORE = Required, deterministic, orchestrator-managed
  EXTENSION = Optional, event-driven, n8n-managed
```

ระยะของ Pipeline:
1. **Discovery** (CORE): วิเคราะห์เทรนด์ → เลือกหัวข้อ → รวบรวมข้อมูลวิจัย
2. **Content** (CORE): โครงเรื่อง → สคริปต์ → ตรวจสอบความถูกต้อง (หลักธรรม, กฎหมาย)
3. **Production** (CORE): สังเคราะห์เสียง → visual assets → คำบรรยาย
4. **Publishing** (CORE): SEO metadata → thumbnail → อัพโหลด YouTube
5. **Notification** (EXTENSION): แจ้งเตือน LINE, อัพเดตสถานะ
6. **Analytics** (CORE): เก็บ KPI, ติดตามประสิทธิภาพ

## 7. นโยบาย Extension (n8n เป็นตัวเลือก)

### การใช้งานที่อนุญาต (Event-Driven Orchestration)
- **การแจ้งเตือนหลังเผยแพร่**: ส่งข้อความ LINE เมื่อวิดีโอออนไลน์
- **การกำหนดเวลา**: เรียก pipeline runs ตามตารางเวลา cron
- **Retry logic**: รันขั้นตอนที่ล้มเหลวซ้ำด้วย exponential backoff
- **การแจ้งเตือน**: แจ้งมนุษย์เมื่อต้องการการตรวจสอบแบบแมนนวล (ธงหลักธรรม, ปัญหาการปฏิบัติตามกฎ)

### การใช้งานที่ห้าม (ต้องอยู่ใน Core)
- **การสร้าง artifact**: n8n ต้องไม่เรียก agents โดยตรงเพื่อสร้างสคริปต์, เสียง หรือวิดีโอ; orchestrator เป็นเจ้าของการทำงาน
- **การข้าม guardrail**: n8n ไม่สามารถ override `PIPELINE_ENABLED`, ข้ามขั้นตอนตรวจสอบ หรือแก้ไข agent behavior
- **การตัดสินใจหลัก**: n8n ไม่สามารถเปลี่ยนกลยุทธ์เนื้อหา, prompt templates หรือ agent parameters; มนุษย์ผ่าน code/config เท่านั้น

### มาตรฐานการทดสอบ
Pipeline ต้องผ่าน full end-to-end test โดย n8n ปิด/ลบออก:
```bash
# n8n down หรือไม่ได้ติดตั้ง
PIPELINE_ENABLED=true python orchestrator.py --pipeline pipeline.web.yml --run-id test_no_n8n
# คาดหวัง: Pipeline เสร็จสมบูรณ์, outputs อยู่ใน output/test_no_n8n/
```

## 8. โมเดลการส่งมอบ (Delivery Model - PR-by-PR)

### เสร็จสมบูรณ์แล้ว (PR1-PR2)
- **PR1**: Foundation (BaseAgent, TrendScout, CLI, tests, docs, CI/CD)
- **PR2**: FlowBiz Client Product adoption (contract endpoints, port binding, guardrails)

### Milestone ที่วางแผนไว้ (PR3-PR11)
- **PR3**: TopicPrioritizer + integration tests
- **PR4**: ScriptOutline + ScriptWriter agents
- **PR5**: DoctrineValidator + compliance checks
- **PR6**: VoiceoverAgent (Google TTS) + audio pipeline
- **PR7**: Localization/Subtitle agent + multi-language support
- **PR8**: SEOMetadata + ThumbnailGenerator
- **PR9**: SchedulingPublishing agent + YouTube API integration
- **PR10**: n8n workflows (optional notifications/scheduling)
- **PR11**: End-to-end integration + production readiness checklist

### Platform v2 (PR12+)
เมื่อมีข้อมูลการใช้งานจริงเพียงพอ (3+ เดือนของข้อมูล KPI, 60+ วิดีโอที่เผยแพร่):
- Dashboard สำหรับการตรวจสอบ/อนุมัติโดยมนุษย์
- การวิเคราะห์และข้อมูลเชิงลึกขั้นสูง
- A/B testing framework สำหรับ prompts/strategies
- การขยายหลายช่อง (ถ้าได้รับการยืนยันจากความสำเร็จของ PR11)

**ข้อจำกัด**: PR12+ ต้องการการยืนยันจากการใช้งานจริง; ห้ามสร้างฟีเจอร์ platform ก่อนเวลาโดยไม่มีความต้องการ/ข้อมูลที่พิสูจน์แล้ว

## 9. Observability & Safety (ขั้นต่ำ)

### Runtime Checks ที่จำเป็น
- **GET /healthz**: สถานะความพร้อมของบริการ; เร็ว (<50ms), ไม่ต้องเชื่อมต่อบริการภายนอก, ไม่ต้อง auth
- **GET /v1/meta**: Metadata ของบริการ (version, build SHA, environment); มีประโยชน์สำหรับการยืนยัน deployment

### เครื่องมือ Safety (อ้างอิงเท่านั้น)
- **scripts/guardrails.sh**: การตรวจสอบการปฏิบัติตามกฎก่อน deployment (port binding, env vars, documentation, security)
- **scripts/runtime_verify.sh**: Smoke tests หลัง deployment (endpoints, port binding, basic pipeline run)
- **PIPELINE_ENABLED kill switch**: หยุดฉุกเฉินสำหรับเหตุการณ์ในการใช้งานจริง (API outages, การเปลี่ยนแปลงนโยบายเนื้อหา)

**หมายเหตุ**: เครื่องมือเหล่านี้มีอยู่และต้องใช้งานได้; PRs ไม่ควรแก้ไขเว้นแต่แก้บัคหรือเพิ่มความปลอดภัย (ห้ามทำให้การตรวจสอบอ่อนแอลง)

### ความคาดหวังด้าน Monitoring
- ทุก pipeline run บันทึก logs ไปยัง `output/<run-id>/logs/`
- ติดตามความสำเร็จ/ล้มเหลวใน pipeline metadata JSON
- ผู้ดูแลมนุษย์ตรวจสอบผลลัพธ์ก่อนเผยแพร่ YouTube (manual gate ใน PR3-PR9; อาจทำอัตโนมัติใน PR12+ ถ้าพิสูจน์ความน่าเชื่อถือแล้ว)

## 10. เส้นทางการพัฒนา (Evolution Path)

### สถานะปัจจุบัน (PR2 เสร็จสมบูรณ์)
- **Manual + Semi-Automated**: วิเคราะห์เทรนด์อัตโนมัติ; การผลิตสคริปต์/วิดีโอกึ่งแมนนวล; การเผยแพร่ต้องมีการอนุมัติจากมนุษย์
- **สภาพแวดล้อม Local/Dev**: รันบนเครื่องนักพัฒนา; ยังไม่ได้ deploy ในการใช้งานจริง
- **ช่องเดียว**: "ธรรมะดีดี" เท่านั้น

### ระยะใกล้ (PR3-PR11, 3-6 เดือนถัดไป)
- **Production-Ready Pipeline**: ระบบอัตโนมัติเต็มรูปแบบ discovery→script→voice→video→upload พร้อม human review gates
- **การแจ้งเตือนที่เชื่อถือได้**: n8n workflows สำหรับ status alerts, scheduling
- **KPI Dashboard**: Web UI สำหรับดูการวิเคราะห์, อนุมัติเนื้อหา, ตรวจสอบค่าใช้จ่าย
- **FlowBiz Integration**: Deploy บน VPS, System Nginx proxying, healthz monitoring

### ระยะกลาง (PR12+, 6-12 เดือน, ขับเคลื่อนด้วยข้อมูล)
- **Automation ที่พิสูจน์แล้ว**: 60+ วิดีโอที่เผยแพร่, KPIs ยืนยันแล้ว (รายได้, engagement, คุณภาพ)
- **ลด Review Gates**: ทำการอนุมัติอัตโนมัติสำหรับเนื้อหาความเสี่ยงต่ำ (ผ่านการตรวจสอบหลักธรรม/กฎหมายอัตโนมัติ)
- **Performance Insights**: คำแนะนำจาก AI สำหรับการเลือกหัวข้อ, การเพิ่มประสิทธิภาพ SEO (มนุษย์ยังคงตัดสินใจ)

### ระยะยาว (อนาคต, ขึ้นอยู่กับความสำเร็จ)
- **Multi-Channel Scaling**: ขยายไปยังช่องธรรมะ/สติปัญญาอื่นๆ ถ้าโมเดลช่องเดียวมีกำไรและเชื่อถือได้
- **ฟีเจอร์ขั้นสูง**: การตรวจจับเทรนด์แบบ real-time, เนื้อหาหลายภาษา, ระบบตัดต่อวิดีโออัตโนมัติ
- **Platform Product**: โซลูชัน white-label สำหรับ content creators อื่นๆ (เป็นการคาดการณ์; ขึ้นอยู่กับการยืนยันจาก PR11)

---

**Blueprint Status**: v1.0 (2025-12-30)  
**Maintained By**: Repository maintainers  
**Update Policy**: ทบทวนรายไตรมาสหรือเมื่อมีการเปลี่ยนแปลงสถาปัตยกรรมหลัก; รักษาความกระชับ (อ่านได้ใน <5 นาที)
