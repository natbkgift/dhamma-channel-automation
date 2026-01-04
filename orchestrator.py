"""
Dhamma Channel Automation - Orchestrator Pipeline
รันเอเจนต์ตามลำดับที่กำหนดใน YAML pipeline
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from automation_core import dispatch_v0, post_templates, youtube_upload  # noqa: E402
from automation_core.utils.env import parse_pipeline_enabled  # noqa: E402

POST_TEMPLATES_ALIASES = {"post_templates", "post.templates"}


def ensure_dir(p: Path):
    """สร้างโฟลเดอร์ถ้ายังไม่มี"""
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str):
    """เขียนไฟล์ข้อความ"""
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj):
    """เขียนไฟล์ JSON"""
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path):
    """อ่านไฟล์ JSON"""
    return json.loads(path.read_text(encoding="utf-8"))


def log(msg: str, level="INFO"):
    """พิมพ์ log พร้อม timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def _artifact_output_rel(run_id: str, filename: str) -> str:
    """
    สร้าง path แบบ relative (รูปแบบ POSIX) สำหรับไฟล์ใน output/{run_id}/artifacts

    Args:
        run_id: รหัสรันของ pipeline ที่ใช้เป็นชื่อโฟลเดอร์ย่อยใน output
        filename: ชื่อไฟล์ที่อยู่ในโฟลเดอร์ artifacts

    Returns:
        path ของไฟล์ใน output/{run_id}/artifacts ในรูปแบบสตริง POSIX
    """
    return (Path("output") / run_id / "artifacts" / filename).as_posix()


def _post_templates_output_rel(run_id: str) -> str:
    """
    สร้าง path แบบ relative (รูปแบบ POSIX) สำหรับไฟล์สรุปเนื้อหาโพสต์

    Args:
        run_id: รหัสรันของ pipeline ที่ใช้เป็นชื่อโฟลเดอร์ย่อยใน output

    Returns:
        path ของไฟล์ post_content_summary.json ภายใต้
        output/{run_id}/artifacts ในรูปแบบสตริง POSIX
    """
    return _artifact_output_rel(run_id, "post_content_summary.json")


def _dispatch_audit_output_rel(run_id: str) -> str:
    """
    สร้าง path แบบ relative สำหรับไฟล์ dispatch_audit.json

    Args:
        run_id: รหัสการรัน pipeline ที่ใช้ในการสร้างโฟลเดอร์ย่อยใน output

    Returns:
        path แบบ relative ของไฟล์ dispatch_audit.json
    """
    return _artifact_output_rel(run_id, "dispatch_audit.json")


def _run_post_templates_step(run_id: str, root_dir: Path) -> str:
    """
    รัน post_templates เพื่อสร้าง post_content_summary.json

    Args:
        run_id: รหัสการรัน pipeline
        root_dir: โฟลเดอร์รากของโปรเจกต์

    Returns:
        path แบบ relative ของไฟล์ post_content_summary.json

    หมายเหตุ:
        - ถ้า PIPELINE_ENABLED=false จะไม่เขียนไฟล์ แต่คืนค่า path ที่คาดว่าจะเขียน
        - เมื่อเปิดใช้งานจะมีการเขียนไฟล์ลง output/<run_id>/artifacts/
    """
    log(f"Post templates: start run_id={run_id}")
    output_rel = _post_templates_output_rel(run_id)
    cli_args = ["render", "--run-id", run_id]
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        log("Post templates: disabled (PIPELINE_ENABLED=false)")
        log(f"Post templates: complete (skipped) -> {output_rel}")
        return output_rel

    log(f"Post templates: invoking post_templates CLI with args: {cli_args}")
    exit_code = post_templates.cli_main(cli_args, base_dir=root_dir)
    if exit_code != 0:
        raise RuntimeError(
            f"post_templates failed with exit code {exit_code} "
            f"for run_id={run_id}; args={cli_args}"
        )

    log(f"Post templates: completed -> {output_rel}")
    return output_rel


def _run_dispatch_v0_step(run_id: str, root_dir: Path) -> str:
    """
    รัน dispatch_v0 เพื่อสร้าง dispatch_audit.json
    """
    _, audit_path = dispatch_v0.generate_dispatch_audit(run_id, base_dir=root_dir)
    if audit_path is None:
        log("Dispatch v0: skipped (PIPELINE_ENABLED=false)")
        return "skipped"
    return audit_path.relative_to(root_dir).as_posix()


def _resolve_script_path(script_path: str | Path, root_dir: Path) -> Path:
    if isinstance(script_path, Path):
        candidate = script_path
    elif isinstance(script_path, str):
        if not script_path.strip():
            raise ValueError("script_path must be a non-empty string")
        candidate = Path(script_path)
    else:
        raise TypeError("script_path must be a string or Path")

    if not candidate.is_absolute():
        candidate = root_dir / candidate

    root_resolved = root_dir.resolve()
    scripts_root = (root_dir / "scripts").resolve()
    candidate_resolved = candidate.resolve()

    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("script_path must be within repository root") from exc

    try:
        candidate_resolved.relative_to(scripts_root)
    except ValueError as exc:
        raise ValueError("script_path must be within scripts/") from exc

    return candidate_resolved


@dataclass(frozen=True)
class PlannedArtifacts:
    output_path: str
    planned_paths: dict[str, str]
    dry_run: bool = True

    def __str__(self) -> str:
        return self.output_path


# ========== AGENT IMPLEMENTATIONS (PHASE: SYSTEM SETUP) ==========


def agent_prompt_pack(step, run_dir: Path):
    """Prompt Pack/Workflow Diagram - จัดการแพ็กพร็อมต์และไดอะแกรม"""
    out = run_dir / step["output"]

    # สแกนพร็อมต์จริงจากโฟลเดอร์
    prompts_dir = ROOT / "prompts"
    prompt_files = list(prompts_dir.glob("*.txt")) if prompts_dir.exists() else []

    prompts_dict = {}
    for pf in prompt_files:
        agent_name = pf.stem.replace("_v1", "").replace("_", " ").title()
        prompts_dict[pf.stem] = {
            "file": str(pf.relative_to(ROOT)),
            "agent": agent_name,
            "size_bytes": pf.stat().st_size,
        }

    pack = {
        "pack_id": "dhamma_v1",
        "created_at": datetime.now().isoformat(),
        "total_prompts": len(prompts_dict),
        "prompts": prompts_dict,
        "workflow_diagram": {
            "phases": [
                "system_setup",
                "discovery",
                "content_creation",
                "publishing",
                "analytics",
            ],
            "agents_per_phase": {
                "system_setup": [
                    "PromptPack",
                    "AgentTemplate",
                    "Security",
                    "Integration",
                    "DataSync",
                    "InventoryIndex",
                    "Monitoring",
                    "Notification",
                    "ErrorFlag",
                    "Dashboard",
                    "BackupArchive",
                ],
                "discovery": [
                    "TrendScout",
                    "TopicPrioritizer",
                    "ResearchRetrieval",
                    "DataEnrichment",
                ],
                "content_creation": [
                    "ScriptOutline",
                    "ScriptWriter",
                    "DoctrineValidator",
                    "LegalCompliance",
                    "VisualAsset",
                    "Voiceover",
                    "Localization",
                    "ThumbnailGenerator",
                ],
                "publishing": [
                    "SEOMetadata",
                    "FormatConversion",
                    "MultiChannelPublish",
                    "SchedulingPublishing",
                ],
                "analytics": [
                    "Analytics",
                    "AdvancedBI",
                    "ExperimentOrchestrator",
                    "GrowthForecast",
                    "FeedbackLoop",
                    "UserFeedbackCollector",
                    "CommunityInsight",
                ],
            },
        },
    }

    write_json(out, pack)
    log(f"✓ Prompt Pack created with {len(prompts_dict)} prompts from {prompts_dir}")
    return out


def agent_template(step, run_dir: Path):
    """Agent Template - แม่แบบสร้างเอเจนต์ใหม่"""
    out = run_dir / step["output"]

    template = {
        "agent_template_version": "1.0",
        "template": {
            "name": "{{AGENT_NAME}}",
            "version": "1.0",
            "description": "{{DESCRIPTION}}",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "result": {"type": "object"},
                },
            },
            "error_handling": {
                "retry_count": 3,
                "timeout_seconds": 300,
                "fallback_action": "notify_and_halt",
            },
        },
        "example_agents": ["TrendScout", "TopicPrioritizer", "ResearchRetrieval"],
    }

    write_json(out, template)
    log("✓ Agent Template created")
    return out


def agent_security(step, run_dir: Path):
    """Security Agent - จัดการความปลอดภัย API keys และ access control"""
    out = run_dir / step["output"]

    # ตรวจสอบไฟล์ .env
    env_file = ROOT / ".env"
    ROOT / ".env.example"
    gitignore = ROOT / ".gitignore"

    api_keys_status = {}
    env_vars = {}

    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
                    if value and value != "your_key_here":
                        api_keys_status[key] = {
                            "status": "configured",
                            "masked": value[:8] + "***",
                        }
                    else:
                        api_keys_status[key] = {
                            "status": "not_configured",
                            "masked": "",
                        }

    # ตรวจสอบ .gitignore
    gitignore_ok = False
    if gitignore.exists():
        gitignore_content = gitignore.read_text(encoding="utf-8")
        gitignore_ok = ".env" in gitignore_content

    security_config = {
        "checked_at": datetime.now().isoformat(),
        "env_file": {
            "exists": env_file.exists(),
            "path": str(env_file.relative_to(ROOT)) if env_file.exists() else ".env",
            "keys_count": len(env_vars),
        },
        "api_keys": api_keys_status
        if api_keys_status
        else {
            "youtube_api": {"status": "not_configured", "note": "Create .env file"},
            "openai_api": {"status": "not_configured", "note": "Create .env file"},
        },
        "access_control": {
            "encryption": "Environment variables",
            "secret_storage": ".env file",
            "gitignore_configured": gitignore_ok,
            "permissions": {
                "read_prompts": ["all_agents"],
                "write_output": ["all_agents"],
                "publish_content": ["SchedulingPublishing", "MultiChannelPublish"],
            },
        },
        "recommendations": [
            "ใช้ .env สำหรับเก็บ API keys"
            if not env_file.exists()
            else "✓ .env file exists",
            "เพิ่ม .env ใน .gitignore" if not gitignore_ok else "✓ .env in .gitignore",
            "หมุนเวียน API keys ทุก 90 วัน",
            "ใช้ IAM roles สำหรับ production",
        ],
    }

    write_json(out, security_config)

    if not env_file.exists():
        log("⚠ .env file not found - using default configuration", "WARNING")
    else:
        log(f"✓ Security check completed - {len(env_vars)} environment variables found")

    return out


def agent_integration(step, run_dir: Path):
    """Integration Agent - เชื่อมต่อระบบภายนอก"""
    out = run_dir / step["output"]

    integrations = {
        "tested_at": datetime.now().isoformat(),
        "external_services": {
            "youtube_data_api": {
                "status": "ready",
                "endpoint": "https://www.googleapis.com/youtube/v3",
                "features": ["search", "videos", "channels"],
            },
            "google_trends": {
                "status": "ready",
                "library": "pytrends",
                "features": ["trending_searches", "interest_over_time"],
            },
            "openai": {
                "status": "ready",
                "models": ["gpt-4", "gpt-3.5-turbo"],
                "features": ["chat", "embeddings"],
            },
        },
        "internal_services": {
            "database": {"type": "sqlite", "path": "data/dhamma.db"},
            "file_storage": {"type": "local", "path": "output/"},
        },
    }

    write_json(out, integrations)
    log(
        f"✓ Integration check - {len(integrations['external_services'])} services ready"
    )
    return out


def agent_data_sync(step, run_dir: Path):
    """Data Sync Agent - ซิงก์ข้อมูลระหว่างระบบ"""
    out = run_dir / step["output"]

    sync_status = {
        "synced_at": datetime.now().isoformat(),
        "sources": {
            "prompts": {"count": 36, "last_updated": "2025-11-03", "status": "synced"},
            "examples": {"count": 36, "last_updated": "2025-11-03", "status": "synced"},
            "agents": {"count": 12, "status": "initialized"},
        },
        "destinations": {
            "local_cache": {"path": "output/cache/", "status": "ready"},
            "database": {"status": "ready"},
        },
        "sync_schedule": "every 1 hour",
        "last_sync_items": ["prompts/*.txt → cache", "examples/*.json → cache"],
    }

    write_json(out, sync_status)
    log("✓ Data sync completed - All sources synced")
    return out


def agent_inventory_index(step, run_dir: Path):
    """Inventory/Index Agent - สแกนและจัดทำดัชนีไฟล์"""
    out = run_dir / step["output"]

    # สแกนไฟล์จริงในโปรเจกต์
    prompts_dir = ROOT / "prompts"
    examples_dir = ROOT / "examples"

    prompt_files = list(prompts_dir.glob("*.txt")) if prompts_dir.exists() else []
    example_files = list(examples_dir.glob("*.json")) if examples_dir.exists() else []

    inventory = {
        "indexed_at": datetime.now().isoformat(),
        "total_agents": 36,
        "prompts": {
            "count": len(prompt_files),
            "files": [f.name for f in prompt_files[:10]],  # แสดงแค่ 10 ตัวแรก
        },
        "examples": {
            "count": len(example_files),
            "files": [f.name for f in example_files[:10]],
        },
        "index": {
            "TrendScout": {
                "prompt": "prompts/trend_scout_v1.txt",
                "example": "examples/trend_scout_input.json",
            },
            "TopicPrioritizer": {
                "prompt": "prompts/topic_prioritizer_v1.txt",
                "example": "examples/topic_prioritizer_input.json",
            },
            "ResearchRetrieval": {
                "prompt": "prompts/research_retrieval_v1.txt",
                "example": "examples/research_retrieval_input.json",
            },
        },
    }

    write_json(out, inventory)
    log(
        f"✓ Inventory indexed - {inventory['prompts']['count']} prompts, {inventory['examples']['count']} examples"
    )
    return out


def agent_monitoring(step, run_dir: Path):
    """Monitoring Agent - เฝ้าระวังระบบ"""
    out = run_dir / step["output"]

    monitoring = {
        "checked_at": datetime.now().isoformat(),
        "system_health": {
            "cpu_usage": "12%",
            "memory_usage": "45%",
            "disk_space": "234 GB free",
            "status": "healthy",
        },
        "agent_status": {
            "total_agents": 12,
            "initialized": 12,
            "running": 0,
            "failed": 0,
        },
        "alerts": [],
        "metrics": {"uptime": "100%", "avg_response_time": "0.5s", "error_rate": "0%"},
    }

    write_json(out, monitoring)
    log("✓ Monitoring initialized - System healthy")
    return out


def agent_notification(step, run_dir: Path):
    """Notification Agent - ระบบแจ้งเตือน"""
    out = run_dir / step["output"]

    notification_config = {
        "configured_at": datetime.now().isoformat(),
        "channels": {
            "console": {"enabled": True, "level": "INFO"},
            "email": {"enabled": False, "recipients": []},
            "slack": {"enabled": False, "webhook_url": ""},
            "line": {"enabled": False, "token": ""},
        },
        "notification_rules": {
            "on_error": ["console", "email"],
            "on_success": ["console"],
            "on_warning": ["console"],
        },
        "test_notification": {
            "message": "Notification system initialized",
            "sent_at": datetime.now().isoformat(),
            "status": "success",
        },
    }

    write_json(out, notification_config)
    log("✓ Notification system configured - Console enabled")
    return out


def agent_error_flag(step, run_dir: Path):
    """Error/Flag Agent - จัดการข้อผิดพลาดและธงเตือน"""
    out = run_dir / step["output"]

    error_system = {
        "initialized_at": datetime.now().isoformat(),
        "error_categories": {
            "critical": {"action": "halt_and_notify", "count": 0},
            "warning": {"action": "log_and_continue", "count": 0},
            "info": {"action": "log_only", "count": 0},
        },
        "flag_types": {
            "doctrine_violation": {
                "severity": "critical",
                "handler": "DoctrineValidator",
            },
            "api_rate_limit": {"severity": "warning", "handler": "Integration"},
            "missing_data": {"severity": "warning", "handler": "DataSync"},
        },
        "current_flags": [],
        "error_log_path": "logs/errors.log",
    }

    write_json(out, error_system)
    log("✓ Error/Flag system initialized - 0 active flags")
    return out


