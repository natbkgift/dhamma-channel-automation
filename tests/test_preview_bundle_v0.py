from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from automation_core import preview_bundle_v0
from automation_core.contracts import publish_request_v1

TEST_CHECKED_AT_STR = "2026-01-01T00:00:00Z"
TEST_CHECKED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _idempotency_key(run_id: str, target: str, platform: str, content_long: str) -> str:
    return publish_request_v1._compute_idempotency_key(
        run_id=run_id, target=target, platform=platform, content_long=content_long
    )


def write_publish_request_v1(
    base_dir: Path,
    run_id: str,
    *,
    target: str = "youtube_community",
    platform: str = "youtube",
    short: str = "short content",
    long: str = "long content",
) -> dict[str, Any]:
    payload = {
        "schema_version": "v1",
        "engine": "publish_request_v0",
        "run_id": run_id,
        "checked_at": TEST_CHECKED_AT_STR,
        "inputs": {
            "post_content_summary": f"output/{run_id}/artifacts/post_content_summary.json",
            "dispatch_audit": f"output/{run_id}/artifacts/dispatch_audit.json",
            "platform": platform,
            "target": target,
        },
        "request": {
            "content_short": short,
            "content_long": long,
            "attachments": [],
        },
        "controls": {
            "dry_run": True,
            "allow_publish": False,
            "idempotency_key": _idempotency_key(
                run_id=run_id, target=target, platform=platform, content_long=long
            ),
        },
        "policy": {"status": "pending", "reasons": []},
        "errors": [],
    }
    path = base_dir / "output" / run_id / "artifacts" / "publish_request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_preview_summary_v1(
    base_dir: Path,
    run_id: str,
    *,
    target: str,
    platform: str,
    short: str = "preview short",
    long: str = "preview long",
    errors: list[dict[str, Any]] | None = None,
    include_result: bool = False,
    status: str = "ok",
) -> dict[str, Any]:
    actions = [
        {
            "type": "print",
            "label": "short",
            "bytes": len(short),
            "preview": short[:500],
        },
        {"type": "print", "label": "long", "bytes": len(long), "preview": long[:500]},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    payload = {
        "schema_version": "v1",
        "engine": "preview_summary_v0",
        "run_id": run_id,
        "checked_at": TEST_CHECKED_AT_STR,
        "inputs": {
            "publish_request": f"output/{run_id}/artifacts/publish_request.json",
            "post_content_summary": f"output/{run_id}/artifacts/post_content_summary.json",
            "dispatch_audit": f"output/{run_id}/artifacts/dispatch_audit.json",
            "platform": platform,
            "target": target,
        },
        "summary": {
            "target": target,
            "platform": platform,
            "mode": "dry_run",
            "actions": actions,
        },
        "policy": {"status": "preview_only", "reasons": []},
        "errors": errors or [],
    }
    if include_result:
        payload["result"] = {
            "status": status,
            "actions": actions,
        }
    path = base_dir / "output" / run_id / "artifacts" / "preview_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _strip_checked_at(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "checked_at"}


def test_preview_bundle_happy_path_writes_file(tmp_path: Path) -> None:
    run_id = "run_preview_bundle"
    publish_request = write_publish_request_v1(tmp_path, run_id)
    preview_summary = write_preview_summary_v1(
        tmp_path,
        run_id,
        target="youtube_community",
        platform="youtube",
        short="short sample",
        long="long sample preview",
    )

    checked_at = TEST_CHECKED_AT
    payload, output_path = preview_bundle_v0.generate_preview_bundle(
        run_id, base_dir=tmp_path, checked_at=checked_at
    )

    assert output_path is not None
    assert output_path.is_file()
    output_text = output_path.read_text(encoding="utf-8")
    saved = json.loads(output_text)
    assert saved == payload
    assert output_text == json.dumps(payload, ensure_ascii=False, indent=2)
    assert payload["schema_version"] == "v1"
    assert payload["engine"] == "preview_bundle_v0"
    assert payload["run_id"] == run_id
    assert payload["bundle"]["platform"] == publish_request["inputs"]["platform"]
    assert payload["bundle"]["target"] == publish_request["inputs"]["target"]
    assert payload["bundle"]["controls"] == {"dry_run": True, "allow_publish": False}
    assert payload["bundle"]["preview"]["status"] == "dry_run"
    assert (
        payload["bundle"]["preview"]["actions"] == preview_summary["summary"]["actions"]
    )
    assert payload["bundle"]["preview"]["errors"] == preview_summary["errors"]
    assert payload["bundle"]["policy"]["status"] == "pending"


def test_preview_bundle_kill_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_preview_bundle_disabled"
    write_publish_request_v1(tmp_path, run_id)
    write_preview_summary_v1(
        tmp_path, run_id, target="youtube_community", platform="youtube"
    )
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    payload, output_path = preview_bundle_v0.generate_preview_bundle(
        run_id, base_dir=tmp_path
    )

    assert payload == {}
    assert output_path is None
    assert not (
        tmp_path / "output" / run_id / "artifacts" / "preview_bundle.json"
    ).exists()


def test_preview_bundle_deterministic_output(tmp_path: Path) -> None:
    run_id = "run_preview_bundle_deterministic"
    write_publish_request_v1(tmp_path, run_id, long="deterministic long content")
    write_preview_summary_v1(
        tmp_path,
        run_id,
        target="youtube_community",
        platform="youtube",
        short="short deterministic",
        long="long deterministic",
    )

    first, _ = preview_bundle_v0.generate_preview_bundle(run_id, base_dir=tmp_path)
    second, _ = preview_bundle_v0.generate_preview_bundle(run_id, base_dir=tmp_path)

    assert _strip_checked_at(first) == _strip_checked_at(second)


def test_preview_bundle_missing_publish_request(tmp_path: Path) -> None:
    run_id = "run_preview_bundle_missing_publish"
    write_preview_summary_v1(
        tmp_path, run_id, target="youtube_community", platform="youtube"
    )

    with pytest.raises(FileNotFoundError, match="Publish request not found"):
        preview_bundle_v0.generate_preview_bundle(run_id, base_dir=tmp_path)


def test_preview_bundle_missing_preview_summary(tmp_path: Path) -> None:
    run_id = "run_preview_bundle_missing_summary"
    write_publish_request_v1(tmp_path, run_id)

    with pytest.raises(FileNotFoundError, match="Preview summary not found"):
        preview_bundle_v0.generate_preview_bundle(run_id, base_dir=tmp_path)


def test_preview_bundle_validate_relative_paths(tmp_path: Path) -> None:
    run_id = "run_preview_bundle_invalid_path"
    write_publish_request_v1(tmp_path, run_id)
    write_preview_summary_v1(
        tmp_path, run_id, target="youtube_community", platform="youtube"
    )

    payload, _ = preview_bundle_v0.generate_preview_bundle(
        run_id, base_dir=tmp_path, checked_at=TEST_CHECKED_AT
    )
    # Start from a valid payload and flip the path to ensure validator rejects absolute inputs
    payload["inputs"]["publish_request"] = (
        f"/abs/{run_id}/artifacts/publish_request.json"
    )

    with pytest.raises(ValueError, match="inputs.publish_request"):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)


