"""DataSyncAgent - จัดการตรวจสอบและเตรียม payload สำหรับงานซิงก์ข้อมูล"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from automation_core.base_agent import BaseAgent

from .model import (
    DataSyncLogEntry,
    DataSyncPayload,
    DataSyncRequest,
    DataSyncResponse,
)


class DataSyncAgent(BaseAgent[DataSyncRequest, DataSyncResponse]):
    """Agent สำหรับประมวลผล data_sync_request และสร้าง payload พร้อม log"""

    DEFAULT_SCHEMA_RESOURCE = "schema_registry.json"

    def __init__(
        self,
        *,
        schema_registry: Mapping[str, Sequence[str]] | None = None,
        schema_registry_path: str | Path | None = None,
    ) -> None:
        super().__init__(
            name="DataSyncAgent",
            version="1.0.0",
            description="ตรวจสอบ schema และเตรียม payload สำหรับงานซิงก์ข้อมูล",
        )

        self.schema_registry: dict[str, list[str]] = self._load_schema_registry(
            schema_registry=schema_registry,
            schema_registry_path=schema_registry_path,
        )

    def _load_schema_registry(
        self,
        *,
        schema_registry: Mapping[str, Sequence[str]] | None,
        schema_registry_path: str | Path | None,
    ) -> dict[str, list[str]]:
        if schema_registry is not None:
            return self._normalize_schema_registry(schema_registry)

        if schema_registry_path is not None:
            path = Path(schema_registry_path)
            if not path.exists():
                msg = f"schema registry path '{path}' ไม่พบไฟล์"
                raise FileNotFoundError(msg)
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._normalize_schema_registry(data)

        with resources.files(__package__).joinpath(
            self.DEFAULT_SCHEMA_RESOURCE
        ).open("r", encoding="utf-8") as registry_file:
            data = json.load(registry_file)
        return self._normalize_schema_registry(data)

    @staticmethod
    def _normalize_schema_registry(
        data: Mapping[str, Sequence[str] | Any]
    ) -> dict[str, list[str]]:
        normalized: dict[str, list[str]] = {}
        for version, fields in data.items():
            if isinstance(fields, (str, bytes)):  # noqa: UP038 - Python < 3.10 compatibility
                msg = "schema registry ต้องระบุ list ของชื่อฟิลด์เป็น string"
                raise ValueError(msg)
            if not isinstance(fields, Sequence):
                msg = "schema registry ต้องระบุ list ของชื่อฟิลด์เป็น string"
                raise ValueError(msg)
            field_list: list[str] = []
            for field in fields:
                if not isinstance(field, str):
                    msg = "schema registry ต้องประกอบด้วยชื่อฟิลด์เป็น string เท่านั้น"
                    raise ValueError(msg)
                field_list.append(field)
            normalized[str(version)] = field_list
        return normalized

    def run(self, input_data: DataSyncRequest) -> DataSyncResponse:
        logs: list[DataSyncLogEntry] = []
        warnings: list[str] = []
        errors: list[str] = []
        suggestions: list[str] = []

        expected_fields = self.schema_registry.get(input_data.data.schema_version)

        # 1. ตรวจสอบ schema
        if input_data.rule.validate_schema:
            if expected_fields is None:
                errors.append(
                    f"ไม่รู้จัก schema_version '{input_data.data.schema_version}'"
                )
                logs.append(
                    DataSyncLogEntry(
                        timestamp=datetime.now(timezone.utc),  # noqa: UP017
                        event="schema_validated",
                        status="failed",
                        message=(
                            f"schema_version {input_data.data.schema_version} ไม่อยู่ใน registry"
                        ),
                    )
                )
                suggestions.append(
                    "อัปเดต schema registry หรือใช้ schema_version ที่รองรับ"
                )
            else:
                actual_fields = input_data.data.fields
                duplicate_fields = sorted(
                    field
                    for field, count in Counter(actual_fields).items()
                    if count > 1
                )
                expected_set = set(expected_fields)
                actual_set = set(actual_fields)
                missing_fields = sorted(expected_set - actual_set)
                extra_fields = sorted(actual_set - expected_set)

                schema_status = "success"
                schema_messages: list[str] = []

                if duplicate_fields:
                    errors.append(
                        "พบฟิลด์ซ้ำ: " + ", ".join(duplicate_fields)
                    )
                    suggestions.append(
                        "ลบฟิลด์ที่ซ้ำออกเพื่อให้ mapping ตรงกับ schema"
                    )
                    schema_status = "failed"
                    schema_messages.append(
                        "พบฟิลด์ซ้ำ: " + ", ".join(duplicate_fields)
                    )

                if missing_fields:
                    errors.append(
                        "พบฟิลด์ขาดหาย: " + ", ".join(missing_fields)
                    )
                    suggestions.append(
                        "เติมข้อมูลฟิลด์ที่จำเป็นให้ตรงกับ schema ก่อนทำการซิงก์"
                    )
                    schema_status = "failed"
                    schema_messages.append(
                        "ฟิลด์ไม่ครบตาม schema: " + ", ".join(missing_fields)
                    )

                if schema_status == "success":
                    schema_message = (
                        f"field mapping ตรง schema {input_data.data.schema_version}"
                    )
                else:
                    schema_message = "; ".join(schema_messages)

                logs.append(
                    DataSyncLogEntry(
                        timestamp=datetime.now(timezone.utc),  # noqa: UP017
                        event="schema_validated",
                        status=schema_status,
                        message=schema_message,
                    )
                )

                if extra_fields:
                    warnings.append(
                        "พบฟิลด์เกินจาก schema: " + ", ".join(extra_fields)
                    )
                    suggestions.append(
                        "พิจารณาตรวจสอบฟิลด์ที่เกินก่อนการซิงก์หรืออัปเดต schema หากจำเป็น"
                    )

        # 2. ตรวจสอบ row_count
        if input_data.data.row_count <= 0:
            errors.append("row_count ต้องมากกว่า 0")
            logs.append(
                DataSyncLogEntry(
                    timestamp=datetime.now(timezone.utc),  # noqa: UP017
                    event="row_count_checked",
                    status="failed",
                    message="จำนวนแถวเป็น 0 หรือค่าติดลบ",
                )
            )
            suggestions.append(
                "ตรวจสอบขั้นตอนดึงข้อมูลหรือ filter ที่อาจทำให้ไม่มีข้อมูล"
            )
        else:
            logs.append(
                DataSyncLogEntry(
                    timestamp=datetime.now(timezone.utc),  # noqa: UP017
                    event="row_count_checked",
                    status="success",
                    message=f"row_count = {input_data.data.row_count}",
                )
            )

        # 3. ตรวจสอบ overwrite flag
        if input_data.rule.overwrite_if_exists:
            logs.append(
                DataSyncLogEntry(
                    timestamp=datetime.now(timezone.utc),  # noqa: UP017
                    event="overwrite_flag",
                    status="pending",
                    message="ตั้งค่า overwrite_if_exists = true (ตรวจสอบไฟล์ปลายทางก่อนคัดลอก)",
                )
            )

        # 4. ตัดสินใจสถานะและ log ผลการคัดลอก
        if errors:
            final_status = "error"
            logs.append(
                DataSyncLogEntry(
                    timestamp=datetime.now(timezone.utc),  # noqa: UP017
                    event="sync_aborted",
                    status="failed",
                    message="หยุดการซิงก์เนื่องจากพบข้อผิดพลาด",
                )
            )
        else:
            final_status = "warning" if warnings else "ready"
            logs.append(
                DataSyncLogEntry(
                    timestamp=datetime.now(timezone.utc),  # noqa: UP017
                    event="payload_ready",
                    status="warning" if warnings else "success",
                    message=(
                        "payload พร้อมสำหรับการซิงก์"
                        + (" พร้อมคำเตือน." if warnings else ".")
                    ),
                )
            )

        payload = DataSyncPayload(
            source_system=input_data.source_system,
            target_system=input_data.target_system,
            file_name=input_data.data.file_name,
            schema_version=input_data.data.schema_version,
            field_mapping=input_data.data.fields,
            row_count=input_data.data.row_count,
            sync_type=input_data.sync_type,
            rule=input_data.rule,
            status=final_status,
        )

        return DataSyncResponse(
            data_sync_payload=payload,
            data_sync_log=logs,
            suggestions=suggestions,
            warnings=warnings,
            errors=errors,
        )