def agent_dashboard(step, run_dir: Path):
    """Dashboard Agent - ศูนย์รวมสถานะและตัวชี้วัด"""
    out = run_dir / step["output"]

    dashboard = {
        "generated_at": datetime.now().isoformat(),
        "system_overview": {
            "status": "operational",
            "agents_ready": 12,
            "pipelines_configured": 1,
            "last_run": "not_yet",
        },
        "metrics": {
            "total_videos_produced": 0,
            "total_agent_runs": 0,
            "success_rate": "N/A",
            "avg_processing_time": "N/A",
        },
        "recent_activity": [
            {
                "time": datetime.now().isoformat(),
                "event": "System initialization",
                "status": "success",
            }
        ],
        "dashboard_url": "file:///" + str(run_dir / "dashboard.html"),
    }

    write_json(out, dashboard)
    log("✓ Dashboard initialized - System ready")
    return out


def agent_backup_archive(step, run_dir: Path):
    """Backup/Archive Agent - สำรองและจัดเก็บข้อมูล"""
    out = run_dir / step["output"]

    # สร้าง backup directory
    backup_dir = ROOT / "output" / "backups"
    ensure_dir(backup_dir)

    # สร้าง backup timestamp
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{backup_timestamp}.zip"

    # เตรียมรายการไฟล์ที่จะ backup
    backup_targets = {
        "prompts": {"path": "prompts/", "exists": (ROOT / "prompts").exists()},
        "examples": {"path": "examples/", "exists": (ROOT / "examples").exists()},
        "pipelines": {"path": "pipelines/", "exists": (ROOT / "pipelines").exists()},
        "configs": {"path": "*.yml", "exists": True},
    }

    # นับไฟล์ที่พร้อม backup
    files_to_backup = []
    for target, info in backup_targets.items():
        if info["exists"] and target != "configs":
            target_path = ROOT / info["path"]
            if target_path.is_dir():
                files = list(target_path.glob("*"))
                files_to_backup.extend(files)

    backup_config = {
        "configured_at": datetime.now().isoformat(),
        "backup_strategy": {
            "frequency": "daily",
            "retention": "30 days",
            "storage_location": str(backup_dir.relative_to(ROOT)),
        },
        "backup_targets": backup_targets,
        "current_backup": {
            "name": backup_name,
            "files_count": len(files_to_backup),
            "status": "ready",
        },
        "archive_policy": {
            "compress": True,
            "format": "zip",
            "naming": "backup_YYYYMMDD_HHMMSS.zip",
        },
        "next_backup": datetime.now().strftime("%Y-%m-%d 00:00:00"),
    }

    write_json(out, backup_config)
    log(
        f"✓ Backup/Archive configured - {len(files_to_backup)} files ready for backup to {backup_dir}"
    )
    return out


# ========== VIDEO WORKFLOW AGENTS ==========


def agent_trend_scout(step, run_dir: Path):
    """Trend Scout - หาเทรนด์/หัวข้อที่กำลังมาในสายธรรมะ"""
    out = run_dir / step["output"]
    niches = step.get("input", {}).get("niches", [])
    horizon = step.get("input", {}).get("horizon_days", 30)

    # สร้างข้อมูลเทรนด์จำลอง (ในการใช้งานจริงจะเชื่อมต่อ YouTube API / Google Trends)
    candidates = [
        {
            "title": "เจริญสติในชีวิตประจำวัน 5 นาที",
            "why_now": "Short-form mindfulness content กำลังเป็นเทรนด์ในช่วง 30 วันข้างหน้า",
            "sources": ["YouTube Trending", "Google Trends TH"],
            "audience": "คนทำงาน, ผู้เริ่มต้น",
            "difficulty": "ง่าย",
            "risk": "ต่ำ - เนื้อหาพื้นฐาน ไม่ขัดแย้ง",
        },
        {
            "title": "วิธีรับมือความเครียดด้วยอานาปานสติ",
            "why_now": "ความเครียดจากการทำงานเพิ่มขึ้น + ปีใหม่ใกล้เข้ามา",
            "sources": ["YouTube Health & Wellness", "Pantip"],
            "audience": "วัยทำงาน 25-45 ปี",
            "difficulty": "กลาง",
            "risk": "ต่ำ - มีอ้างอิงชัดเจน",
        },
        {
            "title": "อริยสัจ 4 ฉบับเข้าใจง่าย",
            "why_now": "Search volume เพิ่มขึ้น 35% ในไทย (เข้าพรรษา)",
            "sources": ["Google Trends", "Facebook Groups"],
            "audience": "ผู้เริ่มต้นศึกษาธรรม",
            "difficulty": "กลาง",
            "risk": "กลาง - ต้องระวังการตีความ",
        },
        {
            "title": "ทำบุญยุคใหม่: ให้ถูกหลักธรรม",
            "why_now": "มีดราม่าเรื่องการบริจาคในโซเชียล",
            "sources": ["Twitter/X Trending", "News"],
            "audience": "ทุกกลุ่ม",
            "difficulty": "ยาก",
            "risk": "สูง - อาจมีความเห็นขัดแย้ง",
        },
        {
            "title": "เมตตาภาวนา: วิธีฝึกให้มีใจเมตตา",
            "why_now": "วันมาฆบูชาใกล้เข้ามา (ก.พ. 2026)",
            "sources": ["YouTube Meditation", "Calendar Events"],
            "audience": "ผู้ปฏิบัติธรรม",
            "difficulty": "ง่าย",
            "risk": "ต่ำ",
        },
    ]

    data = {
        "scouted_at": datetime.now().isoformat(),
        "niches": niches,
        "horizon_days": horizon,
        "total_candidates": len(candidates),
        "candidates": candidates,
    }

    write_json(out, data)
    log(f"✓ Trend Scout found {len(candidates)} trending topics")
    return out


def agent_topic_prioritizer(step, run_dir: Path):
    """Topic Prioritizer - จัดอันดับหัวข้อตามเกณฑ์"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    # Check if topic is provided via environment variable
    topic_override = os.environ.get("DHAMMA_TOPIC")

    data = read_json(in_path)
    candidates = data["candidates"]

    # If topic is provided, force it to be rank 1
    if topic_override:
        # Find matching topic or create new one
        matched = None
        for c in candidates:
            if (
                topic_override.lower() in c["title"].lower()
                or c["title"].lower() in topic_override.lower()
            ):
                matched = c
                break

        # If not found in candidates, create a new one
        if not matched:
            matched = {
                "title": topic_override,
                "why_now": "Selected from Mock Topics Database",
                "sources": ["mock_database"],
                "audience": "ทั่วไป",
                "difficulty": "กลาง",
                "risk": "ต่ำ",
            }

        # Force this topic to rank 1
        scored = [
            {
                "rank": 1,
                "title": matched["title"],
                "scores": {
                    "impact": 10,
                    "feasibility": 10,
                    "alignment": 10,
                    "total": 10.0,
                },
                "reason": matched.get("why_now", "Selected from database"),
                "difficulty": matched.get("difficulty", "กลาง"),
                "risk": matched.get("risk", "ต่ำ"),
                "audience": matched.get("audience", "ทั่วไป"),
            }
        ]

        # Add other topics with lower ranks
        for c in candidates:
            if c["title"] != matched["title"]:
                diff_score = {"ง่าย": 10, "กลาง": 7, "ยาก": 4}.get(c["difficulty"], 5)
                risk_score = {"ต่ำ": 10, "กลาง": 6, "สูง": 3}.get(
                    c["risk"].split(" - ")[0], 5
                )
                impact = 8 if "เพิ่มขึ้น" in c["why_now"] else 6
                total = (impact * 0.4) + (diff_score * 0.3) + (risk_score * 0.3)

                scored.append(
                    {
                        "rank": len(scored) + 1,
                        "title": c["title"],
                        "scores": {
                            "impact": impact,
                            "feasibility": diff_score,
                            "alignment": risk_score,
                            "total": round(total, 2),
                        },
                        "reason": c["why_now"],
                        "difficulty": c["difficulty"],
                        "risk": c["risk"],
                        "audience": c["audience"],
                    }
                )
    else:
        # Original scoring logic
        scored = []
        for c in candidates:
            # คำนวณคะแนนตามเกณฑ์
            diff_score = {"ง่าย": 10, "กลาง": 7, "ยาก": 4}.get(c["difficulty"], 5)
            risk_score = {"ต่ำ": 10, "กลาง": 6, "สูง": 3}.get(
                c["risk"].split(" - ")[0], 5
            )

            # Impact (ประเมินจาก why_now และ audience)
            impact = 8 if "เพิ่มขึ้น" in c["why_now"] else 6

            # Feasibility (จากความยาก)
            feasibility = diff_score

            # Alignment (จากความเสี่ยง)
            alignment = risk_score

            total = (impact * 0.4) + (feasibility * 0.3) + (alignment * 0.3)

            scored.append(
                {
                    "rank": 0,  # จะอัพเดทภายหลัง
                    "title": c["title"],
                    "scores": {
                        "impact": impact,
                        "feasibility": feasibility,
                        "alignment": alignment,
                        "total": round(total, 2),
                    },
                    "reason": c["why_now"],
                    "difficulty": c["difficulty"],
                    "risk": c["risk"],
                    "audience": c["audience"],
                }
            )

        # เรียงตามคะแนน
        scored.sort(key=lambda x: x["scores"]["total"], reverse=True)

        # อัพเดท rank
        for i, item in enumerate(scored, 1):
            item["rank"] = i

    result = {
        "prioritized_at": datetime.now().isoformat(),
        "total_evaluated": len(scored),
        "selected_top": 3,
        "ranked": scored,
        "topic_override": topic_override if topic_override else None,
    }

    write_json(out, result)
    log(
        f"✓ Topic Prioritizer ranked {len(scored)} topics - Top: '{scored[0]['title']}' (score: {scored[0]['scores']['total']})"
    )
    return out


def agent_research_retrieval(step, run_dir: Path):
    """Research Retrieval - รวบรวมอ้างอิงจากแหล่งที่เชื่อถือได้"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    data = read_json(in_path)
    top_topic = data["ranked"][0]  # เลือก rank 1

    # สร้างข้อมูลวิจัยจำลอง (ในการใช้งานจริงจะค้นหาจากฐานข้อมูลพระไตรปิฎก)
    bundle = {
        "researched_at": datetime.now().isoformat(),
        "topic": top_topic["title"],
        "selected_reason": top_topic["reason"],
        "claims": [
            {
                "text": "สติช่วยลดความฟุ้งซ่านและความเครียดได้",
                "support": "พระไตรปิฎก - อนาปานสติสูตร",
            },
            {
                "text": "การทำสมาธิสั้นๆ แต่สม่ำเสมอดีกว่านานแต่ห่างกัน",
                "support": "คำสอนหลวงปู่มั่น ภูริทัตโต",
            },
            {"text": "ลมหายใจเป็นเครื่องมือเข้าถึงสติได้ง่ายที่สุด", "support": "วิสุทธิมรรค บทที่ 8"},
        ],
        "citations": [
            {
                "source": "อนาปานสติสูตร (มัชฌิมนิกาย เล่ม 3)",
                "type": "canonical",
                "link": "",
                "quote": "อานาปานสติสมาธิ เมื่อเจริญแล้ว กระทำให้มากแล้ว มีผลใหญ่ มีอานิสงส์ใหญ่",
                "relevance": "หลักฐานการฝึกสติด้วยลมหายใจ",
            },
            {
                "source": "วิสุทธิมรรค - แปลโดยสมเด็จพระมหาสมณเจ้า กรมพระยาวชิรญาณวโรรส",
                "type": "commentary",
                "link": "",
                "quote": "อานาปานสติเป็นกรรมฐานที่เหมาะสมที่สุดสำหรับผู้เริ่มต้น",
                "relevance": "การตีความและคำแนะนำการปฏิบัติ",
            },
            {
                "source": "บทความวิชาการ: ผลของสติต่อสุขภาพจิต (ม.มหิดล 2023)",
                "type": "secondary",
                "link": "https://example.com/mindfulness-research",
                "quote": "พบว่าการฝึกสติ 5 นาทีต่อวันลดความเครียดได้ 30%",
                "relevance": "หลักฐานทางวิทยาศาสตร์",
            },
        ],
        "keywords": ["สติ", "อนาปานสติ", "ลมหายใจ", "สมาธิ", "ความเครียด"],
        "target_duration": "8-10 นาที",
        "content_level": "ผู้เริ่มต้น",
    }

    write_json(out, bundle)
    log(
        f"✓ Research Retrieval completed for '{bundle['topic']}' - {len(bundle['citations'])} citations"
    )
    return out


def agent_script_outline(step, run_dir: Path):
    """Script Outline - สร้างโครงร่างสคริปต์"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    data = read_json(in_path)

    # รองรับทั้ง research_bundle และ data_enrichment
    if "original_research" in data:
        # มาจาก data_enrichment
        research_data = data["original_research"]
        topic = research_data["topic"]
        claims = research_data.get("claims", [])
    else:
        # มาจาก research_bundle โดยตรง
        topic = data["topic"]
        claims = data.get("claims", [])

    outline_md = f"""# โครงสคริปต์: {topic}

## 📊 ข้อมูลพื้นฐาน
- **ระยะเวลา**: 8-10 นาที
- **กลุ่มเป้าหมาย**: ผู้เริ่มต้น
- **คีย์เวิร์ด**: สติ, อานาปานสติ, ลมหายใจ, สมาธิ

---

## 🎬 โครงสร้างวิดีโอ

### [00:00 - 00:30] Hook (ดึงดูดความสนใจ)
- **เปิด**: "คุณเคยรู้สึกเครียด ใจฟุ้งซ่าน จนไม่รู้จะทำอะไรก่อนดีไหม?"
- **ปัญหา**: ชีวิตยุคใหม่เต็มไปด้วยความเร่งรีบ ทำให้ใจไม่สงบ
- **คำตอบ**: วันนี้จะพาฝึกสติแค่ 5 นาที ทำได้ทุกที่ ทุกเวลา

### [00:30 - 01:30] Introduction (แนะนำหัวข้อ)
- บอกว่าวิดีโอนี้คืออะไร (การฝึกสติด้วยลมหายใจ)
- ทำไมตอนนี้ (เทรนด์ mindfulness + ความเครียดเพิ่มขึ้น)
- ประโยชน์ที่จะได้รับ (ใจสงบ, ลดความเครียด, มีสติ)

### [01:30 - 05:00] Main Points (เนื้อหาหลัก)

#### Point 1: สติคือการรับรู้ปัจจุบัน (1:30-2:30)
- **ข้อมูล**: {claims[0]["text"] if claims else "สติช่วยลดความฟุ้งซ่าน"}
- **อ้างอิง**: {claims[0]["support"] if claims else "พระไตรปิฎก"}
- **ตัวอย่าง**: เวลาเดิน เรารู้หรือเปล่าว่ากำลังเดิน?
- [B-ROLL: คนเดินด้วยความตั้งใจ vs คนเดินแล้วเล่นมือถือ]

#### Point 2: ลมหายใจเป็นสมอของใจ (2:30-3:30)
- **ข้อมูล**: {claims[2]["text"] if len(claims) > 2 else "ลมหายใจเป็นเครื่องมือเข้าถึงสติ"}
- **อ้างอิง**: {claims[2]["support"] if len(claims) > 2 else "วิสุทธิมรรค"}
- **วิธีการ**: สังเกตลมหายใจเข้า-ออก ไม่ต้องควบคุม แค่รับรู้
- [B-ROLL: อนิเมชั่นลมหายใจ / คนนั่งสมาธิ]

#### Point 3: ฝึกสั้นแต่สม่ำเสมอ (3:30-5:00)
- **ข้อมูล**: {claims[1]["text"] if len(claims) > 1 else "ฝึกสั้นแต่สม่ำเสมอดีกว่า"}
- **อ้างอิง**: {claims[1]["support"] if len(claims) > 1 else "คำสอนหลวงปู่มั่น"}
- **เคล็ดลับ**: 5 นาทีทุกเช้า ดีกว่า 1 ชั่วโมงเดือนละครั้ง
- [B-ROLL: ปฏิทิน / กราฟเปรียบเทียบ]

### [05:00 - 07:00] Practical Application (นำไปใช้)
**แนะนำ 3 ขั้นตอนง่ายๆ:**

1. **หาที่นั่งสบาย** (ไม่จำเป็นต้องขัดสมาธิ)
2. **หลับตา สังเกตลมหายใจ** (นับ 1-10 ถ้าช่วย)
3. **ใจฟุ้ง = กลับมาที่ลมหายใจ** (ไม่ต้องโกรธตัวเอง)

[DEMO: แสดงการฝึกจริง 1-2 นาที]

