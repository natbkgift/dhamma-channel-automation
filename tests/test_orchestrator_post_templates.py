from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _write_video_render_summary(base_dir: Path, run_id: str) -> None:
    """
    เขียนไฟล์ video_render_summary.json สำหรับการทดสอบ

    Args:
        base_dir: โฟลเดอร์หลักสำหรับสร้าง output
        run_id: รหัสการรัน pipeline

    Returns:
        None
    """
    summary_path = (
        base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"hook": "Hook line", "cta": "Call to action"}
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _assert_relative(value: str) -> None:
    """
    ตรวจสอบว่า path เป็น relative path และไม่มี path traversal

    Args:
        value: ค่า path ในรูปแบบสตริงที่ต้องการตรวจสอบ

    Raises:
        AssertionError: หาก path เป็น absolute หรือมี ".." อยู่ใน path
    """
    path = Path(value)
    assert not path.is_absolute()
    assert ".." not in path.parts


def test_orchestrator_post_templates_enabled(tmp_path, monkeypatch):
    run_id = "run_post_templates"
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Sample title",
        description="Sample summary",
        tags=["#alpha", "#beta"],
    )
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: post_templates_enabled
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.delenv("PIPELINE_PARAMS_JSON", raising=False)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v1"

    inputs = summary["inputs"]
    _assert_relative(inputs["template_short"])
    _assert_relative(inputs["template_long"])

    sources = inputs["sources"]
    assert sources == [
        f"output/{run_id}/metadata.json",
        f"output/{run_id}/artifacts/video_render_summary.json",
    ]
    for source in sources:
        _assert_relative(source)


def test_orchestrator_post_templates_disabled_no_output(tmp_path, monkeypatch, capsys):
    run_id = "run_post_templates_disabled"
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: post_templates_disabled
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_path),
            "--run-id",
            run_id,
        ],
    )

    exit_code = orchestrator.main()

    assert exit_code == 0
    assert not (tmp_path / "output" / run_id).exists()

    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out


def test_explicit_post_templates_step_disables_fallback(tmp_path, monkeypatch):
    """
    เมื่อระบุขั้นตอน post_templates อย่างชัดเจนต้องไม่เรียกซ้ำแบบอัตโนมัติ
    และต้องไม่เขียนไฟล์เมื่อปิด PIPELINE_ENABLED
    """
    run_id = "explicit_post_templates_once"
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Explicit step",
        description="Ensure single execution",
        tags=["#explicit"],
    )
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: explicit_post_templates
steps:
  - id: quality_gate
    uses: quality.gate
  - id: post_templates
    uses: post.templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls: list[str] = []
    original = orchestrator._run_post_templates_step

    def wrapped(run_id_arg: str, root_dir: Path) -> str:
        calls.append(run_id_arg)
        return original(run_id_arg, root_dir)

    monkeypatch.setattr(orchestrator, "_run_post_templates_step", wrapped)

    def fake_quality_gate(_step, run_dir: Path) -> str:
        return "artifacts/quality_gate_summary.json"

    monkeypatch.setitem(orchestrator.AGENTS, "quality.gate", fake_quality_gate)

    orchestrator.run_pipeline(pipeline_path, run_id)

    post_summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert post_summary_path.exists()
    assert calls == [run_id]

    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    calls.clear()
    disabled_run = "explicit_post_templates_disabled"

    orchestrator.run_pipeline(pipeline_path, disabled_run)

    assert calls == []
    assert not (tmp_path / "output" / disabled_run).exists()
