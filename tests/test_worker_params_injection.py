"""ทดสอบการ inject params ลง env ของ worker"""

from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from automation_core.queue import FileQueue, JobSpec, QueueItem


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _build_job(
    job_id: str,
    scheduled_for: datetime,
    run_id: str,
    params: dict[str, Any] | None,
) -> JobSpec:
    return JobSpec(
        schema_version="v1",
        job_id=job_id,
        created_at=_utc_iso(datetime.now(UTC)),
        scheduled_for=_utc_iso(scheduled_for),
        pipeline_path="pipeline.web.yml",
        run_id=run_id,
        params=params,
        status="pending",
        attempts=0,
        last_error=None,
    )


def _load_runner() -> ModuleType:
    runner_path = Path(__file__).parent.parent / "scripts" / "scheduler_runner.py"
    spec = importlib.util.spec_from_file_location("scheduler_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "false")


def test_injects_params_and_restores_env_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", "previous")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-params",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run-params",
        {"topic_seed": "mindfulness", "slug": "ep001"},
    )
    queue.enqueue(job)

    captured: dict[str, str | None] = {"value": None}

    def _runner_stub(_pipeline_path: Path, _run_id: str) -> None:
        captured["value"] = os.environ.get("PIPELINE_PARAMS_JSON")

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["decision"] == "done"
    assert captured["value"] == '{"slug":"ep001","topic_seed":"mindfulness"}'
    assert os.environ.get("PIPELINE_PARAMS_JSON") == "previous"


def test_restores_env_on_orchestrator_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", "before")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-fail",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run-fail",
        {"slug": "ep002"},
    )
    queue.enqueue(job)

    def _runner_stub(_pipeline_path: Path, _run_id: str) -> None:
        raise RuntimeError("boom")

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "orchestrator_failed"
    assert os.environ.get("PIPELINE_PARAMS_JSON") == "before"


@pytest.mark.parametrize("params_value", [None, {}])
def test_does_not_set_env_when_params_none_or_empty(
    params_value: dict[str, Any] | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", "existing")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-empty",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run-empty",
        params_value,
    )
    queue.enqueue(job)

    captured: dict[str, str | None] = {"value": "unset"}

    def _runner_stub(_pipeline_path: Path, _run_id: str) -> None:
        captured["value"] = os.environ.get("PIPELINE_PARAMS_JSON")

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["decision"] == "done"
    assert captured["value"] is None
    assert os.environ.get("PIPELINE_PARAMS_JSON") == "existing"


def test_pipeline_disabled_no_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", "should-stay")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-disabled",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run-disabled",
        {"slug": "ep003"},
    )
    queue.enqueue(job)

    called = {"count": 0}

    def _runner_stub(_pipeline_path: Path, _run_id: str) -> None:
        called["count"] += 1

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is None
    assert called["count"] == 0
    assert os.environ.get("PIPELINE_PARAMS_JSON") == "should-stay"
    assert not (tmp_path / "output").exists()


def test_params_not_json_serializable_marks_failed_and_restores_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", "before")

    job = _build_job(
        "job-bad-params",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run-bad-params",
        {"when": object()},
    )
    item = QueueItem(
        filename="20260101T000000Z_job-bad-params.json",
        path=tmp_path / "queue" / "pending" / "job-bad-params.json",
        job=job,
        job_id=job.job_id,
    )
    created_queue: dict[str, Any] = {}

    class _FakeQueue:
        def __init__(self, _queue_dir: Path | str) -> None:
            created_queue["instance"] = self
            self.mark_failed_called = False
            self.last_error: str | None = None

        def dequeue_next(self) -> QueueItem | None:
            return item

        def mark_failed(self, _item: QueueItem, error: Any | None = None) -> QueueItem:
            self.mark_failed_called = True
            self.last_error = getattr(error, "code", None)
            return _item

    monkeypatch.setattr(runner, "FileQueue", _FakeQueue)

    called = {"count": 0}

    def _runner_stub(_pipeline_path: Path, _run_id: str) -> None:
        called["count"] += 1

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    queue_instance = created_queue["instance"]
    assert summary is not None
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "job_invalid"
    assert called["count"] == 0
    assert os.environ.get("PIPELINE_PARAMS_JSON") == "before"
    assert queue_instance.mark_failed_called is True
    assert queue_instance.last_error == "job_invalid"