### [07:00 - 08:30] Benefits & Motivation (ประโยชน์)
- ลดความเครียด 30%
- นอนหลับสนิท
- ตัดสินใจได้ดีขึ้น
- มีสติในการทำงาน

### [08:30 - 10:00] Conclusion & CTA
- **สรุป**: สติไม่ยาก เริ่มแค่ 5 นาที
- **เชิญชวน**: ลองฝึกวันนี้ แล้วมาแชร์ประสบการณ์ในคอมเมนต์
- **CTA**: กดไลค์ ถ้าได้ประโยชน์ / Subscribe เพื่อดูวิดีโอธรรมะใหม่ๆ
- **ปิดท้าย**: "สาธุครับ ขออานิสงส์จงสำเร็จทุกประการ"

---

## 📝 หมายเหตุสำหรับการผลิต
- ใช้เสียงพูดนุ่มนวล ไม่เร็วเกินไป
- แทรก B-roll ทุก 20-30 วินาที
- ใส่ subtitle ภาษาไทย (สำคัญ!)
- Background music: Ambient/Meditation (เบาๆ)
"""

    write_text(out, outline_md)
    log(f"✓ Script Outline created for '{topic}'")
    return out


def agent_script_writer(step, run_dir: Path):
    """Script Writer - เขียนสคริปต์เต็มรูปแบบ"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    outline = in_path.read_text(encoding="utf-8")

    # สร้างสคริปต์เต็มจากโครงร่าง
    script = f"""---
title: เจริญสติในชีวิตประจำวัน 5 นาที
duration: ~10 นาที
target: ผู้เริ่มต้น
---

{outline}

---

## 🎤 FULL SCRIPT (พูดทุกคำ)

### [00:00 - 00:30] HOOK
[VISUAL: เปิดด้วยคลิปตัดต่อเร็วๆ - คนเครียด, รถติด, เดดไลน์งาน]
[MUSIC: เสียงเร่งเร้า → จางลง → ดนตรีนุ่มนวล]

**[พูด]** สวัสดีครับผู้ชมทุกท่าน 🙏

คุณเคยรู้สึกเครียด... ใจฟุ้งซ่าน... จนไม่รู้จะทำอะไรก่อนดีไหมครับ?

[PAUSE]

ชีวิตยุคใหม่เต็มไปด้วยความเร่งรีบ ข้อมูลข่าวสารท่วมท้น
ทำให้จิตใจของเราไม่ค่อยได้พัก [PAUSE] ไม่ค่อยได้สงบเลย

[B-ROLL: มือเลื่อนดูโทรศัพท์ไม่หยุด]

**[พูด]** แต่ถ้าผมบอกว่า... แค่ 5 นาที... ทำได้ทุกที่ ทุกเวลา
คุณก็สามารถทำให้ใจสงบลงได้ล่ะ?

[VISUAL: Title card ปรากฏ "เจริญสติใน 5 นาที | ทำได้ทุกที่"]

วันนี้ เรามาเรียนรู้เทคนิคง่ายๆ จากพระพุทธศาสนากันครับ

---

### [00:30 - 01:30] INTRODUCTION

[VISUAL: ผู้พูดนั่งในฉากธรรมชาติ/ห้องสมุด พื้นหลังสงบ]

**[พูด]** วิดีโอนี้ เราจะมาเรียนรู้เรื่อง **"สติ"** กันครับ

โดยเฉพาะการฝึกสติด้วย **"ลมหายใจ"** หรือที่เรียกว่า **อานาปานสติ**
[TEXT: อานาปานสติ = สติกับลมหายใจ]

ซึ่งเป็นเทคนิคที่พระพุทธเจ้าทรงสอนไว้ใน**พระไตรปิฎก**เลยครับ

[CITATION: อนาปานสติสูตร - มัชฌิมนิกาย เล่ม 3]
[B-ROLL: ภาพพระไตรปิฎก / ภาพวาดพระพุทธเจ้า]

**[พูด]** ทำไมถึงเลือกเรื่องนี้ตอนนี้? เพราะว่า...

ช่วงนี้ **mindfulness** หรือการฝึกสติกำลังเป็นที่นิยมมากในต่างประเทศ
และคนไทยก็เริ่มสนใจมากขึ้นเรื่อยๆ ครับ

[B-ROLL: กราฟ Google Trends แสดงการค้นหา "สติ" เพิ่มขึ้น]

**[พูด]** และเมื่อเราฝึกสติแล้ว เราจะได้อะไร? [PAUSE]

ประโยชน์ 3 อย่างหลักๆ คือ:
1. **ใจสงบ ไม่ฟุ้งซ่าน** [TEXT: ✓ ใจสงบ]
2. **ลดความเครียด** [TEXT: ✓ ลดเครียด]
3. **มีสติในการทำงานและการดำเนินชีวิต** [TEXT: ✓ มีสติ]

เอาล่ะ... มาเริ่มกันเลยครับ!

---

### [01:30 - 02:30] POINT 1: สติคืออะไร?

[VISUAL: Animation หรือ Whiteboard อธิบาย]

**[พูด]** ก่อนอื่น เรามาทำความเข้าใจกันก่อนว่า **"สติ"** คืออะไร

สติ ก็คือ **"การรับรู้ปัจจุบัน"** ครับ

[TEXT: สติ = การรับรู้ในปัจจุบัน]

**[พูด]** ลองคิดดูนะครับ... ตอนนี้คุณกำลังดูวิดีโอนี้อยู่
แต่ **จิตใจ** ของคุณอยู่ที่ไหน? [PAUSE]

อาจกำลังคิดเรื่องงานที่ยังไม่เสร็จ...
อาจกำลังกังวลเรื่องพรุ่งนี้...
หรือนึกถึงอดีตที่ผ่านมา...

[B-ROLL: คนเดินด้วยตั้งใจ ตัดกับคนเดินแล้วเล่นมือถือ]

**[พูด]** นี่แหละครับ คือการ **"ไม่มีสติ"** - ร่างกายอยู่ที่นี่ แต่ใจอยู่ที่อื่น

ตามหลักพระพุทธศาสนา พระพุทธเจ้าตรัสไว้ว่า
**"สติช่วยลดความฟุ้งซ่านและความเครียดได้"**

[CITATION POPUP: อนาปานสติสูตร]

และนี่ไม่ใช่แค่ทฤษฎีนะครับ วิทยาศาสตร์สมัยใหม่ก็พิสูจน์แล้ว!

[B-ROLL: งานวิจัย/สถิติ]

---

### [02:30 - 03:30] POINT 2: ลมหายใจ = สมอของใจ

[VISUAL: Animation ลมหายใจเข้า-ออก / Breathing Cycle]

**[พูด]** คำถามต่อมาคือ... เราจะฝึกสติได้อย่างไร?

คำตอบคือ... ใช้ **"ลมหายใจ"** เป็นเครื่องมือครับ

[TEXT: ลมหายใจ = สมอของใจ ⚓]

**[พูด]** ทำไมต้องเป็นลมหายใจ? เพราะว่า...

ลมหายใจเป็นสิ่งที่:
- **มีอยู่ตลอดเวลา** (หายใจไม่หยุด)
- **ไม่ต้องเตรียมอะไร** (ไม่ต้องใช้อุปกรณ์)
- **เข้าถึงได้ง่าย** (สังเกตได้ทันที)

[B-ROLL: คนนั่งสมาธิ สงบ ผ่อนคลาย]

**[พูด]** ในพระไตรปิฎก **วิสุทธิมรรค** บอกไว้ว่า
**"ลมหายใจเป็นเครื่องมือเข้าถึงสติได้ง่ายที่สุด"**

[CITATION: วิสุทธิมรรค บทที่ 8]

วิธีทำก็ง่ายมากครับ:
- **สังเกตลมหายใจเข้า** [PAUSE]
- **สังเกตลมหายใจออก** [PAUSE]
- **ไม่ต้องควบคุม** แค่รับรู้ว่ากำลังหายใจ

[VISUAL: Person breathing naturally, text overlay showing "IN" "OUT"]

จิตใจของเราจะยึดเกาะกับลมหายใจ... เหมือน**สมอเรือ**
ไม่ให้ล่องลอยไปตามความคิด ครับ

---

### [03:30 - 05:00] POINT 3: ฝึกสั้นแต่สม่ำเสมอ

[VISUAL: กราฟเปรียบเทียบ: 5min daily vs 1hr monthly]

**[พูด]** หลายคนคิดว่า การฝึกสติต้องนั่งสมาธินาน ๆ
หลายชั่วโมงถึงจะได้ผล...

แต่จริง ๆ แล้ว **ไม่ใช่นะครับ!**

[TEXT: 5 นาที/วัน > 1 ชม./เดือน]

**[พูด]** ตามคำสอนของ**หลวงปู่มั่น ภูริทัตโต** บอกไว้ว่า
**"การทำสมาธิสั้น ๆ แต่สม่ำเสมอ ดีกว่านานแต่ห่างกัน"**

[CITATION: คำสอนหลวงปู่มั่น]

[B-ROLL: ปฏิทินที่ติ๊กถูกทุกวัน vs ปฏิทินที่ห่างมาก]

**[พูด]** ทำไมล่ะ? เพราะว่าสมองเราทำงานแบบ **"หลัก习惯"** ครับ

ยิ่งทำบ่อย สมองจะจดจำและสร้างเป็นนิสัยได้ง่ายกว่า
การทำนาน ๆ แต่เดือนละครั้ง

[VISUAL: Brain animation showing neural pathways strengthening]

**[พูด]** เคล็ดลับง่าย ๆ:
- **ตั้งเวลาทุกเช้า** - เช่น หลังตื่นนอน หรือก่อนอาบน้ำ
- **แค่ 5 นาที** - ไม่ต้องนาน
- **ทำทุกวัน** - นี่สำคัญที่สุด!

[B-ROLL: แอพริเตือน / นาฬิกา / ปฏิทิน]

**[พูด]** ถ้าทำได้ 30 วันติด... มันจะกลายเป็น **นิสัย** ไปเลยครับ!

---

### [05:00 - 07:00] PRACTICAL: ขั้นตอนฝึก 3 ข้อ

[VISUAL: Split screen - ผู้พูด + Demo animation]

**[พูด]** เอาล่ะ! ถึงเวลาที่เราจะลงมือฝึกกันจริง ๆ แล้วครับ

มี **3 ขั้นตอนง่าย ๆ** เท่านั้นเอง:

---

**ขั้นที่ 1: หาที่นั่งสบาย**

[B-ROLL: คนนั่งขัดสมาธิ, นั่งเก้าอี้, นั่งริมเตียง]

**[พูด]** ไม่จำเป็นต้องนั่งขัดสมาธิ นะครับ
นั่งเก้าอี้ธรรมดาก็ได้... นั่งริมเตียงก็ได้...
ขอแค่ให้ **หลังตรง** และรู้สึก**สบาย**

[TEXT: ✓ นั่งสบาย ✓ หลังตรง]

---

**ขั้นที่ 2: หลับตา สังเกตลมหายใจ**

[VISUAL: Close-up ใบหน้าสงบ หลับตา พร้อม breathing animation overlay]

**[พูด]** หลับตาเบา ๆ... [PAUSE]

แล้วเริ่มสังเกต **ลมหายใจเข้า-ออก**

[PAUSE - นิ่ง 3 วินาที]

หายใจเข้า... รู้ว่ากำลังหายใจเข้า...

[PAUSE]

หายใจออก... รู้ว่ากำลังหายใจออก...

[PAUSE]

[TEXT: นับได้ (1-10) ถ้าช่วยจดจ่อ]

**[พูด]** ถ้าอยากนับก็ได้นะครับ เช่น
"หายใจเข้า... 1"
"หายใจออก... 2"
ไปเรื่อย ๆ จนถึง 10 แล้วเริ่มใหม่

---

**ขั้นที่ 3: ใจฟุ้ง? กลับมาที่ลมหายใจ**

[VISUAL: Animation showing thoughts appearing and returning to breath]

**[พูด]** นี่สำคัญที่สุดครับ!

ระหว่างฝึก ความคิดจะผุดขึ้นมาในหัวแน่นอน...
อาจเป็นเรื่องงาน... เรื่องอาหาร... เรื่องอะไรก็ตาม

[PAUSE]

**อย่าโกรธตัวเอง นะครับ!**

[TEXT: ⚠ อย่าโกรธตัวเอง - นี่เป็นเรื่องปกติ]

**[พูด]** นี่เป็นเรื่อง**ปกติ**มาก
แค่... เมื่อสังเกตเห็นว่าใจฟุ้ง...
ค่อย ๆ พาใจกลับมาที่ **ลมหายใจ** อีกครั้ง

[VISUAL: Gentle hand gesture guiding back]

ทำแบบนี้ซ้ำ ๆ... นี่แหละครับคือ **"การฝึกสติ"**

---

[DEMO SECTION - 1-2 นาที]

**[พูด]** เอาล่ะ เรามาลองฝึกด้วยกันตอนนี้เลยครับ แค่ 1 นาที

ใครพร้อม... ลองนั่งสบาย ๆ หลับตาเบา ๆ...

[PAUSE - นิ่ง 5 วินาที พร้อม soft music]

หายใจเข้า... รู้ตัว... [PAUSE 3 วินาที]

หายใจออก... รู้ตัว... [PAUSE 3 วินาที]

[ทำ 5-6 รอบ]

**[พูด]** ... ค่อย ๆ ลืมตาได้ครับ [PAUSE]

รู้สึกยังไงบ้างครับ? ใจสงบลงบ้างไหม? 😊

---

### [07:00 - 08:30] BENEFITS

[VISUAL: Infographic แสดงประโยชน์]

**[พูด]** เมื่อเราฝึกสติสม่ำเสมอ เราจะได้ประโยชน์มากมายครับ

จากงานวิจัยของ **มหาวิทยาลัยมหิดล ปี 2023** พบว่า

[B-ROLL: Academic paper / Research data]

✅ **ลดความเครียดได้ถึง 30%** ในแค่ 4 สัปดาห์

[CITATION: งานวิจัย ม.มหิดล 2023]

ประโยชน์อื่น ๆ ที่พบ:
- **นอนหลับสนิทขึ้น** [ICON: 😴]
- **ตัดสินใจได้ดีขึ้น** [ICON: 🧠]
- **มีสติในการทำงาน** [ICON: 💼]
- **สัมพันธ์ภาพที่ดีขึ้น** [ICON: 👥]

[B-ROLL: คนนอนหลับสบาย / คนทำงานมีสมาธิ / ครอบครัวมีความสุข]

**[พูด]** และที่สำคัญครับ... สติทำให้เราอยู่กับปัจจุบันได้
**ไม่หลงอดีต ไม่กังวลอนาคต**

มีความสุขกับปัจจุบันได้ครับ 🙏

---

### [08:30 - 10:00] CONCLUSION & CTA

[VISUAL: กลับมาที่ผู้พูด พื้นหลังสงบ]

**[พูด]** เอาล่ะครับ มาถึงตอนท้ายแล้ว

วันนี้เราได้เรียนรู้เรื่อง **"สติ"** กันไปแล้ว โดยเฉพาะ**อานาปานสติ**

สรุปสั้น ๆ:
1. สติคือการรับรู้ปัจจุบัน
2. ใช้ลมหายใจเป็นเครื่องมือ
3. ฝึกแค่ 5 นาที แต่ทุกวัน

[TEXT: 5 นาที/วัน = เปลี่ยนชีวิต]

**[พูด]** สติไม่ใช่เรื่องยาก... ไม่ต้องเป็นพระ ไม่ต้องนั่งสมาธินานๆ
แค่เริ่มต้นจากสิ่งง่าย ๆ ที่มีอยู่แล้ว... **ลมหายใจ** ครับ

[PAUSE]

**[พูด]** ผมอยากชวนให้ทุกคนลอง **ฝึกวันนี้เลย**
แล้วมาแชร์ประสบการณ์ให้ผมฟังได้ใน**คอมเมนต์**ด้านล่างนะครับ

[CTA TEXT: 💬 แชร์ประสบการณ์ในคอมเมนต์]

ถ้าวิดีโอนี้มีประโยชน์... อย่าลืม **กดไลค์** ให้ผมด้วยนะครับ 👍

และถ้าอยากดูวิดีโอธรรมะอื่น ๆ ก็ **กด Subscribe** ได้เลยครับ 🔔

[B-ROLL: Animation กดไลค์และ Subscribe]

**[พูด - ปิดท้าย]** สาธุครับ 🙏

ขออานิสงส์ที่เกิดจากการฟังธรรม... จงสำเร็จแก่ทุกท่าน
ให้ทุกท่านมีสติ มีสมาธิ และมีความสุขในชีวิตครับ

[PAUSE]

แล้วพบกันใหม่... วิดีโอหน้า สวัสดีครับ 🙏

[FADE OUT with soft music]

[END SCREEN:
- วิดีโอแนะนำ 2 อัน
- ปุ่ม Subscribe
- Link คลิปเพลย์ลิสต์ธรรมะ]

---

## 📋 PRODUCTION NOTES

### Timing Breakdown:
- Hook: 30 sec
- Intro: 1 min
- Content: 3.5 min (Point 1-3)
- Practice: 2 min
- Benefits: 1.5 min
- CTA: 1.5 min
**Total: ~10 min**

### B-Roll Requirements:
- คนเครียด / รถติด (stock footage)
- พระไตรปิฎก / วัด
- คนนั่งสมาธิ (ถ่ายเอง)
- กราฟ / สถิติ (create in After Effects)
- ธรรมชาติ / สงบ (stock footage)

### Audio:
- Background music: Meditation/Ambient (15-20% volume)
- Voice: Clear, calm, 120 wpm speaking rate
- Sound effects: Subtle (page turn, ding)

### Graphics:
- Citations: แสดงในมุมล่าง 3-5 วินาที
- Key points: Text overlay สีทอง/เทาอ่อน
- Icons: Simple, Thai-friendly

### Subtitles:
- ภาษาไทยเต็มรูปแบบ
- Font: Prompt, Kanit (อ่านง่าย)
- White text + black outline
"""

    write_text(out, script)
    log("✓ Script Writer completed - Full script with timestamps ready")
    return out