@pytest.fixture
def validation_test_payload(
    request: pytest.FixtureRequest, tmp_path: Path
) -> tuple[dict[str, Any], str]:
    run_id = f"run_{request.node.name}"
    write_publish_request_v1(tmp_path, run_id)
    write_preview_summary_v1(
        tmp_path, run_id, target="youtube_community", platform="youtube"
    )
    payload, _ = preview_bundle_v0.generate_preview_bundle(run_id, base_dir=tmp_path)
    return payload, run_id


def test_extract_preview_components_prefers_result_over_summary() -> None:
    summary_actions = [
        {"type": "print", "label": "short", "bytes": 1, "preview": "a"},
        {"type": "print", "label": "long", "bytes": 2, "preview": "bb"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    result_actions = [
        {"type": "print", "label": "short", "bytes": 3, "preview": "ccc"},
        {"type": "print", "label": "long", "bytes": 4, "preview": "dddd"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "summary": {"actions": summary_actions},
            "result": {"status": "ok", "actions": result_actions},
            "errors": [],
        }
    )

    assert status == "ok"
    assert actions == result_actions
    assert errors == []


def test_extract_preview_components_falls_back_without_result() -> None:
    summary_actions = [
        {"type": "print", "label": "short", "bytes": 1, "preview": "a"},
        {"type": "print", "label": "long", "bytes": 2, "preview": "bb"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "summary": {"mode": "dry_run", "actions": summary_actions},
            "errors": [],
        }
    )

    assert status == "dry_run"
    assert actions == summary_actions
    assert errors == []


def test_extract_preview_components_falls_back_without_summary() -> None:
    result_actions = [
        {"type": "print", "label": "short", "bytes": 3, "preview": "ccc"},
        {"type": "print", "label": "long", "bytes": 4, "preview": "dddd"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "result": {"status": "ok", "actions": result_actions},
            "errors": [],
        }
    )

    assert status == "ok"
    assert actions == result_actions
    assert errors == []


def test_extract_preview_components_falls_back_to_summary_actions() -> None:
    summary_actions = [
        {"type": "print", "label": "short", "bytes": 1, "preview": "a"},
        {"type": "print", "label": "long", "bytes": 2, "preview": "bb"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "summary": {"actions": summary_actions},
            "result": {"status": "ok"},
            "errors": [],
        }
    )

    assert status == "ok"
    assert actions == summary_actions
    assert errors == []


def test_extract_preview_components_falls_back_to_summary_status() -> None:
    result_actions = [
        {"type": "print", "label": "short", "bytes": 3, "preview": "ccc"},
        {"type": "print", "label": "long", "bytes": 4, "preview": "dddd"},
        {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
    ]
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "summary": {"mode": "dry_run"},
            "result": {"actions": result_actions},
            "errors": [],
        }
    )

    assert status == "dry_run"
    assert actions == result_actions
    assert errors == []


def test_extract_preview_components_marks_error_when_errors_present() -> None:
    status, actions, errors = preview_bundle_v0._extract_preview_components(
        {
            "summary": {"mode": "dry_run", "actions": []},
            "errors": [{"code": "preview_error"}],
        }
    )

    assert status == "error"
    assert actions == []
    assert errors == [{"code": "preview_error"}]


def test_preview_bundle_rejects_uppercase_idempotency_key(
    validation_test_payload: tuple[dict[str, Any], str],
) -> None:
    payload, run_id = validation_test_payload

    payload["bundle"]["idempotency_key"] = payload["bundle"]["idempotency_key"].upper()

    with pytest.raises(ValueError, match="bundle.idempotency_key"):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)


