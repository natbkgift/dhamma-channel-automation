from __future__ import annotations

import argparse
import json
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.contracts.common import (
    _artifact_rel_path,
    _validate_relative_path,
    _validate_run_id,
)
from automation_core.contracts.publish_request_v1 import validate_publish_request
from automation_core.preview_summary_v0 import (
    MAX_PREVIEW_CHARS,
    PUBLISH_REASON,
    parse_pipeline_enabled,
    validate_preview_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "preview_bundle_v0"
BUNDLE_NAME = "preview_bundle.json"
PUBLISH_REQUEST_NAME = "publish_request.json"
PREVIEW_SUMMARY_NAME = "preview_summary.json"
EXPECTED_ACTIONS = 3
IDEMPOTENCY_HEX_LEN = 64
HEX_CHARS = "0123456789abcdef"
DEFAULT_DRY_RUN = True
DEFAULT_ALLOW_PUBLISH = False


def _publish_request_rel_path(run_id: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return _artifact_rel_path(run_id, PUBLISH_REQUEST_NAME, validate=False)


def _preview_summary_rel_path(run_id: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return _artifact_rel_path(run_id, PREVIEW_SUMMARY_NAME, validate=False)


def _load_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    return data


def load_publish_request(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any]]:
    run_id = _validate_run_id(run_id)
    relative = _publish_request_rel_path(run_id, validate=False)
    path = base_dir / relative
    if not path.is_file():
        raise FileNotFoundError(f"Publish request not found: {relative}")
    data = _load_json(path)
    validate_publish_request(data, run_id)
    return relative, data


def load_preview_summary(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any]]:
    run_id = _validate_run_id(run_id)
    relative = _preview_summary_rel_path(run_id, validate=False)
    path = base_dir / relative
    if not path.is_file():
        raise FileNotFoundError(f"Preview summary not found: {relative}")
    data = _load_json(path)
    validate_preview_summary(data, run_id)
    return relative, data


def _copy_dict_list(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in items]


def _extract_preview_components(
    preview_summary: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    status = None
    actions: list[dict[str, Any]] | None = None
    errors = preview_summary.get("errors") or []
    result = preview_summary.get("result")
    if isinstance(result, dict):
        if isinstance(result.get("status"), str):
            status = result["status"]
        if isinstance(result.get("actions"), list):
            actions = result["actions"]
    summary = preview_summary.get("summary")
    if isinstance(summary, dict):
        if status is None and isinstance(summary.get("mode"), str):
            status = summary["mode"]
        if actions is None and isinstance(summary.get("actions"), list):
            actions = summary["actions"]
    if status is None:
        status = "error" if errors else "ok"
    if actions is None:
        actions = []
    return status, _copy_dict_list(actions), _copy_dict_list(errors)


def build_preview_bundle(
    *,
    run_id: str,
    publish_request_path: str,
    preview_summary_path: str,
    publish_request: dict[str, Any],
    preview_summary: dict[str, Any],
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    checked = (checked_at or datetime.now(tz=UTC)).isoformat().replace("+00:00", "Z")
    inputs = publish_request["inputs"]
    request = publish_request["request"]
    controls = publish_request["controls"]
    status, actions, errors = _extract_preview_components(preview_summary)
    payload = {
        "schema_version": "v1",
        "engine": ENGINE_NAME,
        "run_id": run_id,
        "checked_at": checked,
        "inputs": {
            "publish_request": publish_request_path,
            "preview_summary": preview_summary_path,
        },
        "bundle": {
            "platform": inputs["platform"],
            "target": inputs["target"],
            "idempotency_key": controls["idempotency_key"],
            "controls": {
                "dry_run": controls["dry_run"],
                "allow_publish": controls["allow_publish"],
            },
            "content": {
                "short": request["content_short"],
                "long": request["content_long"],
            },
            "preview": {
                "status": status,
                "actions": actions,
                "errors": errors,
            },
            "policy": {
                "status": "pending",
                "reasons": [],
            },
        },
        "errors": [],
    }
    return payload


def _validate_hex_key(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("bundle.idempotency_key is required")
    if len(value) != IDEMPOTENCY_HEX_LEN or any(
        ch not in HEX_CHARS for ch in value.lower()
    ):
        raise ValueError(
            f"bundle.idempotency_key must be {IDEMPOTENCY_HEX_LEN} hex chars"
        )


def _validate_preview_actions(actions: list[dict[str, Any]]) -> None:
    if len(actions) != EXPECTED_ACTIONS:
        raise ValueError(f"bundle.preview.actions must have {EXPECTED_ACTIONS} items")

    def require_print(action: dict[str, Any], label: str) -> None:
        if action.get("type") != "print" or action.get("label") != label:
            raise ValueError(f"bundle.preview.actions {label} must be print/{label}")
        bytes_value = action.get("bytes")
        if not isinstance(bytes_value, int) or bytes_value < 0:
            raise ValueError(f"bundle.preview.actions {label}.bytes must be >= 0")
        preview = action.get("preview")
        if not isinstance(preview, str):
            raise ValueError(f"bundle.preview.actions {label}.preview must be string")
        if len(preview) > MAX_PREVIEW_CHARS:
            raise ValueError(
                f"bundle.preview.actions {label}.preview must be <= {MAX_PREVIEW_CHARS} chars"
            )

    def require_publish(action: dict[str, Any]) -> None:
        if action.get("type") != "noop" or action.get("label") != "publish":
            raise ValueError("bundle.preview.actions publish must be noop/publish")
        if action.get("reason") != PUBLISH_REASON:
            raise ValueError(
                "bundle.preview.actions publish reason must be no_publish_in_v0"
            )

    require_print(actions[0], "short")
    require_print(actions[1], "long")
    require_publish(actions[2])


def _validate_preview_errors(errors: list[dict[str, Any]]) -> None:
    for error in errors:
        if not isinstance(error, dict):
            raise ValueError("bundle.preview.errors must contain objects")
        code = error.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("error.code is required")
        message = error.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("error.message is required")
        if error.get("step") != "adapter.preview":
            raise ValueError("error.step must be 'adapter.preview'")
        if "detail" not in error:
            raise ValueError("error.detail is required")


def validate_preview_bundle(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("preview_bundle must be an object")
    if payload.get("schema_version") != "v1":
        raise ValueError("preview_bundle.schema_version must be 'v1'")
    if payload.get("engine") != ENGINE_NAME:
        raise ValueError(f"preview_bundle.engine must be '{ENGINE_NAME}'")

    _validate_run_id(run_id)
    payload_run_id = payload.get("run_id")
    if not isinstance(payload_run_id, str):
        raise ValueError("preview_bundle.run_id must be a string")
    _validate_run_id(payload_run_id)
    if payload_run_id != run_id:
        raise ValueError("preview_bundle.run_id must match run_id")

    checked_at = payload.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise ValueError("preview_bundle.checked_at is required")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("preview_bundle.inputs must be an object")
    publish_request_path = _validate_relative_path(
        inputs.get("publish_request"), "inputs.publish_request"
    )
    expected_publish = _publish_request_rel_path(run_id, validate=False)
    if publish_request_path != expected_publish:
        raise ValueError(
            "inputs.publish_request must be 'output/<run_id>/artifacts/publish_request.json'"
        )
    preview_summary_path = _validate_relative_path(
        inputs.get("preview_summary"), "inputs.preview_summary"
    )
    expected_summary = _preview_summary_rel_path(run_id, validate=False)
    if preview_summary_path != expected_summary:
        raise ValueError(
            "inputs.preview_summary must be 'output/<run_id>/artifacts/preview_summary.json'"
        )

    bundle = payload.get("bundle")
    if not isinstance(bundle, dict):
        raise ValueError("preview_bundle.bundle must be an object")

    platform = bundle.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("bundle.platform is required")
    target = bundle.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("bundle.target is required")
    _validate_hex_key(bundle.get("idempotency_key"))

    controls = bundle.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("bundle.controls must be an object")
    if controls.get("dry_run") is not DEFAULT_DRY_RUN:
        raise ValueError("bundle.controls.dry_run must be true")
    if controls.get("allow_publish") is not DEFAULT_ALLOW_PUBLISH:
        raise ValueError("bundle.controls.allow_publish must be false")

    content = bundle.get("content")
    if not isinstance(content, dict):
        raise ValueError("bundle.content must be an object")
    if not isinstance(content.get("short"), str):
        raise ValueError("bundle.content.short must be a string")
    if not isinstance(content.get("long"), str):
        raise ValueError("bundle.content.long must be a string")

    preview = bundle.get("preview")
    if not isinstance(preview, dict):
        raise ValueError("bundle.preview must be an object")
    status = preview.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("bundle.preview.status is required")
    actions = preview.get("actions")
    if not isinstance(actions, list):
        raise ValueError("bundle.preview.actions must be a list")
    _validate_preview_actions(actions)
    preview_errors = preview.get("errors") or []
    if not isinstance(preview_errors, list):
        raise ValueError("bundle.preview.errors must be a list")
    _validate_preview_errors(preview_errors)

    policy = bundle.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("bundle.policy must be an object")
    if policy.get("status") != "pending":
        raise ValueError("bundle.policy.status must be 'pending'")
    reasons = policy.get("reasons")
    if not isinstance(reasons, list):
        raise ValueError("bundle.policy.reasons must be a list")
    for reason in reasons:
        if not isinstance(reason, str):
            raise ValueError("bundle.policy.reasons must contain strings")

    errors = payload.get("errors") or []
    if not isinstance(errors, list):
        raise ValueError("preview_bundle.errors must be a list")
    return payload


def generate_preview_bundle(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any], Path | None]:
    run_id = _validate_run_id(run_id)
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return {}, None

    publish_rel, publish_request = load_publish_request(run_id, base_dir)
    preview_rel, preview_summary = load_preview_summary(run_id, base_dir)
    payload = build_preview_bundle(
        run_id=run_id,
        publish_request_path=publish_rel,
        preview_summary_path=preview_rel,
        publish_request=publish_request,
        preview_summary=preview_summary,
        checked_at=checked_at,
    )
    validate_preview_bundle(payload, run_id)

    output_path = base_dir / "output" / run_id / "artifacts" / BUNDLE_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    output_rel = output_path.relative_to(base_dir).as_posix()
    print(f"Preview bundle v0: wrote {output_rel}")
    return payload, output_path


def cli_main(argv: list[str] | None = None, base_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview bundle v0 - build preview_bundle.json"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    bundle_parser = subparsers.add_parser("bundle", help="Generate preview bundle (v0)")
    bundle_parser.add_argument("--run-id", required=True, help="Run identifier")

    args = parser.parse_args(argv)
    base_dir = base_dir or REPO_ROOT

    try:
        if args.command == "bundle":
            generate_preview_bundle(args.run_id, base_dir=base_dir)
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:  # pragma: no cover - CLI error handling
        traceback.print_exc()
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