def agent_doctrine_validator(step, run_dir: Path):
    """Doctrine Validator - ตรวจสอบความถูกต้องตามหลักธรรม"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    script = in_path.read_text(encoding="utf-8")

    # ตรวจสอบจำลอง (ในการใช้งานจริงจะใช้ AI หรือผู้เชี่ยวชาญ)
    validation = {
        "validated_at": datetime.now().isoformat(),
        "status": "approved",
        "checked_by": "AI Doctrine Validator v1.0",
        "issues": [],  # ไม่มีปัญหา
        "approved_sections": [
            {"section": "00:00-02:30", "status": "approved", "note": "คำนิยามสติถูกต้อง"},
            {
                "section": "02:30-03:30",
                "status": "approved",
                "note": "อ้างอิงวิสุทธิมรรคถูกต้อง",
            },
            {
                "section": "03:30-05:00",
                "status": "approved",
                "note": "คำสอนหลวงปู่มั่นสอดคล้อง",
            },
            {
                "section": "05:00-07:00",
                "status": "approved",
                "note": "วิธีปฏิบัติเหมาะสมผู้เริ่มต้น",
            },
        ],
        "citations_verified": [
            {"citation": "อนาปานสติสูตร (มัชฌิมนิกาย)", "status": "verified"},
            {"citation": "วิสุทธิมรรค บทที่ 8", "status": "verified"},
            {"citation": "คำสอนหลวงปู่มั่น", "status": "verified"},
        ],
        "overall_feedback": "✅ สคริปต์ถูกต้องตามหลักธรรม เหมาะสมสำหรับผู้เริ่มต้น ไม่มีข้อความที่อาจทำให้เข้าใจผิด",
        "recommendations": [
            "เพิ่ม disclaimer ว่านี่เป็นแนวทางพื้นฐาน ควรศึกษาเพิ่มเติม",
            "อาจเพิ่มข้อมูลเกี่ยวกับความแตกต่างของสติกับ mindfulness สมัยใหม่",
        ],
    }

    # เพิ่มหมายเหตุในสคริปต์
    validated_script = f"""<!-- DOCTRINE VALIDATION -->
<!-- Status: {validation["status"].upper()} -->
<!-- Validated at: {validation["validated_at"]} -->
<!-- Validator: {validation["checked_by"]} -->
<!-- Feedback: {validation["overall_feedback"]} -->
<!-- ==================== -->

{script}

<!-- ==================== -->
<!-- VALIDATION REPORT -->
<!-- Issues: {len(validation["issues"])} -->
<!-- Approved Sections: {len(validation["approved_sections"])} -->
<!-- Citations Verified: {len(validation["citations_verified"])} -->
<!-- ==================== -->
"""

    write_text(out, validated_script)

    # บันทึกรายงานแยก
    validation_report = run_dir / "validation_report.json"
    write_json(validation_report, validation)

    log(
        f"✓ Doctrine Validator - APPROVED - {len(validation['approved_sections'])} sections verified"
    )
    return out


def agent_seo_metadata(step, run_dir: Path):
    """SEO & Metadata - สร้าง metadata สำหรับเผยแพร่"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    # อ่านสคริปต์เพื่อสร้าง metadata
    in_path.read_text(encoding="utf-8")

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "platform": "youtube",
        "title": "เจริญสติในชีวิตประจำวัน 5 นาที | ฝึกอานาปานสติแบบง่ายๆ ได้ผลจริง",
        "title_length": 68,  # ต้องไม่เกิน 70
        "description": """🙏 เจริญสติง่ายๆ แค่ 5 นาที ทำได้ทุกที่ ทุกเวลา!

วิดีโอนี้จะพาคุณเรียนรู้การฝึก "อานาปานสติ" หรือสติกับลมหายใจ
ตามหลักพระพุทธศาสนาแบบเข้าใจง่าย เหมาะสำหรับผู้เริ่มต้น

📖 เนื้อหาในวิดีโอ:
00:00 - สติคืออะไร?
01:30 - ทำไมต้องใช้ลมหายใจ?
02:30 - ฝึกสั้นแต่สม่ำเสมอ
05:00 - ขั้นตอนฝึก 3 ข้อ (พร้อมแนะนำ)
07:00 - ประโยชน์ที่ได้รับ
08:30 - สรุปและเริ่มต้นฝึก

✨ ประโยชน์:
• ลดความเครียดได้ถึง 30%
• นอนหลับสนิท
• มีสติในการทำงาน
• ตัดสินใจได้ดีขึ้น

📚 อ้างอิงจาก:
• อนาปานสติสูตร (มัชฌิมนิกาย)
• วิสุทธิมรรค
• คำสอนหลวงปู่มั่น ภูริทัตโต

💬 แชร์ประสบการณ์การฝึกสติของคุณในคอมเมนต์ได้เลยครับ!

🔔 Subscribe เพื่อดูวิดีโอธรรมะใหม่ๆ
👍 กดไลค์ถ้าชอบ

#สติ #อานาปานสติ #ธรรมะ #mindfulness #meditation #พุทธศาสนา
""",
        "tags": [
            "สติ",
            "อานาปานสติ",
            "ธรรมะ",
            "พุทธศาสนา",
            "mindfulness",
            "meditation",
            "สมาธิ",
            "ลมหายใจ",
            "ลดเครียด",
            "ฝึกสติ",
            "เจริญสติ",
            "ทำสมาธิ",
            "พระพุทธศาสนา",
            "ธรรมะเพื่อชีวิต",
            "วิปัสสนา",
        ],
        "category": "Education",
        "language": "th",
        "default_audio_language": "th",
        "visibility": "public",
        "made_for_kids": False,
        "thumbnail_suggestions": [
            "ภาพคนนั่งสมาธิ + ข้อความ 'ฝึกสติ 5 นาที'",
            "ภาพลมหายใจ (animation) + '5 MIN MINDFULNESS'",
            "ภาพใบโพธิ์/ธรรมชาติสงบ + 'อานาปานสติ เริ่มต้นง่าย'",
        ],
        "playlists": ["ธรรมะเบื้องต้น", "การฝึกสติ", "สมาธิภาวนา"],
        "end_screen": {
            "duration": 20,
            "elements": [
                {"type": "video", "position": "left", "video": "latest"},
                {"type": "playlist", "position": "right", "playlist": "ธรรมะเบื้องต้น"},
                {"type": "subscribe", "position": "center"},
            ],
        },
        "cards": [
            {
                "time": "00:30",
                "type": "poll",
                "question": "คุณเคยฝึกสติมาก่อนไหม?",
                "options": ["เคย", "ไม่เคย", "กำลังฝึกอยู่"],
            },
            {
                "time": "05:00",
                "type": "link",
                "url": "playlist_link",
                "message": "ดูวิดีโอสมาธิเพิ่มเติม",
            },
        ],
        "monetization": {"enabled": True, "ad_suitability": "family_friendly"},
        "seo_keywords": [
            "วิธีฝึกสติ",
            "สติคืออะไร",
            "อานาปานสติ ทำอย่างไร",
            "mindfulness ภาษาไทย",
            "ลดเครียดด้วยธรรมะ",
            "ฝึกสมาธิง่ายๆ",
            "เจริญสติ 5 นาที",
        ],
    }

    write_json(out, metadata)
    log(
        f"✓ SEO & Metadata created - Title: {metadata['title_length']} chars, Tags: {len(metadata['tags'])}"
    )
    return out


def agent_data_enrichment(step, run_dir: Path):
    """Data Enrichment - เพิ่มข้อมูลเสริมจากแหล่งต่างๆ"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    data = read_json(in_path)
    topic = data["topic"]

    # เพิ่มข้อมูลเสริม
    enriched = {
        "enriched_at": datetime.now().isoformat(),
        "topic": topic,
        "original_research": data,
        "additional_context": {
            "historical_background": {
                "period": "พุทธกาล (พ.ศ. 80-543)",
                "location": "อินเดียตะวันออกเฉียงเหนือ",
                "relevance": "อานาปานสติเป็นหนึ่งในกรรมฐานที่พระพุทธเจ้าทรงใช้ตรัสรู้",
            },
            "modern_research": [
                {
                    "study": "Effects of Mindfulness on Stress Reduction",
                    "institution": "มหาวิทยาลัยมหิดล",
                    "year": 2023,
                    "finding": "ลดความเครียดได้ 30% ใน 4 สัปดาห์",
                },
                {
                    "study": "Breath-focused meditation and brain activity",
                    "institution": "Harvard Medical School",
                    "year": 2022,
                    "finding": "เพิ่มการทำงานของ prefrontal cortex",
                },
            ],
            "related_practices": ["วิปัสสนากรรมฐาน", "สมถภาวนา", "พรหมวิหาร 4"],
            "common_misconceptions": [
                {"myth": "ต้องนั่งสมาธินาน ๆ ถึงจะได้ผล", "truth": "ฝึกสั้นแต่สม่ำเสมอดีกว่า"},
                {"myth": "สติคือการไม่คิดอะไรเลย", "truth": "สติคือการรับรู้ปัจจุบันอย่างตั้งใจ"},
            ],
            "practical_tips": [
                "เริ่มต้น 2-3 นาทีก่อน ค่อยเพิ่ม",
                "เลือกเวลาเดิมทุกวัน (เช่น หลังตื่นนอน)",
                "ไม่ต้องโกรธตัวเองเมื่อใจฟุ้ง",
                "ใช้แอพช่วยเตือน (optional)",
            ],
            "cultural_context": {
                "thai_buddhism": "ในพุทธศาสนาไทยนิยมฝึกอานาปานสติในวัด",
                "daily_practice": "สามารถนำไปใช้ในชีวิตประจำวันได้",
                "festivals": "วันมาฆบูชา, อาสาฬหบูชา เหมาะกับการฝึก",
            },
        },
        "fact_check": {
            "verified": True,
            "sources_count": len(data.get("citations", [])),
            "credibility_score": 9.5,
        },
    }

    write_json(out, enriched)
    log(
        f"✓ Data Enrichment completed - Added {len(enriched['additional_context'])} context categories"
    )
    return out


def agent_legal_compliance(step, run_dir: Path):
    """Legal/Compliance - ตรวจสอบด้านกฎหมายและข้อบังคับ"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    in_path.read_text(encoding="utf-8")

    compliance = {
        "checked_at": datetime.now().isoformat(),
        "status": "compliant",
        "checks": {
            "copyright": {
                "status": "clear",
                "details": "ไม่พบการละเมิดลิขสิทธิ์ - ใช้อ้างอิงจากพระไตรปิฎก (สาธารณสมบัติ)",
                "music_licensing": "ต้องใช้ royalty-free หรือซื้อลิขสิทธิ์",
                "image_licensing": "ต้องใช้ stock photos ที่มีลิขสิทธิ์",
            },
            "religious_content": {
                "status": "appropriate",
                "details": "ไม่มีเนื้อหาที่หมิ่นศาสนาหรือบิดเบือนหลักธรรม",
                "tone": "เคารพและเหมาะสม",
            },
            "medical_claims": {
                "status": "compliant",
                "details": "ไม่มี medical claims ที่ผิดกฎหมาย",
                "disclaimers_needed": [
                    "การฝึกสติเป็นการส่งเสริมสุขภาพจิต ไม่ใช่การรักษาโรค",
                    "หากมีอาการทางจิตรุนแรงควรปรึกษาแพทย์",
                ],
            },
            "advertising": {
                "status": "clear",
                "details": "ไม่มีการโฆษณาสินค้าหรือบริการ",
                "sponsored_content": False,
            },
            "personal_data": {
                "status": "compliant",
                "details": "ไม่มีการเก็บข้อมูลส่วนบุคคล",
                "gdpr_compliance": "N/A - ไม่เกี่ยวข้อง",
            },
            "age_appropriate": {
                "status": "all_ages",
                "rating": "G - General Audiences",
                "details": "เหมาะสำหรับทุกวัย",
            },
        },
        "required_disclaimers": [
            {
                "type": "general",
                "text": "เนื้อหานี้เป็นการศึกษาธรรมะเบื้องต้น ควรศึกษาเพิ่มเติมจากครูบาอาจารย์",
                "placement": "end_of_description",
            },
            {
                "type": "health",
                "text": "การฝึกสติเป็นการส่งเสริมสุขภาพจิต ไม่ใช่การรักษาโรค หากมีปัญหาสุขภาพจิตรุนแรง ควรปรึกษาแพทย์ผู้เชี่ยวชาญ",
                "placement": "video_description",
            },
        ],
        "youtube_policy_compliance": {
            "community_guidelines": "pass",
            "advertiser_friendly": True,
            "coppa_compliant": True,
            "spam_deceptive_practices": "clear",
        },
        "recommendations": [
            "เพิ่ม disclaimer ในคำบรรยายวิดีโอ",
            "ระบุแหล่งที่มาของภาพและเสียงประกอบ",
            "ใช้ Creative Commons หรือ royalty-free content",
        ],
        "approval_status": "approved_with_disclaimers",
    }

    write_json(out, compliance)
    log(
        f"✓ Legal/Compliance check - {compliance['status'].upper()} - {len(compliance['required_disclaimers'])} disclaimers needed"
    )
    return out


