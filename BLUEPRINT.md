# BLUEPRINT.md

**Single Source of Truth** for Dhamma Channel Automation project boundaries, invariants, and evolution path.

---

## 1. Purpose

- **Mission**: Automate YouTube content production for "ธรรมะดีดี" (Dhamma Channel) using AI agents to generate 20-30 high-quality Buddhist/mindfulness videos per month
- **Revenue Target**: 100,000 THB/month from YouTube AdSense
- **Automation Goal**: Reduce manual production time by 70% while maintaining content quality and cultural appropriateness
- **Safety First**: Reliable, auditable pipeline with human oversight gates; AI generates, humans decide

## 2. Scope

### Core Pipeline (Deterministic)
Pipeline stages executed sequentially by orchestrator:
- **Discovery**: TrendScout, TopicPrioritizer, ResearchRetrieval
- **Content**: ScriptOutline, ScriptWriter, DoctrineValidator, LegalCompliance
- **Production**: VoiceoverAgent (TTS), VisualAsset, Localization/Subtitle
- **Publishing**: SEOMetadata, ThumbnailGenerator, SchedulingPublishing
- **Analytics**: KPI tracking, performance monitoring

### Extensions (Event-Driven, Optional)
n8n workflows for orchestration enhancements:
- Post-publish LINE notifications
- Scheduled pipeline triggers
- Retry logic for failed stages
- Alert routing for human review

## 3. Non-goals

- **No closed-loop auto-optimization**: AI reads KPIs but does NOT autonomously change prompts, agent parameters, or content strategy; humans/rules decide all changes
- **n8n not required**: Core pipeline must function fully without any n8n workflows; extensions are convenience, not dependency
- **No multi-tenant**: Single channel, single operator; scaling to other channels is future work (post-PR11)

## 4. Core Invariants (Must-Not-Break)

1. **Kill Switch Safety**: `PIPELINE_ENABLED=false` stops all pipeline execution cleanly; orchestrator and web runner enforce this; exit code 0 (no-op, not error)
2. **Removable Extensions**: Disabling/removing n8n, webhooks, or notification systems must NOT break core pipeline execution
3. **Idempotent Upload**: YouTube publish agent must detect existing videos to prevent duplicate uploads; safe to re-run
4. **Localhost-Only Ports**: All services bind to `127.0.0.1:PORT`; System Nginx is the sole public-facing reverse proxy (FlowBiz pattern)
5. **Green Main Branch**: Every PR keeps `main` branch deployable; minimal changes, full tests pass, no breaking changes
6. **Audit Trail**: All pipeline runs produce timestamped output directories with full logs, artifacts, and metadata

## 5. System Shape (Core vs Extensions)

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

**Port Configuration Pattern**: Single source of truth in `config/flowbiz_port.env` (`FLOWBIZ_ALLOCATED_PORT=3007`); all services reference this variable; System Nginx proxies from public domain to `127.0.0.1:3007`.

## 6. Control Flow (High Level)

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

Pipeline phases:
1. **Discovery** (CORE): Trend analysis → topic selection → research gathering
2. **Content** (CORE): Outline → script → validation (doctrine, legal)
3. **Production** (CORE): Voice synthesis → visual assets → subtitles
4. **Publishing** (CORE): SEO metadata → thumbnail → YouTube upload
5. **Notification** (EXTENSION): LINE alerts, status updates
6. **Analytics** (CORE): KPI collection, performance tracking

## 7. Extension Policy (n8n Optional)

### Allowed Uses (Event-Driven Orchestration)
- **After-publish notifications**: Send LINE message when video is live
- **Scheduling**: Trigger pipeline runs on cron schedule
- **Retry logic**: Re-run failed pipeline stages with exponential backoff
- **Alerting**: Notify humans when manual review required (doctrine flag, compliance issue)

