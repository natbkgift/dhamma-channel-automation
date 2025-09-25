"""
Pydantic Models สำหรับ ScriptOutlineAgent
กำหนด Schema สำหรับ Input และ Output ของ Agent
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ViewerPersona(BaseModel):
    """โปรไฟล์ผู้ชมเป้าหมาย"""

    name: str = Field(description="ชื่อกลุ่มผู้ชม")
    pain_points: list[str] = Field(description="ปัญหาที่พบ")
    desired_state: str = Field(description="สถานะที่ต้องการ")

    @field_validator("pain_points")
    @classmethod
    def validate_pain_points(cls, v):
        if not v:
            raise ValueError("ต้องมีปัญหาอย่างน้อย 1 ข้อ")
        return v


class StylePreferences(BaseModel):
    """การตั้งค่าสไตล์การนำเสนอ"""

    tone: str = Field(description="น้ำเสียงการนำเสนอ")
    avoid: list[str] = Field(description="สิ่งที่ควรหลีกเลี่ยง")


class RetentionGoals(BaseModel):
    """เป้าหมายการกักเก็บผู้ชม"""

    hook_drop_max_pct: int = Field(description="% การดรอปสูงสุดที่ hook", ge=0, le=100)
    mid_segment_break_every_sec: int = Field(
        description="ช่วงเวลาการแทรก retention pattern", gt=0
    )


class CoreTeachingSubSegment(BaseModel):
    """ส่วนย่อยของการสอนหลัก"""

    label: str = Field(description="ชื่อส่วนย่อย")
    est_seconds: int = Field(description="เวลาประมาณ (วินาที)", gt=0)
    teaching_points: list[str] = Field(description="ประเด็นการสอน")
    concept_links: list[str] = Field(description="แนวคิดที่เชื่อมโยง")
    citation_placeholders: list[str] = Field(description="ตัวอย่างการอ้างอิง")
    retention_tags: list[str] = Field(description="แท็ก retention pattern")


class OutlineSection(BaseModel):
    """ส่วนหนึ่งของโครงร่าง"""

    section: str = Field(description="ชื่อส่วน")
    goal: str | None = Field(None, description="เป้าหมายของส่วนนี้")
    est_seconds: int = Field(description="เวลาประมาณ (วินาที)", gt=0)
    retention_tags: list[str] = Field(description="แท็ก retention pattern")

    # Optional fields for specific section types
    hook_pattern: str | None = Field(None, description="รูปแบบ hook")
    content_draft: str | None = Field(None, description="ร่างเนื้อหา")
    key_points: list[str] | None = Field(None, description="ประเด็นสำคัญ")
    analogy_type: str | None = Field(None, description="ประเภทของการเปรียบเทียบ")
    beat_points: list[str] | None = Field(None, description="จุดสำคัญในการเล่าเรื่อง")
    sub_segments: list[CoreTeachingSubSegment] | None = Field(
        None, description="ส่วนย่อยของการสอน"
    )
    steps: list[str] | None = Field(None, description="ขั้นตอนการปฏิบัติ")
    question: str | None = Field(None, description="คำถามสำหรับ reflection")
    cta_phrase: str | None = Field(None, description="ข้อความ call to action")
    closing_line: str | None = Field(None, description="ประโยคปิด")

    @field_validator("section")
    @classmethod
    def validate_section_name(cls, v):
        valid_sections = [
            "Hook",
            "Problem Amplify",
            "Transition Prompt",
            "Story / Analogy",
            "Core Teaching",
            "Practice / Application",
            "Reflection Question",
            "Soft CTA",
            "Calm Closing",
        ]
        if v not in valid_sections:
            raise ValueError(f"Section ต้องเป็นหนึ่งใน: {valid_sections}")
        return v


class PacingCheck(BaseModel):
    """การตรวจสอบจังหวะและเวลา"""

    total_est_seconds: int = Field(description="เวลารวมทั้งหมด (วินาที)", ge=0)
    within_range: bool = Field(description="อยู่ในช่วงเป้าหมายหรือไม่")
    target_range_seconds: list[int] = Field(description="ช่วงเป้าหมาย [min, max]")
    comment: str = Field(description="ความคิดเห็นเพิ่มเติม")

    @field_validator("target_range_seconds")
    @classmethod
    def validate_range(cls, v):
        if len(v) != 2:
            raise ValueError("target_range_seconds ต้องมี 2 ค่า [min, max]")
        if v[0] >= v[1]:
            raise ValueError("min ต้องน้อยกว่า max")
        return v


class ConceptCoverage(BaseModel):
    """การครอบคลุมแนวคิดหลัก"""

    expected: list[str] = Field(description="แนวคิดที่คาดหวัง")
    covered: list[str] = Field(description="แนวคิดที่ครอบคลุมแล้ว")
    missing: list[str] = Field(description="แนวคิดที่ขาดหายไป")
    suggest_add_in_section: str | None = Field(None, description="แนะนำส่วนที่ควรเพิ่ม")
    coverage_ratio: float = Field(description="อัตราส่วนการครอบคลุม", ge=0, le=1)


class SelfCheck(BaseModel):
    """การตรวจสอบด้วยตัวเอง"""

    time_within_tolerance: bool = Field(description="เวลาอยู่ในขอบเขตที่ยอมรับได้")
    has_core_sections: bool = Field(description="มีส่วนหลักครบ")
    no_empty_sections: bool = Field(description="ไม่มีส่วนที่ว่าง")


class MetaInfo(BaseModel):
    """ข้อมูล metadata เกี่ยวกับการสร้างโครงร่าง"""

    hook_pattern_selected: str = Field(description="รูปแบบ hook ที่เลือก")
    retention_patterns_used: list[str] = Field(description="รูปแบบ retention ที่ใช้")
    interrupt_spacing_ok: bool = Field(
        description="การจัดช่วงเวลา pattern interrupt เหมาะสม"
    )
    self_check: SelfCheck = Field(description="การตรวจสอบด้วยตัวเอง")


class ScriptOutlineInput(BaseModel):
    """Input สำหรับ ScriptOutlineAgent"""

    topic_title: str = Field(description="หัวข้อวิดีโอ")
    summary_bullets: list[str] = Field(description="สรุปประเด็นหลัก")
    core_concepts: list[str] = Field(description="แนวคิดหลัก")
    missing_concepts: list[str] = Field(
        default_factory=list, description="แนวคิดที่ขาดหายไป"
    )
    target_minutes: int = Field(description="เป้าหมายความยาว (นาที)", gt=0)
    viewer_persona: ViewerPersona = Field(description="โปรไฟล์ผู้ชม")
    style_preferences: StylePreferences = Field(description="การตั้งค่าสไตล์")
    retention_goals: RetentionGoals = Field(description="เป้าหมายการกักเก็บผู้ชม")

    @field_validator("summary_bullets")
    @classmethod
    def validate_summary_bullets(cls, v):
        if not v:
            raise ValueError("ต้องมีสรุปประเด็นอย่างน้อย 1 ข้อ")
        return v

    @field_validator("core_concepts")
    @classmethod
    def validate_core_concepts(cls, v):
        if not v:
            raise ValueError("ต้องมีแนวคิดหลักอย่างน้อย 1 ข้อ")
        return v


class ScriptOutlineOutput(BaseModel):
    """Output สำหรับ ScriptOutlineAgent"""

    topic: str = Field(description="หัวข้อวิดีโอ")
    duration_target_min: int = Field(description="เป้าหมายความยาว (นาที)", gt=0)
    outline: list[OutlineSection] = Field(description="โครงร่างทั้งหมด")
    pacing_check: PacingCheck = Field(description="การตรวจสอบจังหวะ")
    concept_coverage: ConceptCoverage = Field(description="การครอบคลุมแนวคิด")
    hook_variants: list[str] = Field(description="ตัวเลือก hook อื่นๆ")
    meta: MetaInfo = Field(description="ข้อมูล metadata")
    warnings: list[str] = Field(default_factory=list, description="คำเตือน")

    @field_validator("outline")
    @classmethod
    def validate_outline_has_hook(cls, v):
        if not v:
            raise ValueError("โครงร่างต้องมีอย่างน้อย 1 ส่วน")

        # ตรวจสอบว่ามี Hook
        hook_sections = [section for section in v if section.section == "Hook"]
        if not hook_sections:
            raise ValueError("โครงร่างต้องมีส่วน Hook")

        return v

    @field_validator("hook_variants")
    @classmethod
    def validate_hook_variants_count(cls, v):
        if len(v) < 1:
            raise ValueError("ต้องมี hook variants อย่างน้อย 1 ตัวเลือก")
        return v


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""

    error: dict[str, str | Any] = Field(description="ข้อมูลข้อผิดพลาด")

    @field_validator("error")
    @classmethod
    def validate_error_structure(cls, v):
        required_keys = ["code", "message"]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"error ต้องมี key: {key}")
        return v