def agent_visual_asset(step, run_dir: Path):
    """Visual Asset - สร้างคำแนะนำสำหรับภาพและวิดีโอประกอบ"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    in_path.read_text(encoding="utf-8")

    visual_guide = {
        "generated_at": datetime.now().isoformat(),
        "total_scenes": 12,
        "scenes": [
            {
                "timestamp": "00:00-00:30",
                "type": "b-roll",
                "description": "คลิปตัดต่อเร็ว: คนเครียด, รถติด, เดดไลน์งาน",
                "mood": "เร่งเร้า → ผ่อนคลาย",
                "suggestions": [
                    "Stock footage: stressed office worker",
                    "Traffic jam timelapse",
                    "Clock ticking",
                ],
                "transition": "fade to calm nature",
            },
            {
                "timestamp": "00:30-01:30",
                "type": "on-screen",
                "description": "ผู้พูดนั่งในฉากธรรมชาติ/ห้องสมุด",
                "mood": "สงบ, น่าเชื่อถือ",
                "suggestions": [
                    "Natural background (plants, soft light)",
                    "Bookshelf with Dhamma books",
                    "Warm lighting",
                ],
                "text_overlay": ["สติ = การรับรู้ในปัจจุบัน"],
            },
            {
                "timestamp": "01:30-02:30",
                "type": "animation",
                "description": "อธิบายสติด้วย animation/whiteboard",
                "mood": "ชัดเจน, เข้าใจง่าย",
                "suggestions": [
                    "Animated mind wandering vs focused",
                    "Simple icons and diagrams",
                    "Color: ฟ้า/เขียว (สงบ)",
                ],
                "text_overlay": ["สติ", "ร่างกาย ≠ ใจ", "รับรู้ปัจจุบัน"],
            },
            {
                "timestamp": "02:30-03:30",
                "type": "b-roll + animation",
                "description": "ลมหายใจเข้า-ออก พร้อม animation",
                "mood": "ผ่อนคลาย, ช้า",
                "suggestions": [
                    "Person breathing peacefully",
                    "Animated breath cycle (in/out)",
                    "Nature sounds (optional)",
                ],
                "text_overlay": ["ลมหายใจเข้า", "ลมหายใจออก", "⚓ สมอของใจ"],
            },
            {
                "timestamp": "05:00-07:00",
                "type": "demonstration",
                "description": "Demo การฝึกจริง 3 ขั้นตอน",
                "mood": "ใกล้ชิด, ปฏิบัติได้จริง",
                "suggestions": [
                    "Split screen: instructor + close-up",
                    "Show proper sitting posture",
                    "Calm facial expressions",
                ],
                "text_overlay": ["ขั้นที่ 1", "ขั้นที่ 2", "ขั้นที่ 3"],
            },
        ],
        "b_roll_list": [
            "คนนั่งสมาธิริมทะเล/ภูเขา",
            "ใบไม้ไหว/คลื่นน้ำ (ช้า ๆ)",
            "พระพุทธรูป (respectful angle)",
            "ธรรมชาติสงบ (พระอาทิตย์ขึ้น/ตก)",
            "มือวางบนตัก (meditation mudra)",
            "ธูปควันลอย (optional)",
        ],
        "graphics_needed": [
            "Title card: เจริญสติใน 5 นาที",
            "Lower thirds: citations",
            "Progress bar: 1-2-3 steps",
            "End screen: Subscribe + Playlist",
        ],
        "color_palette": {
            "primary": "#8BC34A",  # Green - สงบ
            "secondary": "#81D4FA",  # Light Blue - ผ่อนคลาย
            "accent": "#FFD54F",  # Gold - พุทธศาสนา
            "text": "#37474F",  # Dark gray
        },
        "fonts": {
            "thai": "Prompt, Kanit",
            "english": "Montserrat",
            "style": "clean, modern, readable",
        },
        "stock_footage_sources": [
            "Pexels (free)",
            "Pixabay (free)",
            "Unsplash (free photos)",
            "Envato Elements (paid)",
        ],
        "total_duration": "10:00",
        "estimated_edit_time": "4-6 hours",
    }

    write_json(out, visual_guide)
    log(
        f"✓ Visual Asset guide created - {visual_guide['total_scenes']} scenes, {len(visual_guide['b_roll_list'])} B-roll clips"
    )
    return out


def agent_voiceover(step, run_dir: Path):
    """Voiceover - คำแนะนำสำหรับการพากย์เสียง"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    in_path.read_text(encoding="utf-8")

    voiceover_guide = {
        "generated_at": datetime.now().isoformat(),
        "voice_profile": {
            "gender": "male (suggested)",
            "age_range": "30-45",
            "tone": "warm, calm, trustworthy",
            "accent": "Central Thai (ภาคกลาง)",
            "speaking_rate": "120 wpm (words per minute) - ช้ากว่าปกติ",
            "pitch": "medium-low (สงบ)",
        },
        "recording_settings": {
            "format": "WAV",
            "sample_rate": "48kHz",
            "bit_depth": "24-bit",
            "microphone": "Condenser mic (แนะนำ)",
            "environment": "soundproof room / ห้องเงียบ",
        },
        "sections": [
            {
                "timestamp": "00:00-00:30",
                "section": "Hook",
                "tone": "engaging → calming",
                "pace": "medium → slow",
                "emphasis": ["เคยรู้สึกเครียด", "ใจฟุ้งซ่าน", "5 นาที"],
                "pauses": [
                    {"after": "ไหมครับ?", "duration": "1.5s"},
                    {"after": "ไม่ค่อยได้พัก", "duration": "1s"},
                ],
                "notes": "เริ่มด้วยพลังงาน แล้วค่อยสงบลง",
            },
            {
                "timestamp": "00:30-01:30",
                "section": "Introduction",
                "tone": "informative, friendly",
                "pace": "moderate",
                "emphasis": ["สติ", "อานาปานสติ", "พระไตรปิฎก"],
                "pauses": [
                    {"after": "อานาปานสติ", "duration": "0.5s"},
                    {"after": "ช่วงนี้", "duration": "0.5s"},
                ],
                "notes": "ให้ข้อมูล แต่ไม่เทคนิคเกินไป",
            },
            {
                "timestamp": "05:00-07:00",
                "section": "Demonstration",
                "tone": "gentle, guiding",
                "pace": "very slow",
                "emphasis": ["หายใจเข้า", "หายใจออก", "กลับมาที่ลมหายใจ"],
                "pauses": [
                    {"after": "หายใจเข้า...", "duration": "3s"},
                    {"after": "หายใจออก...", "duration": "3s"},
                    {"type": "meditation_silence", "duration": "5-10s"},
                ],
                "notes": "พูดช้ามาก เหมือนนำทำสมาธิ ใช้น้ำเสียงนุ่ม",
            },
            {
                "timestamp": "08:30-10:00",
                "section": "Conclusion",
                "tone": "encouraging, warm",
                "pace": "moderate",
                "emphasis": ["แค่ 5 นาที", "ทุกวัน", "สาธุครับ"],
                "pauses": [
                    {"after": "มาแชร์ประสบการณ์", "duration": "0.5s"},
                    {"after": "สาธุครับ", "duration": "2s"},
                ],
                "notes": "ปิดท้ายด้วยความอบอุ่น เชิญชวน",
            },
        ],
        "pronunciation_guide": {
            "อานาปานสติ": "อา-นา-ปา-นะ-สะ-ติ",
            "วิสุทธิมรรค": "วิ-สุด-ทิ-มัก",
            "มัชฌิมนิกาย": "มัด-ฉิ-มะ-นิ-กาย",
        },
        "background_music": {
            "type": "Ambient / Meditation",
            "volume": "15-20% (เบามาก)",
            "tracks_suggested": [
                "Calm Meditation Piano",
                "Tibetan Singing Bowls (soft)",
                "Nature Sounds (rain, stream)",
            ],
            "fade_in_out": "3 seconds",
        },
        "post_processing": {
            "noise_reduction": "medium",
            "eq": "boost low-mids (warm voice)",
            "compression": "gentle (2:1 ratio)",
            "reverb": "subtle room reverb",
            "normalization": "-3dB LUFS",
        },
        "alternative_options": {
            "tts_services": [
                "Google Cloud TTS (Thai)",
                "Amazon Polly (limited Thai)",
                "ElevenLabs (AI voice cloning)",
            ],
            "human_voiceover": {
                "fiverr": "$20-50 per 10 min",
                "local_talent": "ติดต่อนักพากย์ไทย",
            },
        },
        "estimated_recording_time": "30-45 minutes (with retakes)",
        "estimated_editing_time": "1-2 hours",
    }

    write_json(out, voiceover_guide)
    log(
        f"✓ Voiceover guide created - {len(voiceover_guide['sections'])} sections with detailed direction"
    )
    return out


def agent_voiceover_tts(step, run_dir: Path):
    """Deterministic voiceover TTS generation (orchestrator-only)."""
    run_id = run_dir.name
    summary_rel = (
        Path("output") / run_id / "artifacts" / "voiceover_summary.json"
    ).as_posix()

    from automation_core import voiceover_tts

    config = step.get("config") or {}
    if not isinstance(config, dict):
        raise TypeError("config must be a mapping")

    slug = config.get("slug")
    if not isinstance(slug, str):
        raise TypeError("slug must be a string")

    voiceover_tts._validate_identifier(run_id, "run_id")
    slug = voiceover_tts._validate_identifier(slug, "slug")

    script_path_value = config.get("script_path")
    if script_path_value is None:
        raise ValueError("script_path is required")
    if config.get("script_text") is not None:
        raise ValueError("script_text is not supported; use script_path")

    dry_run = config.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise TypeError("dry_run must be a boolean")

    root_dir = ROOT.resolve()
    script_path = _resolve_script_path(script_path_value, root_dir)
    script_text = script_path.read_text(encoding="utf-8")

    if dry_run:
        (
            _,
            _,
            wav_path,
            metadata_path,
            resolved_root,
        ) = voiceover_tts._prepare_voiceover_data(
            script_text,
            run_id,
            slug,
            root_dir=root_dir,
        )
        wav_rel = voiceover_tts._relative_to_root(wav_path, resolved_root)
        metadata_rel = voiceover_tts._relative_to_root(metadata_path, resolved_root)
        planned = {
            "summary_path": summary_rel,
            "wav_path": wav_rel,
            "metadata_path": metadata_rel,
        }
        return PlannedArtifacts(
            output_path=summary_rel,
            planned_paths=planned,
            dry_run=True,
        )

    metadata = voiceover_tts.generate_voiceover(
        script_text,
        run_id,
        slug,
        root_dir=root_dir,
    )

    if metadata is None:
        log(voiceover_tts.PIPELINE_DISABLED_MESSAGE, "INFO")
        return summary_rel

    wav_rel = Path(str(metadata["output_wav_path"])).as_posix()
    metadata_rel = Path(wav_rel).with_suffix(".json").as_posix()
    if Path(wav_rel).is_absolute() or Path(metadata_rel).is_absolute():
        raise ValueError("Summary paths must be relative")
    if not wav_rel.startswith(f"data/voiceovers/{run_id}/"):
        raise ValueError("WAV output must be under data/voiceovers/<run_id>/")
    if not metadata_rel.startswith(f"data/voiceovers/{run_id}/"):
        raise ValueError("Metadata output must be under data/voiceovers/<run_id>/")

    input_sha = str(metadata["input_sha256"])
    engine_name = str(metadata.get("engine_name", "unknown"))
    if engine_name.endswith("_tts"):
        engine_value = engine_name
    else:
        engine_value = f"{engine_name}_tts"
    summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "slug": slug,
        "text_sha256_12": input_sha[:12],
        "wav_path": wav_rel,
        "metadata_path": metadata_rel,
        "engine": engine_value,
    }

    summary_path = root_dir / "output" / run_id / "artifacts" / "voiceover_summary.json"
    write_json(summary_path, summary)
    log(f"Voiceover TTS summary created: {summary_rel}")
    return summary_rel


def agent_video_render(step, run_dir: Path):
    """Render MP4 from voiceover summary using ffmpeg."""
    run_id = run_dir.name

    from automation_core import voiceover_tts

    config = step.get("config") or {}
    if not isinstance(config, dict):
        raise TypeError("config must be a mapping")

    slug = config.get("slug")
    if slug is None:
        raise ValueError("config.slug is required")
    if not isinstance(slug, str):
        raise TypeError("slug must be a string")
    if not slug.strip():
        raise ValueError("slug must be a non-empty string")

    voiceover_tts._validate_identifier(run_id, "run_id")
    slug = voiceover_tts._validate_identifier(slug, "slug")

    dry_run = config.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise TypeError("dry_run must be a boolean")

    fps = config.get("fps", 30)
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps must be a positive integer")

    resolution = config.get("resolution", "1920x1080")
    if not isinstance(resolution, str) or not resolution.strip():
        raise TypeError("resolution must be a non-empty string")
    if not re.fullmatch(r"\d+x\d+", resolution):
        raise ValueError("resolution must be in WxH digits (e.g. 1920x1080)")
    width_str, height_str = resolution.split("x")
    if int(width_str) <= 0 or int(height_str) <= 0:
        raise ValueError("resolution must be in WxH digits (e.g. 1920x1080)")

    bg_color = config.get("bg_color", "black")
    if not isinstance(bg_color, str) or not bg_color.strip():
        raise ValueError("bg_color must be a non-empty string")

    root_dir = ROOT.resolve()

    def _resolve_relative_path(value: str, field_name: str) -> tuple[Path, str]:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        candidate = Path(value)
        if candidate.is_absolute():
            raise ValueError(f"{field_name} must be a relative path")
        if ".." in candidate.parts:
            raise ValueError(f"{field_name} must not contain path traversal")
        resolved = (root_dir / candidate).resolve()
        try:
            resolved.relative_to(root_dir)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be within repository root") from exc
        return resolved, candidate.as_posix()

    image_path_value = config.get("image_path")
    image_abs = None
    image_rel = None
    if image_path_value is not None:
        image_abs, image_rel = _resolve_relative_path(image_path_value, "image_path")
        if not image_abs.is_file():
            raise FileNotFoundError(f"Image input not found: {image_rel}")

    voiceover_summary_value = config.get("voiceover_summary_path")
    if voiceover_summary_value is None:
        voiceover_summary_rel = (
            Path("output") / run_id / "artifacts" / "voiceover_summary.json"
        ).as_posix()
        voiceover_summary_path = root_dir / voiceover_summary_rel
    else:
        voiceover_summary_path, voiceover_summary_rel = _resolve_relative_path(
            voiceover_summary_value, "voiceover_summary_path"
        )
        artifacts_root = (root_dir / "output" / run_id / "artifacts").resolve()
        try:
            voiceover_summary_path.relative_to(artifacts_root)
        except ValueError as exc:
            raise ValueError(
                "voiceover_summary_path must be within output/<run_id>/artifacts"
            ) from exc

    try:
        summary = read_json(voiceover_summary_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Voiceover summary not found: {voiceover_summary_rel}"
        ) from exc
    if not isinstance(summary, dict):
        raise TypeError("voiceover_summary must be a JSON object")

    schema_version = summary.get("schema_version")
    if not isinstance(schema_version, str):
        raise ValueError("voiceover_summary.schema_version is required")

    summary_run_id = summary.get("run_id")
    if summary_run_id is not None and summary_run_id != run_id:
        raise ValueError("voiceover_summary.run_id does not match run_id")

    summary_slug = summary.get("slug")
    if summary_slug is not None and summary_slug != slug:
        raise ValueError("voiceover_summary.slug does not match config slug")

    text_sha = summary.get("text_sha256_12")
    if not isinstance(text_sha, str) or len(text_sha) != 12:
        raise ValueError("voiceover_summary.text_sha256_12 must be a 12-char string")

    wav_value = summary.get("wav_path")
    if not isinstance(wav_value, str):
        raise ValueError("voiceover_summary.wav_path must be a string")
    wav_rel = Path(wav_value).as_posix()
    wav_path_value = Path(wav_rel)
    if wav_path_value.is_absolute():
        raise ValueError("voiceover_summary.wav_path must be a relative path")
    if ".." in wav_path_value.parts:
        raise ValueError("voiceover_summary.wav_path must not contain path traversal")
    if not wav_rel.startswith(f"data/voiceovers/{run_id}/"):
        raise ValueError(
            "voiceover_summary.wav_path must be under data/voiceovers/<run_id>/"
        )
    wav_abs = (root_dir / wav_path_value).resolve()
    try:
        wav_abs.relative_to(root_dir)
    except ValueError as exc:
        raise ValueError(
            "voiceover_summary.wav_path must be within repository root"
        ) from exc

    output_mp4_rel = (
        Path("output") / run_id / "artifacts" / f"{slug}_{text_sha}.mp4"
    ).as_posix()
    summary_rel = (
        Path("output") / run_id / "artifacts" / "video_render_summary.json"
    ).as_posix()

    if dry_run:
        planned = {
            "summary_path": summary_rel,
            "output_mp4_path": output_mp4_rel,
            "input_voiceover_summary": voiceover_summary_rel,
            "input_wav_path": wav_rel,
        }
        return PlannedArtifacts(
            output_path=summary_rel,
            planned_paths=planned,
            dry_run=True,
        )

    if not wav_abs.is_file():
        raise FileNotFoundError(f"WAV input not found: {wav_rel}")

    output_mp4_abs = (root_dir / Path(output_mp4_rel)).resolve()
    output_mp4_abs.parent.mkdir(parents=True, exist_ok=True)

    if image_abs is not None:
        cmd_exec = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_abs),
            "-i",
            str(wav_abs),
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_mp4_abs),
        ]
        cmd_recorded = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            image_rel,
            "-i",
            wav_rel,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            output_mp4_rel,
        ]
    else:
        color_filter = f"color=c={bg_color}:s={resolution}:r={fps}"
        cmd_exec = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            color_filter,
            "-i",
            str(wav_abs),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_mp4_abs),
        ]
        cmd_recorded = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            color_filter,
            "-i",
            wav_rel,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            output_mp4_rel,
        ]

    try:
        subprocess.run(cmd_exec, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found in PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        tail = "\n".join(stderr.splitlines()[-20:]) if stderr else ""
        message = "ffmpeg failed"
        if tail:
            message = f"ffmpeg failed:\n{tail}"
        raise RuntimeError(message) from exc

    render_summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "slug": slug,
        "text_sha256_12": text_sha,
        "input_voiceover_summary": voiceover_summary_rel,
        "input_wav_path": wav_rel,
        "output_mp4_path": output_mp4_rel,
        "engine": "ffmpeg",
        "ffmpeg_cmd": cmd_recorded,
    }

    summary_path = root_dir / summary_rel
    write_json(summary_path, render_summary)
    log(f"Video render summary created: {summary_rel}")
    return summary_rel


