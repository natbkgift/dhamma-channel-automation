"""โมเดลข้อมูลสำหรับ DataSyncAgent"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SyncRule(BaseModel):
    """กฎการซิงก์ข้อมูล"""

    overwrite_if_exists: bool = Field(
        False, description="ถ้าจริงให้ overwrite ไฟล์ที่มีอยู่ในเป้าหมาย"
    )
    validate_schema: bool = Field(True, description="ตรวจสอบ schema ของข้อมูลก่อนซิงก์")


class SyncData(BaseModel):
    """รายละเอียดข้อมูลที่ต้องซิงก์"""

    file_name: str = Field(..., description="ชื่อไฟล์ที่จะซิงก์")
    schema_version: str = Field(..., description="เวอร์ชัน schema ของข้อมูล")
    fields: list[str] = Field(..., description="รายชื่อฟิลด์ในข้อมูล")
    row_count: int = Field(..., ge=0, description="จำนวนแถวของข้อมูล")

    @field_validator("fields")
    def validate_fields_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("fields ต้องมีอย่างน้อย 1 รายการ")
        return value


class DataSyncRequest(BaseModel):
    """คำขอสำหรับ DataSyncAgent"""

    source_system: str
    target_system: str
    sync_type: Literal["copy", "sync", "migrate", "update", "merge"]
    data: SyncData
    rule: SyncRule


class DataSyncLogEntry(BaseModel):
    """รายการ log ของกระบวนการซิงก์"""

    timestamp: datetime
    event: str
    status: Literal["success", "warning", "failed", "pending"]
    message: str


class DataSyncPayload(BaseModel):
    """ข้อมูล payload สำหรับการซิงก์"""

    source_system: str
    target_system: str
    file_name: str
    schema_version: str
    field_mapping: list[str]
    row_count: int
    sync_type: Literal["copy", "sync", "migrate", "update", "merge"]
    rule: SyncRule
    status: Literal["ready", "pending", "warning", "error", "merged"]


class DataSyncResponse(BaseModel):
    """ผลลัพธ์ของ DataSyncAgent"""

    data_sync_payload: DataSyncPayload
    data_sync_log: list[DataSyncLogEntry]
    suggestions: list[str]
    warnings: list[str]
    errors: list[str]