### Prohibited Uses (Must Stay in Core)
- **Artifact generation**: n8n must NOT call agents directly to create scripts, audio, or video; orchestrator owns execution
- **Guardrail bypass**: n8n cannot override `PIPELINE_ENABLED`, skip validation stages, or modify agent behavior
- **Core decision-making**: n8n cannot change content strategy, prompt templates, or agent parameters; humans via code/config only

### Testing Standard
Pipeline must pass full end-to-end test with n8n disabled/removed:
```bash
# n8n down or not installed
PIPELINE_ENABLED=true python orchestrator.py --pipeline pipeline.web.yml --run-id test_no_n8n
# Expected: Pipeline completes successfully, outputs in output/test_no_n8n/
```

## 8. Delivery Model (PR-by-PR)

### Completed (PR1-PR2)
- **PR1**: Foundation (BaseAgent, TrendScout, CLI, tests, docs, CI/CD)
- **PR2**: FlowBiz Client Product adoption (contract endpoints, port binding, guardrails)

### Planned Milestones (PR3-PR11)
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
When sufficient production data exists (3+ months of KPI data, 60+ videos published):
- Dashboard for human review/approval gates
- Advanced analytics and insights
- A/B testing framework for prompts/strategies
- Multi-channel expansion (if validated by PR11 success)

**Constraint**: PR12+ requires production validation; do NOT prematurely build platform features without proven demand/data.

## 9. Observability & Safety (Minimum)

### Required Runtime Checks
- **GET /healthz**: Service health status; fast (<50ms), no external dependencies, no auth required
- **GET /v1/meta**: Service metadata (version, build SHA, environment); useful for deployment verification

### Safety Tools (Reference Only)
- **scripts/guardrails.sh**: Pre-deployment compliance checks (port binding, env vars, documentation, security)
- **scripts/runtime_verify.sh**: Post-deployment smoke tests (endpoints, port binding, basic pipeline run)
- **PIPELINE_ENABLED kill switch**: Emergency stop for production incidents (API outages, content policy changes)

**Note**: These tools exist and must remain functional; PRs should NOT modify them unless fixing bugs or extending safety (never weaken checks).

### Monitoring Expectations
- Every pipeline run logs to `output/<run-id>/logs/`
- Success/failure tracked in pipeline metadata JSON
- Human operators review outputs before YouTube publish (manual gate in PR3-PR9; may automate in PR12+ if proven reliable)

## 10. Evolution Path

### Current State (PR2 Complete)
- **Manual + Semi-Automated**: Trend analysis automated; script/video production semi-manual; publish requires human approval
- **Local/Dev Environment**: Runs on developer machine; not yet production-deployed
- **Single Channel**: "ธรรมะดีดี" only

### Near-Term (PR3-PR11, Next 3-6 Months)
- **Production-Ready Pipeline**: Fully automated discovery→script→voice→video→upload with human review gates
- **Reliable Notifications**: n8n workflows for status alerts, scheduling
- **KPI Dashboard**: Web UI for viewing analytics, approving content, monitoring costs
- **FlowBiz Integration**: Deployed on VPS, System Nginx proxying, healthz monitoring

### Mid-Term (PR12+, 6-12 Months, Data-Driven)
- **Proven Automation**: 60+ videos published, KPIs validated (revenue, engagement, quality)
- **Reduced Review Gates**: Automate approval for low-risk content (doctrine/legal checks pass automatically)
- **Performance Insights**: AI-powered suggestions for topic selection, SEO optimization (humans still decide)

### Long-Term (Future, Conditional on Success)
- **Multi-Channel Scaling**: Expand to other Buddhist/mindfulness channels if single-channel model proves profitable and reliable
- **Advanced Features**: Real-time trend detection, multi-language content, video editing automation
- **Platform Product**: White-label solution for other content creators (speculative; depends on PR11 validation)

---

**Blueprint Status**: v1.0 (2025-12-30)  
**Maintained By**: Repository maintainers  
**Update Policy**: Review quarterly or when major architectural changes planned; keep concise (<5 min read)
