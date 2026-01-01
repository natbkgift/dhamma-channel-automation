"""
ตัวช่วยจัดการพารามิเตอร์ pipeline สำหรับ runtime env
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

PIPELINE_PARAMS_ENV = "PIPELINE_PARAMS_JSON"
_MISSING = object()


class ParamsSerializationError(ValueError):
    """ข้อผิดพลาดเมื่อ params ไม่สามารถแปลงเป็น JSON ได้"""


def serialize_pipeline_params(params: dict[str, Any]) -> str:
    """แปลง params เป็น JSON แบบ deterministic"""

    try:
        return json.dumps(
            params,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ParamsSerializationError("job params must be JSON serializable") from exc


@contextmanager
def inject_pipeline_params(params: dict[str, Any] | None) -> Iterator[None]:
    """ตั้งค่า env สำหรับ params ชั่วคราวและคืนค่าเดิมเสมอ"""

    previous = os.environ.get(PIPELINE_PARAMS_ENV, _MISSING)
    try:
        if params:
            payload = serialize_pipeline_params(params)
            os.environ[PIPELINE_PARAMS_ENV] = payload
        else:
            os.environ.pop(PIPELINE_PARAMS_ENV, None)
        yield
    finally:
        if previous is _MISSING:
            os.environ.pop(PIPELINE_PARAMS_ENV, None)
        else:
            os.environ[PIPELINE_PARAMS_ENV] = previous