def test_preview_bundle_rejects_invalid_action_order(
    validation_test_payload: tuple[dict[str, Any], str],
) -> None:
    payload, run_id = validation_test_payload
    actions = payload["bundle"]["preview"]["actions"]
    actions[0], actions[1] = actions[1], actions[0]

    with pytest.raises(
        ValueError,
        match="bundle.preview.actions short must be print/short",
    ):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)


def test_preview_bundle_rejects_invalid_publish_reason(
    validation_test_payload: tuple[dict[str, Any], str],
) -> None:
    payload, run_id = validation_test_payload
    payload["bundle"]["preview"]["actions"][2]["reason"] = "publish"

    with pytest.raises(ValueError, match="bundle.preview.actions publish reason"):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)


def test_preview_bundle_rejects_invalid_action_type(
    validation_test_payload: tuple[dict[str, Any], str],
) -> None:
    payload, run_id = validation_test_payload
    payload["bundle"]["preview"]["actions"][0]["type"] = "noop"

    with pytest.raises(
        ValueError,
        match="bundle.preview.actions short must be print/short",
    ):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)


def test_preview_bundle_rejects_invalid_error_step(
    validation_test_payload: tuple[dict[str, Any], str],
) -> None:
    payload, run_id = validation_test_payload
    payload["bundle"]["preview"]["errors"] = [
        {
            "code": "preview_error",
            "message": "failed",
            "step": "adapter.publish",
            "detail": {},
        }
    ]

    with pytest.raises(ValueError, match="error.step must be 'adapter.preview'"):
        preview_bundle_v0.validate_preview_bundle(payload, run_id)