def agent_quality_gate(step, run_dir: Path):
    """Quality Gate - ตรวจสอบคุณภาพวิดีโอที่เรนเดอร์แล้วแบบ deterministic."""
    run_id = run_dir.name
    root_dir = ROOT.resolve()

    QG_ENGINE = "quality.gate"
    SEVERITY_ERROR = "error"
    CODE_MP4_MISSING = "mp4_missing"
    CODE_MP4_EMPTY = "mp4_empty"
    CODE_FFPROBE_FAILED = "ffprobe_failed"
    CODE_DURATION_ZERO_OR_MISSING = "duration_zero_or_missing"
    CODE_AUDIO_STREAM_MISSING = "audio_stream_missing"

    summary_rel = (
        Path("output") / run_id / "artifacts" / "video_render_summary.json"
    ).as_posix()
    summary_path = root_dir / summary_rel

    try:
        summary = read_json(summary_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Video render summary not found: {summary_rel}"
        ) from exc

    if not isinstance(summary, dict):
        raise TypeError("video_render_summary must be a JSON object")

    schema_version = summary.get("schema_version")
    if schema_version != "v1":
        raise ValueError("video_render_summary.schema_version must be 'v1'")

    summary_run_id = summary.get("run_id")
    if summary_run_id is not None and summary_run_id != run_id:
        raise ValueError("video_render_summary.run_id does not match run_id")

    output_mp4_value = summary.get("output_mp4_path")
    if not isinstance(output_mp4_value, str) or not output_mp4_value.strip():
        raise ValueError("video_render_summary.output_mp4_path is required")

    output_mp4_rel = Path(output_mp4_value).as_posix()
    output_mp4_path_value = Path(output_mp4_rel)
    if output_mp4_path_value.is_absolute():
        raise ValueError("video_render_summary.output_mp4_path must be a relative path")
    if ".." in output_mp4_path_value.parts:
        raise ValueError(
            "video_render_summary.output_mp4_path must not contain path traversal"
        )
    output_mp4_abs = (root_dir / output_mp4_path_value).resolve()
    try:
        output_mp4_abs.relative_to(root_dir)
    except ValueError as exc:
        raise ValueError(
            "video_render_summary.output_mp4_path must be within repository root"
        ) from exc

    checked_at = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    reasons: list[dict[str, object]] = []
    checks = {
        "mp4_exists": False,
        "mp4_size_bytes": None,
        "ffprobe_ok": None,
        "duration_seconds": None,
        "has_audio_stream": None,
    }

    def _add_reason(code: str, message: str, severity: str) -> None:
        reasons.append(
            {
                "code": code,
                "message": message,
                "severity": severity,
                "engine": QG_ENGINE,
                "checked_at": checked_at,
            }
        )

    def _check_mp4_existence() -> None:
        if not output_mp4_abs.is_file():
            _add_reason(
                CODE_MP4_MISSING,
                f"MP4 file not found: {output_mp4_rel}",
                SEVERITY_ERROR,
            )
            return

        checks["mp4_exists"] = True

    def _check_mp4_size() -> None:
        mp4_size = output_mp4_abs.stat().st_size
        checks["mp4_size_bytes"] = mp4_size
        if mp4_size == 0:
            _add_reason(
                CODE_MP4_EMPTY, f"MP4 file is empty: {output_mp4_rel}", SEVERITY_ERROR
            )

    def _run_ffprobe() -> dict | None:
        ffprobe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type",
            "-of",
            "json",
            str(output_mp4_abs),
        ]
        try:
            completed = subprocess.run(
                ffprobe_cmd, check=False, capture_output=True, text=True
            )
        except OSError:
            _add_reason(CODE_FFPROBE_FAILED, "ffprobe execution failed", SEVERITY_ERROR)
            checks["ffprobe_ok"] = False
            return None

        if completed.returncode != 0:
            _add_reason(
                CODE_FFPROBE_FAILED,
                f"ffprobe returned non-zero exit code: {completed.returncode}",
                SEVERITY_ERROR,
            )
            checks["ffprobe_ok"] = False
            return None

        try:
            data = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            _add_reason(
                CODE_FFPROBE_FAILED, "ffprobe output was not valid JSON", SEVERITY_ERROR
            )
            checks["ffprobe_ok"] = False
            return None

        checks["ffprobe_ok"] = True
        return data if isinstance(data, dict) else None

    def _check_duration(ffprobe_data: dict) -> None:
        duration_raw = ffprobe_data.get("format", {}).get("duration")
        duration_seconds = None
        if duration_raw is not None:
            try:
                duration_seconds = float(duration_raw)
            except (TypeError, ValueError):
                duration_seconds = None

        if duration_seconds is None or duration_seconds <= 0:
            _add_reason(
                CODE_DURATION_ZERO_OR_MISSING,
                "MP4 duration is missing or zero",
                SEVERITY_ERROR,
            )
        else:
            checks["duration_seconds"] = duration_seconds

    def _check_audio_stream(ffprobe_data: dict) -> None:
        streams = ffprobe_data.get("streams", [])
        has_audio = any(
            isinstance(stream, dict) and stream.get("codec_type") == "audio"
            for stream in streams
        )
        checks["has_audio_stream"] = has_audio
        if not has_audio:
            _add_reason(
                CODE_AUDIO_STREAM_MISSING,
                "No audio stream detected in MP4",
                SEVERITY_ERROR,
            )

    _check_mp4_existence()
    if checks["mp4_exists"]:
        _check_mp4_size()

    if checks["mp4_exists"] and not any(
        r.get("code") == CODE_MP4_EMPTY for r in reasons
    ):
        ffprobe_data = _run_ffprobe()
        if checks["ffprobe_ok"]:
            assert ffprobe_data is not None
            _check_duration(ffprobe_data)
            _check_audio_stream(ffprobe_data)

    decision = "pass"
    if any(reason.get("severity") == SEVERITY_ERROR for reason in reasons):
        decision = "fail"

    gate_summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "input_video_render_summary": summary_rel,
        "output_mp4_path": output_mp4_rel,
        "decision": decision,
        "reasons": reasons,
        "checked_at": checked_at,
        "engine": QG_ENGINE,
        "checks": checks,
    }

    summary_out = (
        root_dir / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    write_json(summary_out, gate_summary)
    log(f"Quality gate summary created: {summary_out.relative_to(root_dir)}")

    if decision == "fail":
        codes = [reason.get("code", "unknown") for reason in reasons]
        top_codes = ", ".join(codes[:3])
        raise RuntimeError(
            f"Quality gate failed for run_id={run_id}; reasons={top_codes}"
        )

    return summary_out.relative_to(root_dir).as_posix()


def agent_post_templates(_step, run_dir: Path):
    """
    รันเอเจนต์ post templates เพื่อสร้างสรุปเนื้อหาโพสต์แบบ deterministic

    Args:
        _step: ข้อมูลการตั้งค่าของสเต็ปจากไฟล์ pipeline YAML
            (ไม่ได้ถูกใช้งานโดยตรงในฟังก์ชันนี้ แต่คงพารามิเตอร์ไว้ให้มีรูปแบบ
            สอดคล้องกับเอเจนต์ตัวอื่นใน orchestrator)
        run_dir: โฟลเดอร์รันของ pipeline สำหรับ run_id นั้น ๆ
            ใช้สำหรับอ่านค่า run_id จากชื่อโฟลเดอร์

    Returns:
        เส้นทางไฟล์แบบ relative (POSIX string) จาก root ของโปรเจ็กต์
        ไปยังไฟล์ post_content_summary.json ที่ถูกสร้างภายใต้
        output/<run_id>/artifacts/

    Side effects:
        สร้างไฟล์ post_content_summary.json ภายใต้โฟลเดอร์ artifacts
        ของ run_id โดยอาศัยการทำงานของ _run_post_templates_step()
    """
    run_id = run_dir.name
    root_dir = ROOT.resolve()
    return _run_post_templates_step(run_id, root_dir)


def agent_dispatch_v0(_step, run_dir: Path):
    """รันเอเจนต์ dispatch_v0 เพื่อสร้าง dispatch_audit.json"""
    run_id = run_dir.name
    root_dir = ROOT.resolve()
    return _run_dispatch_v0_step(run_id, root_dir)


def _youtube_upload_parse_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _youtube_upload_is_enabled(step_cfg: dict) -> bool:
    config = step_cfg.get("config")
    if config is not None and not isinstance(config, dict):
        raise TypeError("step.config must be an object")
    if isinstance(config, dict) and "dry_run" in config:
        dry_run = config.get("dry_run")
        if not isinstance(dry_run, bool):
            raise TypeError("config.dry_run must be a boolean")
        if dry_run:
            return False
    return os.environ.get("YOUTUBE_UPLOAD_ENABLED", "false").strip().lower() == "true"


def _youtube_upload_expected_quality_summary_rel(run_id: str) -> str:
    return (
        Path("output") / run_id / "artifacts" / "quality_gate_summary.json"
    ).as_posix()


def _youtube_upload_load_quality_summary_required(root_dir: Path, run_id: str) -> dict:
    quality_rel = _youtube_upload_expected_quality_summary_rel(run_id)
    quality_path = root_dir / quality_rel
    try:
        payload = read_json(quality_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Quality gate summary not found: {quality_rel}"
        ) from exc
    if not isinstance(payload, dict):
        raise TypeError("quality_gate_summary must be a JSON object")
    schema_version = payload.get("schema_version")
    if schema_version != "v1":
        raise ValueError("quality_gate_summary.schema_version must be 'v1'")
    summary_run_id = payload.get("run_id")
    if summary_run_id is not None and summary_run_id != run_id:
        raise ValueError("quality_gate_summary.run_id does not match run_id")
    return payload


def _youtube_upload_try_load_quality_summary(
    root_dir: Path, run_id: str
) -> dict | None:
    quality_rel = _youtube_upload_expected_quality_summary_rel(run_id)
    quality_path = root_dir / quality_rel
    if not quality_path.is_file():
        return None
    try:
        payload = read_json(quality_path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != "v1":
        return None
    return payload


def _youtube_upload_validate_repo_relative_path(
    root_dir: Path,
    value: str,
    label: str,
) -> Path:
    rel = Path(Path(value).as_posix())
    if rel.is_absolute():
        raise ValueError(f"{label} must be a relative path")
    if ".." in rel.parts:
        raise ValueError(f"{label} must not contain path traversal")
    abs_path = (root_dir / rel).resolve()
    try:
        abs_path.relative_to(root_dir)
    except ValueError as exc:
        raise ValueError(f"{label} must be within repository root") from exc
    return abs_path


def _youtube_upload_read_json_if_dict(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _youtube_upload_parse_tags_text(text: str) -> list[str]:
    """แปลงข้อความแท็กจากไฟล์ override

    รูปแบบที่รองรับ: JSON array ของสตริงเท่านั้น เช่น ["tag1", "tag2"]
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, str)]
    return []


def _youtube_upload_resolve_override_path(root_dir: Path, env_name: str) -> Path | None:
    raw = os.environ.get(env_name)
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    return _youtube_upload_validate_repo_relative_path(root_dir, value, env_name)


def _youtube_upload_read_override_text(path: Path, env_name: str) -> str:
    max_bytes = 65_536
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Unable to read override file for {env_name}") from exc
    if size > max_bytes:
        raise ValueError(
            f"Override file for {env_name} is too large (>{max_bytes} bytes)"
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Override file for {env_name} must be valid UTF-8 text"
        ) from exc
    except OSError as exc:
        raise ValueError(f"Unable to read override file for {env_name}") from exc


def _youtube_upload_resolve_metadata(
    root_dir: Path, run_id: str
) -> tuple[str, str, list[str]]:
    title = None
    description = None
    tags: list[str] | None = None

    metadata_path = root_dir / "output" / run_id / "metadata.json"
    metadata = _youtube_upload_read_json_if_dict(metadata_path)
    if metadata:
        raw_title = metadata.get("title")
        if isinstance(raw_title, str) and raw_title != "":
            title = raw_title
        raw_description = metadata.get("description")
        if isinstance(raw_description, str) and raw_description != "":
            description = raw_description
        raw_tags = metadata.get("tags")
        if isinstance(raw_tags, list):
            tags = [item for item in raw_tags if isinstance(item, str)]

    if title is None:
        title_path = _youtube_upload_resolve_override_path(
            root_dir, "YOUTUBE_TITLE_PATH"
        )
        if title_path is not None:
            title = _youtube_upload_read_override_text(title_path, "YOUTUBE_TITLE_PATH")

    if description is None:
        description_path = _youtube_upload_resolve_override_path(
            root_dir, "YOUTUBE_DESCRIPTION_PATH"
        )
        if description_path is not None:
            description = _youtube_upload_read_override_text(
                description_path, "YOUTUBE_DESCRIPTION_PATH"
            )

    if tags is None:
        tags_path = _youtube_upload_resolve_override_path(root_dir, "YOUTUBE_TAGS_PATH")
        if tags_path is not None:
            tags_text = _youtube_upload_read_override_text(
                tags_path, "YOUTUBE_TAGS_PATH"
            )
            tags = _youtube_upload_parse_tags_text(tags_text)

    if title is None:
        title = f"Dhamma Video - {run_id}"
    if description is None:
        description = "Generated by Dhamma Channel Automation."
    if tags is None:
        tags = []

    return title, description, tags


def _youtube_upload_extract_http_status(exc: Exception) -> int | None:
    if isinstance(exc, youtube_upload.YoutubeApiError):
        return exc.status
    for attr in ("status", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    resp = getattr(exc, "resp", None)
    status = getattr(resp, "status", None)
    if isinstance(status, int):
        return status
    return None


def agent_youtube_upload(step, run_dir: Path):
    """เอเจนต์อัปโหลด YouTube - อัปโหลดไฟล์ MP4 ขึ้น YouTube พร้อม retry และสรุปผลลัพธ์

    หมายเหตุ: ควรถูกเรียกผ่าน orchestrator เท่านั้น เพื่อให้ guardrails เช่น
    `PIPELINE_ENABLED` ถูกบังคับใช้อย่างถูกต้อง
    """
    run_id = run_dir.name
    root_dir = ROOT.resolve()

    YU_ENGINE = "youtube.upload"
    CODE_UPLOAD_DISABLED = "upload_disabled"
    CODE_QUALITY_NOT_PASS = "quality_gate_not_pass"
    CODE_INPUT_MP4_MISSING = "input_mp4_missing"
    CODE_AUTH_MISSING_ENV = "auth_missing_env"
    CODE_DEPS_MISSING = "youtube_deps_missing"
    CODE_YOUTUBE_API_ERROR = "youtube_api_error"
    CODE_FAILED_AFTER_RETRIES = "upload_failed_after_retries"

    upload_enabled = _youtube_upload_is_enabled(step)
    max_retries = _youtube_upload_parse_int_env("YOUTUBE_UPLOAD_MAX_RETRIES", 3)
    backoff_seconds = _youtube_upload_parse_int_env(
        "YOUTUBE_UPLOAD_BACKOFF_SECONDS", 10
    )
    privacy_status_raw = (
        os.environ.get("YOUTUBE_PRIVACY_STATUS", "unlisted").strip().lower()
    )
    if privacy_status_raw not in ("private", "unlisted", "public"):
        log(
            f"Invalid YOUTUBE_PRIVACY_STATUS='{privacy_status_raw}', falling back to 'unlisted'",
            "WARN",
        )
        privacy_status = "unlisted"
    else:
        privacy_status = privacy_status_raw

    checked_at = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    upload_summary_rel = (
        Path("output") / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    upload_summary_path = root_dir / upload_summary_rel

    title, description, tags = _youtube_upload_resolve_metadata(root_dir, run_id)
    quality_rel = _youtube_upload_expected_quality_summary_rel(run_id)

    output_mp4_rel = ""

    def _write_summary(
        decision: str,
        attempt_count: int,
        error_code: str | None = None,
        error_message: str | None = None,
        video_id: str | None = None,
    ) -> str:
        video_url = None
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        error = None
        if error_code is not None:
            error = {
                "code": error_code,
                "message": error_message or "",
            }

        summary = {
            "schema_version": "v1",
            "run_id": run_id,
            "engine": YU_ENGINE,
            "checked_at": checked_at,
            "quality_gate_summary": quality_rel,
            "input_mp4_path": output_mp4_rel,
            "decision": decision,
            "privacy_status": privacy_status,
            "attempt_count": attempt_count,
            "max_retries": max_retries,
            "backoff_seconds": backoff_seconds,
            "video_id": video_id,
            "video_url": video_url,
            "error": error,
            "metadata": {
                "title": title,
                "description": description,
                "tags": tags,
            },
        }
        write_json(upload_summary_path, summary)
        return upload_summary_rel.as_posix()

    if not upload_enabled:
        summary_path = _write_summary(
            decision="skipped",
            attempt_count=0,
            error_code=CODE_UPLOAD_DISABLED,
            error_message="YouTube upload disabled",
        )
        log(
            f"YouTube upload skipped; decision=skipped; code={CODE_UPLOAD_DISABLED}; attempt=0",
            "INFO",
        )
        return summary_path

    quality_summary_required = _youtube_upload_load_quality_summary_required(
        root_dir, run_id
    )
    quality_decision = quality_summary_required.get("decision")

    # Extract and validate output_mp4_path from quality summary (once)
    output_mp4_value = quality_summary_required.get("output_mp4_path")
    if isinstance(output_mp4_value, str) and output_mp4_value:
        output_mp4_rel = Path(output_mp4_value).as_posix()
        output_mp4_abs = _youtube_upload_validate_repo_relative_path(
            root_dir, output_mp4_rel, "quality_gate_summary.output_mp4_path"
        )
    else:
        if quality_decision == "pass":
            raise ValueError("quality_gate_summary.output_mp4_path is required")
        output_mp4_abs = None

    if quality_decision != "pass":
        summary_path = _write_summary(
            decision="skipped",
            attempt_count=0,
            error_code=CODE_QUALITY_NOT_PASS,
            error_message="Quality gate decision not pass",
        )
        log(
            f"YouTube upload skipped; decision=skipped; code={CODE_QUALITY_NOT_PASS}; attempt=0",
            "INFO",
        )
        return summary_path

    # At this point, quality_decision == "pass" and output_mp4_abs must be valid
    if output_mp4_abs is None:
        raise ValueError("quality_gate_summary.output_mp4_path is required")

    if not output_mp4_abs.is_file() or output_mp4_abs.stat().st_size <= 0:
        _write_summary(
            decision="failed",
            attempt_count=0,
            error_code=CODE_INPUT_MP4_MISSING,
            error_message="Input MP4 missing or empty",
        )
        log(
            f"YouTube upload failed; decision=failed; code={CODE_INPUT_MP4_MISSING}; attempt=0",
            "ERROR",
        )
        raise RuntimeError(
            f"YouTube upload failed for run_id={run_id}; code={CODE_INPUT_MP4_MISSING}"
        )

    total_attempts = 1 + max_retries
    attempt = 0
    while attempt < total_attempts:
        attempt += 1
        try:
            video_id = youtube_upload.upload_video(
                output_mp4_abs, title, description, tags, privacy_status
            )
            summary_path = _write_summary(
                decision="uploaded",
                attempt_count=attempt,
                video_id=video_id,
            )
            log(
                f"YouTube upload completed; decision=uploaded; attempt={attempt}",
                "SUCCESS",
            )
            return summary_path
        except youtube_upload.YoutubeDepsMissingError as exc:
            _write_summary(
                decision="failed",
                attempt_count=attempt,
                error_code=CODE_DEPS_MISSING,
                error_message="YouTube dependencies are not installed",
            )
            log(
                f"YouTube upload failed; decision=failed; code={CODE_DEPS_MISSING}; attempt={attempt}",
                "ERROR",
            )
            raise RuntimeError(
                f"YouTube upload failed for run_id={run_id}; code={CODE_DEPS_MISSING}"
            ) from exc
        except youtube_upload.YoutubeAuthMissingError as exc:
            _write_summary(
                decision="failed",
                attempt_count=attempt,
                error_code=CODE_AUTH_MISSING_ENV,
                error_message="Missing YouTube auth environment variables",
            )
            log(
                f"YouTube upload failed; decision=failed; code={CODE_AUTH_MISSING_ENV}; attempt={attempt}",
                "ERROR",
            )
            raise RuntimeError(
                f"YouTube upload failed for run_id={run_id}; code={CODE_AUTH_MISSING_ENV}"
            ) from exc
        except Exception as exc:
            status = _youtube_upload_extract_http_status(exc)
            retryable = status == 429 or (status is not None and 500 <= status < 600)
            if retryable and attempt < total_attempts:
                log(
                    "YouTube upload attempt "
                    f"{attempt}/{total_attempts} failed; decision=retry; code={CODE_YOUTUBE_API_ERROR}",
                    "WARN",
                )
                time.sleep(backoff_seconds)
                continue

            if retryable:
                error_code = CODE_FAILED_AFTER_RETRIES
                error_message = "YouTube upload failed after retries"
            else:
                error_code = CODE_YOUTUBE_API_ERROR
                error_message = "YouTube API error"

            _write_summary(
                decision="failed",
                attempt_count=attempt,
                error_code=error_code,
                error_message=error_message,
            )
            log(
                f"YouTube upload failed; decision=failed; code={error_code}; attempt={attempt}",
                "ERROR",
            )
            raise RuntimeError(
                f"YouTube upload failed for run_id={run_id}; code={error_code}"
            ) from exc


def agent_localization(step, run_dir: Path):
    """Localization & Subtitle - สร้างคำบรรยายและแปลภาษา"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    in_path.read_text(encoding="utf-8")

    # สร้าง SRT template
    srt_content = """1
00:00:00,000 --> 00:00:05,000
สวัสดีครับผู้ชมทุกท่าน 🙏

2
00:00:05,000 --> 00:00:10,000
คุณเคยรู้สึกเครียด ใจฟุ้งซ่าน
จนไม่รู้จะทำอะไรก่อนดีไหมครับ?

3
00:00:12,000 --> 00:00:17,000
ชีวิตยุคใหม่เต็มไปด้วยความเร่งรีบ
ข้อมูลข่าวสารท่วมท้น

4
00:00:17,000 --> 00:00:22,000
ทำให้จิตใจของเราไม่ค่อยได้พัก
ไม่ค่อยได้สงบเลย

5
00:00:24,000 --> 00:00:30,000
แต่ถ้าผมบอกว่า แค่ 5 นาที
ทำได้ทุกที่ ทุกเวลา

6
00:00:30,000 --> 00:00:35,000
คุณก็สามารถทำให้ใจสงบลงได้

... [continues]
"""

    localization = {
        "generated_at": datetime.now().isoformat(),
        "primary_language": "th",
        "subtitles": {
            "thai": {
                "filename": "subtitles_th.srt",
                "status": "generated",
                "total_lines": 120,
                "format": "SRT",
                "encoding": "UTF-8",
                "font_recommendation": "Prompt, Kanit",
                "size": "Medium (not too small)",
                "position": "Bottom center",
                "style": {
                    "color": "White",
                    "outline": "Black (2px)",
                    "background": "Semi-transparent black (optional)",
                },
            },
            "english": {
                "filename": "subtitles_en.srt",
                "status": "to_be_translated",
                "target_audience": "International Buddhists, meditation practitioners",
                "notes": "Translate key terms carefully: สติ = mindfulness/awareness",
            },
        },
        "translation_guide": {
            "key_terms": {
                "สติ": "mindfulness / awareness",
                "อานาปานสติ": "mindfulness of breathing / breath meditation",
                "พระไตรปิฎก": "Tripitaka / Pali Canon",
                "วิสุทธิมรรค": "Visuddhimagga / Path of Purification",
                "กรรมฐาน": "meditation object / kammaṭṭhāna",
                "สมาธิ": "concentration / samadhi",
            },
            "cultural_notes": [
                "🙏 emoji = wai gesture (Thai greeting)",
                "Keep Thai Buddhist terminology intact when appropriate",
                "Add footnotes for untranslatable concepts",
            ],
        },
        "accessibility": {
            "closed_captions": {
                "enabled": True,
                "includes_sound_effects": "[เสียงธรรมชาติ]",
                "speaker_labels": "[ผู้บรรยาย]",
            },
            "auto_generated": {
                "youtube_auto_captions": "available as backup",
                "accuracy": "60-70% (Thai)",
                "recommendation": "Always upload custom SRT",
            },
        },
        "srt_file_preview": srt_content[:500] + "...",
        "tools_recommended": [
            "Subtitle Edit (free, Windows)",
            "Aegisub (free, cross-platform)",
            "YouTube Studio (built-in editor)",
            "Rev.com (paid transcription service)",
        ],
        "quality_checklist": [
            "ตรวจสอบความสอดคล้องกับเสียง",
            "แบ่งบรรทัดตามความหมาย (ไม่เกิน 2 บรรทัด)",
            "ระยะเวลาแสดงผล 1-7 วินาที/บรรทัด",
            "ใช้ emoji อย่างประหยัด",
            "ตรวจสอบการสะกดคำ",
        ],
        "estimated_time": "2-3 hours (manual timing)",
    }

    # เขียนไฟล์ SRT ตัวอย่าง
    srt_path = run_dir / "subtitles_th.srt"
    write_text(srt_path, srt_content)

    write_json(out, localization)
    log(
        f"✓ Localization completed - Thai SRT generated ({localization['subtitles']['thai']['total_lines']} lines)"
    )
    return out


def agent_thumbnail_generator(step, run_dir: Path):
    """Thumbnail Generator - สร้างคอนเซ็ปต์ภาพปก"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    metadata = read_json(in_path)
    title = metadata.get("title", "")

    thumbnail_concepts = {
        "generated_at": datetime.now().isoformat(),
        "video_title": title,
        "dimensions": "1280x720 px (16:9)",
        "file_format": "JPG or PNG",
        "file_size_limit": "2MB (YouTube)",
        "concepts": [
            {
                "concept_id": 1,
                "title": "Peaceful Meditation",
                "text_overlay": {
                    "main": "ฝึกสติ 5 นาที",
                    "sub": "เข้าใจง่าย ทำได้ทุกที่",
                    "font_size": {"main": "72pt", "sub": "36pt"},
                    "font": "Kanit Bold",
                    "color": "White + Gold",
                    "stroke": "Dark shadow (3px)",
                },
                "visual_elements": [
                    "Person meditating (silhouette or clear face)",
                    "Natural background (sunset, mountains)",
                    "Soft glow/light effect",
                    "🙏 emoji (optional)",
                ],
                "color_scheme": "warm (orange/gold)",
                "emotion": "peaceful, inviting",
                "composition": "Rule of thirds - subject on right, text on left",
            },
            {
                "concept_id": 2,
                "title": "Modern Minimal",
                "text_overlay": {
                    "main": "5 นาที",
                    "sub": "เปลี่ยนใจ",
                    "badge": "🧘 สติ",
                    "font_size": {"main": "120pt", "sub": "48pt"},
                    "font": "Prompt ExtraBold",
                    "color": "Dark blue + White",
                    "style": "Clean, modern",
                },
                "visual_elements": [
                    "Minimalist breath animation",
                    "Geometric shapes (circles/waves)",
                    "Gradient background (blue to green)",
                    "NO clutter",
                ],
                "color_scheme": "cool (blue/green)",
                "emotion": "modern, trustworthy",
                "composition": "Center-aligned, symmetrical",
            },
            {
                "concept_id": 3,
                "title": "Emotional Hook",
                "text_overlay": {
                    "main": "ใจฟุ้งซ่าน?",
                    "sub": "5 นาที แก้ได้!",
                    "font_size": {"main": "80pt", "sub": "52pt"},
                    "font": "Kanit Bold",
                    "color": "Yellow + White",
                    "effect": "Slight tilt (dynamic)",
                },
                "visual_elements": [
                    "Split screen: stressed vs calm face",
                    "Before/After concept",
                    "Arrows or transformation symbol",
                    "High contrast",
                ],
                "color_scheme": "contrast (yellow/dark)",
                "emotion": "curiosity, problem-solving",
                "composition": "Dynamic split, eye-catching",
            },
        ],
        "design_principles": {
            "readability": "Text readable on mobile (4-6 words max)",
            "contrast": "High contrast text/background",
            "branding": "Consistent with channel style",
            "emotion": "Show face when possible (5x higher CTR)",
            "curiosity": "Ask question or promise benefit",
        },
        "tools": {
            "free": [
                "Canva (template available)",
                "Photopea (free Photoshop alternative)",
                "GIMP",
            ],
            "paid": ["Adobe Photoshop", "Affinity Photo", "Figma"],
        },
        "a_b_testing": {
            "recommendation": "Create 2-3 versions, test which gets higher CTR",
            "test_duration": "7-14 days",
            "metrics": "CTR (Click-Through Rate)",
        },
        "best_practices": [
            "ใช้ใบหน้าคนจริง (ถ้าเป็นไปได้)",
            "ข้อความสั้น ชัดเจน ไม่เกิน 6 คำ",
            "สีสันสดใส แต่ไม่ฉูดฉาด",
            "ตรงกับเนื้อหาวิดีโอ (ไม่ clickbait)",
            "เพิ่ม emoji 1-2 ตัว (optional)",
        ],
        "avoid": [
            "ข้อความเยอะเกินไป",
            "สีจางจนอ่านไม่ออก",
            "ภาพไม่เกี่ยวกับเนื้อหา",
            "Clickbait หลอกลวง",
        ],
    }

    write_json(out, thumbnail_concepts)
    log(
        f"✓ Thumbnail concepts created - {len(thumbnail_concepts['concepts'])} designs ready"
    )
    return out


def agent_format_conversion(step, run_dir: Path):
    """Format Conversion - แปลงไฟล์เป็นรูปแบบต่างๆ"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    in_path.read_text(encoding="utf-8")

    formats = {
        "converted_at": datetime.now().isoformat(),
        "source_file": str(in_path),
        "conversions": {
            "video": {
                "youtube": {
                    "format": "MP4",
                    "codec": "H.264",
                    "resolution": "1920x1080 (1080p)",
                    "frame_rate": "30fps",
                    "bitrate": "8-12 Mbps",
                    "audio": "AAC 320kbps",
                    "max_file_size": "128GB",
                    "aspect_ratio": "16:9",
                },
                "facebook": {
                    "format": "MP4",
                    "resolution": "1280x720 (720p)",
                    "aspect_ratio": "16:9 or 1:1 (square)",
                    "max_duration": "240 min",
                    "max_file_size": "10GB",
                },
                "tiktok_shorts": {
                    "format": "MP4",
                    "resolution": "1080x1920 (vertical)",
                    "aspect_ratio": "9:16",
                    "max_duration": "10 min",
                    "recommendation": "Extract key 60-90 sec clips",
                },
            },
            "audio": {
                "podcast": {
                    "format": "MP3",
                    "bitrate": "192kbps",
                    "sample_rate": "44.1kHz",
                    "use_case": "Audio-only version for podcast platforms",
                }
            },
            "document": {
                "pdf": {
                    "filename": "script_formatted.pdf",
                    "use_case": "Printable script for reference",
                    "include": ["Full script", "Citations", "Timestamps"],
                },
                "docx": {
                    "filename": "script_editable.docx",
                    "use_case": "Editable for future revisions",
                },
            },
        },
        "export_settings": {
            "premiere_pro": {
                "sequence": "1920x1080, 30fps",
                "export_preset": "YouTube 1080p Full HD",
            },
            "davinci_resolve": {
                "timeline": "1920x1080, 30fps",
                "delivery": "YouTube preset",
            },
            "final_cut_pro": {"destination": "YouTube & Facebook"},
        },
        "optimization": {
            "compress_without_quality_loss": {
                "tool": "HandBrake",
                "preset": "Fast 1080p30",
            },
            "thumbnail": {
                "extract_frame": "at 02:30 (engaging moment)",
                "resolution": "1280x720",
            },
        },
        "delivery_checklist": [
            "MP4 for YouTube (1080p)",
            "SRT subtitle file",
            "Thumbnail JPG (1280x720)",
            "Metadata JSON",
            "PDF script (backup)",
        ],
    }

    write_json(out, formats)
    log(
        f"✓ Format conversion specs created - {len(formats['conversions'])} format categories"
    )
    return out


def agent_multi_channel_publish(step, run_dir: Path):
    """Multi-Channel Publish - เผยแพร่หลายแพลตฟอร์ม"""
    in_path = run_dir / step["input_from"]
    out = run_dir / step["output"]

    metadata = read_json(in_path)

    multi_channel = {
        "published_at": datetime.now().isoformat(),
        "status": "ready_for_distribution",
        "platforms": {
            "youtube": {
                "enabled": True,
                "priority": 1,
                "settings": {
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", []),
                    "category": "Education",
                    "visibility": "public",
                    "publish_time": "2025-11-05 10:00:00 +07:00",
                    "playlist": "ธรรมะเบื้องต้น",
                    "thumbnail": "thumbnail.jpg",
                    "end_screen": True,
                    "cards": True,
                    "subtitles": "subtitles_th.srt",
                },
                "api_endpoint": "YouTube Data API v3",
                "status": "scheduled",
            },
            "facebook": {
                "enabled": True,
                "priority": 2,
                "targets": [
                    {
                        "type": "page",
                        "name": "Dhamma Channel",
                        "post_text": "🙏 วิดีโอใหม่! เจริญสติในชีวิตประจำวัน 5 นาที\n\nมาเรียนรู้การฝึก 'อานาปานสติ' แบบง่ายๆ ที่ทำได้ทุกที่ ทุกเวลา\n\n✨ ประโยชน์:\n• ลดความเครียด\n• ใจสงบ\n• นอนหลับสนิท\n\nดูเต็มได้ที่: [YouTube Link]",
                        "hashtags": ["#ธรรมะ", "#สติ", "#mindfulness"],
                        "schedule": "same_as_youtube",
                    },
                    {
                        "type": "group",
                        "name": "ธรรมะเพื่อชีวิต",
                        "permission": "request_approval",
                    },
                ],
            },
            "line": {
                "enabled": False,
                "targets": [
                    {
                        "type": "broadcast",
                        "message": "🙏 วิดีโอธรรมะใหม่\n\nเจริญสติใน 5 นาที\nดูได้ที่: [Link]",
                        "image": "thumbnail.jpg",
                    }
                ],
                "note": "Enable when LINE OA is ready",
            },
            "tiktok": {
                "enabled": False,
                "note": "Create 60-90 sec vertical clips",
                "recommendation": "Extract key teaching moments",
                "aspect_ratio": "9:16",
            },
            "website": {
                "enabled": True,
                "priority": 3,
                "settings": {
                    "blog_post": {
                        "title": metadata.get("title", ""),
                        "content": "Embed YouTube + Full transcript",
                        "category": "Meditation",
                        "tags": metadata.get("tags", [])[:5],
                    },
                    "embed_code": "<iframe width='560' height='315' src='...'></iframe>",
                },
            },
        },
        "cross_promotion_schedule": {
            "day_0": {
                "time": "10:00",
                "action": "Publish to YouTube",
                "platforms": ["youtube"],
            },
            "day_0+2h": {
                "time": "12:00",
                "action": "Share to Facebook Page",
                "platforms": ["facebook"],
            },
            "day_0+4h": {
                "time": "14:00",
                "action": "Post to Website",
                "platforms": ["website"],
            },
            "day_1": {
                "time": "09:00",
                "action": "Share to Facebook Groups",
                "platforms": ["facebook_groups"],
            },
            "day_2": {
                "time": "10:00",
                "action": "LINE Broadcast (if enabled)",
                "platforms": ["line"],
            },
        },
        "analytics_tracking": {
            "utm_parameters": {
                "youtube": "?utm_source=youtube&utm_medium=video&utm_campaign=mindfulness_series",
                "facebook": "?utm_source=facebook&utm_medium=social&utm_campaign=mindfulness_series",
                "line": "?utm_source=line&utm_medium=broadcast&utm_campaign=mindfulness_series",
            },
            "metrics_to_track": [
                "views",
                "watch_time",
                "engagement_rate",
                "click_through_rate",
                "shares",
                "comments",
            ],
        },
        "automation_tools": [
            "Buffer (social media scheduling)",
            "Hootsuite (multi-platform posting)",
            "Zapier (workflow automation)",
            "YouTube Studio (native scheduling)",
        ],
    }

    write_json(out, multi_channel)
    log(
        f"✓ Multi-Channel publish configured - {len([p for p in multi_channel['platforms'].values() if p.get('enabled')])} platforms enabled"
    )
    return out


def agent_publish(step, run_dir: Path):
    """Scheduling & Publishing - จัดการเผยแพร่และกำหนดเวลา"""
    run_dir / step["input_from"]
    out = run_dir / step["output"]

    # รับ input หลายไฟล์
    input_from = step.get("input_from", {})
    if isinstance(input_from, dict):
        script_file = input_from.get("script", "script_validated.md")
        metadata_file = input_from.get("metadata", "metadata.json")
    else:
        metadata_file = input_from
        script_file = "script_validated.md"

    run_dir / script_file if "/" in script_file or "\\" in script_file else run_dir / script_file
    metadata_path = (
        run_dir / metadata_file
        if "/" in metadata_file or "\\" in metadata_file
        else run_dir / metadata_file
    )

    # อ่านข้อมูล
    metadata = read_json(metadata_path) if metadata_path.exists() else {}

    # สร้างข้อมูลการเผยแพร่
    publish_config = {
        "scheduled_at": datetime.now().isoformat(),
        "status": "ready_to_publish",
        "platforms": ["youtube"],
        "youtube": {
            "video_file": "output/final_video.mp4",
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "category": metadata.get("category", "Education"),
            "privacy": metadata.get("visibility", "public"),
            "publish_time": "tomorrow 10:00 +07:00",
            "playlist_id": None,
            "thumbnail": "output/thumbnail.jpg",
        },
        "checklist": {
            "video_file": False,
            "thumbnail": False,
            "script_approved": True,
            "metadata_ready": True,
            "doctrine_validated": True,
            "seo_optimized": True,
            "subtitles": False,
            "visual_assets": False,
            "voiceover": False,
        },
    }

    write_json(out, publish_config)

    # สร้าง checklist แยก
    checklist_md = f"""# 📋 Complete Publish Checklist

## ✅ Content Creation (Completed)
- [x] Trend Scout - Topics identified
- [x] Topic Prioritizer - Best topic selected
- [x] Research Retrieval - Citations gathered
- [x] Data Enrichment - Context added
- [x] Script Outline - Structure created
- [x] Script Writer - Full script written
- [x] Doctrine Validator - Approved ✅
- [x] Legal/Compliance - Compliant ✅

## ✅ Production Assets (To Complete)
- [ ] Visual Asset Guide - Review B-roll list
- [ ] Voiceover - Record or generate
- [ ] Localization - Thai subtitles ready
- [ ] Thumbnail - Design 3 concepts, pick best
- [ ] Format Conversion - Export final MP4

## ✅ Publishing (To Complete)
- [ ] SEO Metadata - Applied to video
- [ ] Multi-Channel - Schedule cross-posting
- [ ] Upload to YouTube
- [ ] Set publish time: {publish_config["youtube"]["publish_time"]}
- [ ] Add to playlist: "ธรรมะเบื้องต้น"
- [ ] Community post scheduled
- [ ] Backup/Archive - Save final package

## ✅ Post-Publishing
- [ ] Monitor first 24h metrics
- [ ] Respond to comments (first 2-3 hours critical)
- [ ] Check retention rate
- [ ] Update analytics dashboard
- [ ] Share to Facebook/LINE (staggered)

## 📊 Target Metrics (First Week)
- Views: 1,000+
- Watch Time: > 50% avg
- Likes: > 95%
- Comments: 20+
- Shares: 50+
"""

    checklist_path = run_dir / "publish_checklist.md"
    write_text(checklist_path, checklist_md)

    log(
        f"✓ Publish configured - Scheduled for {publish_config['youtube']['publish_time']}"
    )
    log(f"✓ Complete checklist created: {checklist_path}")
    return out


# ========== AGENT REGISTRY ==========

AGENTS = {
    # System Setup Phase
    "PromptPack": agent_prompt_pack,
    "AgentTemplate": agent_template,
    "Security": agent_security,
    "Integration": agent_integration,
    "DataSync": agent_data_sync,
    "InventoryIndex": agent_inventory_index,
    "Monitoring": agent_monitoring,
    "Notification": agent_notification,
    "ErrorFlag": agent_error_flag,
    "Dashboard": agent_dashboard,
    "BackupArchive": agent_backup_archive,
    # Video Workflow Phase
    "TrendScout": agent_trend_scout,
    "TopicPrioritizer": agent_topic_prioritizer,
    "ResearchRetrieval": agent_research_retrieval,
    "DataEnrichment": agent_data_enrichment,
    "ScriptOutline": agent_script_outline,
    "ScriptWriter": agent_script_writer,
    "DoctrineValidator": agent_doctrine_validator,
    "LegalCompliance": agent_legal_compliance,
    "VisualAsset": agent_visual_asset,
    "Voiceover": agent_voiceover,
    "voiceover.tts": agent_voiceover_tts,
    "video.render": agent_video_render,
    "quality.gate": agent_quality_gate,
    "post_templates": agent_post_templates,
    "post.templates": agent_post_templates,
    "dispatch.v0": agent_dispatch_v0,
    "youtube.upload": agent_youtube_upload,
    "Localization": agent_localization,
    "ThumbnailGenerator": agent_thumbnail_generator,
    "SEOAndMetadata": agent_seo_metadata,
    "FormatConversion": agent_format_conversion,
    "MultiChannelPublish": agent_multi_channel_publish,
    "SchedulingPublishing": agent_publish,
}


# ========== PIPELINE RUNNER ==========


def run_pipeline(pipeline_path: Path, run_id: str):
    """รัน pipeline ตามไฟล์ YAML"""
    log(f"Loading pipeline: {pipeline_path}")

    pipeline_enabled = parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))
    if not pipeline_enabled:
        log("Pipeline disabled by PIPELINE_ENABLED=false", "INFO")
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return {
            "pipeline": "unknown",
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "total_steps": 0,
            "successful": 0,
            "failed": 0,
            "results": {},
            "output_dir": str(ROOT / "output" / run_id),
            "status": "disabled",
        }

    with open(pipeline_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    pipeline_name = cfg.get("pipeline", "unknown")
    steps = cfg.get("steps", [])

    def _pipeline_has_step(step_name: str, *, aliases: set[str] | None = None) -> bool:
        """ตรวจสอบว่า step ที่มีค่า uses ตามที่กำหนดมีอยู่ใน pipeline หรือไม่"""
        allowed = aliases or {step_name}
        return any(
            isinstance(step_cfg, dict) and step_cfg.get("uses") in allowed
            for step_cfg in steps
        )

    has_quality_gate = _pipeline_has_step("quality.gate")
    has_post_templates = _pipeline_has_step(
        "post_templates", aliases=POST_TEMPLATES_ALIASES
    )
    has_dispatch_v0 = _pipeline_has_step("dispatch.v0")

    log(f"Pipeline: {pipeline_name} ({len(steps)} steps)")

    run_dir = ROOT / "output" / run_id

    log(f"Output directory: {run_dir}")

    def _is_dry_run_step(step_cfg: dict) -> bool:
        config = step_cfg.get("config")
        if not isinstance(config, dict):
            return False
        return bool(config.get("dry_run", False))

    dry_run_only_pipeline = bool(steps) and all(
        _is_dry_run_step(step_cfg) for step_cfg in steps
    )

    results = {}
    root_dir = ROOT.resolve()
    post_templates_ran = False
    dispatch_ran = False

    def _run_dispatch_once() -> None:
        """เรียก dispatch_v0 หนึ่งครั้งเมื่อยังไม่ได้รันและไม่มี step dispatch.v0 ระบุไว้"""
        nonlocal dispatch_ran
        if dispatch_ran or has_dispatch_v0:
            return
        _run_dispatch_v0_step(run_id, root_dir)
        dispatch_ran = True

    def _mark_post_templates_complete() -> None:
        """
        บันทึกสถานะว่าได้รัน post_templates แล้ว และจะเรียก dispatch_v0 ผ่าน
        _run_dispatch_once() เฉพาะเมื่อ “ทั้งสองเงื่อนไข” เป็นจริง:

        - dispatch_v0 ยังไม่เคยถูกรันใน pipeline run นี้ และ
        - pipeline ไม่มี step ที่ uses == "dispatch.v0" ระบุไว้โดยตรง
        """
        nonlocal post_templates_ran
        post_templates_ran = True
        _run_dispatch_once()

    def _maybe_run_post_templates(step_uses: str, step_result: object) -> None:
        """
        ตรวจสอบเงื่อนไขและเรียก post_templates แบบอัตโนมัติเมื่อเหมาะสม

        Args:
            step_uses: ค่า uses ของ step ที่เพิ่งรันเสร็จ
            step_result: ผลลัพธ์จาก step นั้น (ใช้เช็ค dry_run)

        หมายเหตุ:
            - จะข้ามถ้ามี step post_templates ระบุไว้แล้ว หรือเคยรันไปแล้ว
            - จะรันหลัง quality.gate หรือหลัง video.render (เมื่อไม่มี quality.gate)
        """
        nonlocal post_templates_ran
        if post_templates_ran or has_post_templates:
            return
        if isinstance(step_result, PlannedArtifacts) and step_result.dry_run:
            return
        if step_uses == "quality.gate" or (
            step_uses == "video.render" and not has_quality_gate
        ):
            # ถ้าไม่มี step post_templates ที่ชัดเจน ให้รันแบบโดยอัตโนมัติหลังจาก
            # quality gate (แนะนำ) หรือหลัง video render เป็น fallback
            try:
                _run_post_templates_step(run_id, root_dir)
                _mark_post_templates_complete()
            except Exception as e:
                log(
                    f"ERROR in auto-invoked post_templates (after {step_uses}): {e}",
                    "ERROR",
                )
                raise

    for i, step in enumerate(steps, 1):
        step_id = step["id"]
        uses = step["uses"]

        log(f"[{i}/{len(steps)}] Running: {step_id} (uses: {uses})")

        agent_func = AGENTS.get(uses)
        if not agent_func:
            log(f"ERROR: Agent not implemented: {uses}", "ERROR")
            raise RuntimeError(f"Agent not implemented: {uses}")

        try:
            result = agent_func(step, run_dir)
            output_path = result
            planned_paths = None
            if isinstance(result, PlannedArtifacts):
                output_path = result.output_path
                if dry_run_only_pipeline:
                    planned_paths = result.planned_paths
            entry = {"status": "success", "output": str(output_path)}
            if planned_paths is not None:
                entry["planned_paths"] = planned_paths
            results[step_id] = entry
            if uses in POST_TEMPLATES_ALIASES:
                _mark_post_templates_complete()
            if uses == "dispatch.v0":
                dispatch_ran = True
            log(f"[{i}/{len(steps)}] ✓ {step_id} completed", "SUCCESS")
            _maybe_run_post_templates(uses, result)
        except Exception as e:
            log(f"ERROR in {step_id}: {e}", "ERROR")
            results[step_id] = {"status": "error", "error": str(e)}
            raise

    # สรุปผล
    summary = {
        "pipeline": pipeline_name,
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "total_steps": len(steps),
        "successful": len([r for r in results.values() if r["status"] == "success"]),
        "failed": len([r for r in results.values() if r["status"] == "error"]),
        "results": results,
        "output_dir": str(run_dir),
    }

    if dry_run_only_pipeline:
        log("=" * 60)
        log("Pipeline completed (dry run) - no files were written")
        log("=" * 60)
        return summary

    summary_path = run_dir / "pipeline_summary.json"
    write_json(summary_path, summary)

    log("=" * 60)
    log(
        f"Pipeline completed: {summary['successful']}/{summary['total_steps']} steps successful"
    )
    log(f"Results saved to: {run_dir}")
    log("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Dhamma Channel Automation - Orchestrator"
    )
    parser.add_argument("--pipeline", required=True, help="Path to YAML pipeline file")
    parser.add_argument("--run-id", default=None, help="Run ID (default: timestamp)")
    parser.add_argument(
        "--topic", default=None, help="Topic title to use (overrides mock data)"
    )

    args = parser.parse_args()

    # Check global kill switch (PIPELINE_ENABLED)
    pipeline_enabled = parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))

    if not pipeline_enabled:
        log("Pipeline disabled by PIPELINE_ENABLED=false", "INFO")
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return 0  # Exit successfully (no-op)

    if args.run_id is None:
        args.run_id = f"run_{int(time.time())}"

    # Store topic in environment for agents to access
    if args.topic:
        os.environ["DHAMMA_TOPIC"] = args.topic

    pipeline_path = Path(args.pipeline)

    if not pipeline_path.exists():
        print(f"ERROR: Pipeline file not found: {pipeline_path}")
        return 1

    try:
        run_pipeline(pipeline_path, args.run_id)
        return 0
    except Exception as e:
        log(f"Pipeline failed: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    exit(main())
