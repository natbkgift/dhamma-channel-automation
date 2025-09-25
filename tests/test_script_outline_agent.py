"""
Test cases สำหรับ ScriptOutlineAgent
ทดสอบการทำงานของ Agent ในการสร้างโครงร่างวิดีโอ
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.script_outline import (
    RetentionGoals,
    ScriptOutlineAgent,
    ScriptOutlineInput,
    ScriptOutlineOutput,
    StylePreferences,
    ViewerPersona,
)


class TestScriptOutlineAgent:
    """Test cases สำหรับ ScriptOutlineAgent"""

    def setup_method(self):
        """Setup สำหรับแต่ละ test"""
        self.agent = ScriptOutlineAgent()

    def test_agent_initialization(self):
        """ทดสอบการสร้าง agent"""
        assert self.agent.name == "ScriptOutlineAgent"
        assert self.agent.version == "1.0.0"
        assert "โครงร่างวิดีโอ" in self.agent.description

    def test_run_basic_functionality(self):
        """ทดสอบการทำงานพื้นฐานของ agent"""
        input_data = ScriptOutlineInput(
            topic_title="ปล่อยวางความกังวลก่อนนอน",
            summary_bullets=[
                "การสังเกตเวทนาโดยไม่ยึดช่วยคลายกังวล",
                "อานาปานสติช่วงสั้นก่อนหลับลดการวนคิด",
                "การยอมรับความไม่แน่นอนทำให้ใจคลาย",
            ],
            core_concepts=["สติ", "เวทนา", "ปล่อยวาง", "อานาปานสติ"],
            missing_concepts=["เมตตา"],
            target_minutes=10,
            viewer_persona=ViewerPersona(
                name="คนทำงานเมือง",
                pain_points=["นอนไม่ค่อยหลับ", "คิดเรื่องงานซ้ำ", "กังวลอนาคต"],
                desired_state="ใจผ่อนคลาย หลับง่ายขึ้น",
            ),
            style_preferences=StylePreferences(
                tone="อบอุ่น สงบ ไม่สั่งสอน", avoid=["ศัพท์บาลีหนักเกินไปติดๆกัน", "การตำหนิตัวผู้ชม"]
            ),
            retention_goals=RetentionGoals(
                hook_drop_max_pct=30, mid_segment_break_every_sec=120
            ),
        )

        result = self.agent.run(input_data)

        # ตรวจสอบประเภทผลลัพธ์
        assert isinstance(result, ScriptOutlineOutput)
        assert result.topic == input_data.topic_title
        assert result.duration_target_min == input_data.target_minutes

    def test_outline_structure_requirements(self):
        """ทดสอบโครงสร้างของโครงร่างที่ต้องมี"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # ตรวจสอบว่ามีส่วนสำคัญครบ
        section_names = [section.section for section in result.outline]

        # ต้องมี Hook
        assert "Hook" in section_names

        # ต้องมี Core Teaching
        assert "Core Teaching" in section_names

        # ต้องมี Practice / Application
        assert "Practice / Application" in section_names

        # Hook ต้องเป็นส่วนแรก
        assert result.outline[0].section == "Hook"

    def test_hook_section_requirements(self):
        """ทดสอบข้อกำหนดของส่วน Hook"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        hook_section = next(s for s in result.outline if s.section == "Hook")

        # ต้องมี hook_pattern
        assert hook_section.hook_pattern is not None
        assert hook_section.hook_pattern in self.agent.hook_patterns

        # เวลาต้องไม่เกิน 8 วินาที
        assert hook_section.est_seconds <= 8

        # ต้องมี content_draft
        assert hook_section.content_draft is not None
        assert len(hook_section.content_draft.split()) <= 25  # ไม่เกิน 25 คำ

    def test_core_teaching_structure(self):
        """ทดสอบโครงสร้างของส่วน Core Teaching"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        core_section = next(s for s in result.outline if s.section == "Core Teaching")

        # ต้องมี sub_segments
        assert core_section.sub_segments is not None
        assert len(core_section.sub_segments) >= 1

        # แต่ละ sub_segment ต้องมีข้อมูลครบ
        for sub_segment in core_section.sub_segments:
            assert sub_segment.label
            assert sub_segment.est_seconds > 0
            assert sub_segment.teaching_points
            assert sub_segment.concept_links
            assert sub_segment.citation_placeholders

    def test_pacing_calculation(self):
        """ทดสอบการคำนวณเวลาและจังหวะ"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # ตรวจสอบการคำนวณเวลารวม
        manual_total = sum(section.est_seconds for section in result.outline)
        assert result.pacing_check.total_est_seconds == manual_total

        # ตรวจสอบ target range
        target_seconds = input_data.target_minutes * 60
        assert result.pacing_check.target_range_seconds[0] < target_seconds
        assert result.pacing_check.target_range_seconds[1] > target_seconds

    def test_concept_coverage_tracking(self):
        """ทดสอบการติดตามการครอบคลุมแนวคิด"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # ตรวจสอบว่ามีการติดตามแนวคิด
        coverage = result.concept_coverage

        assert coverage.expected
        assert coverage.covered
        assert 0 <= coverage.coverage_ratio <= 1

        # expected ต้องรวมทั้ง core_concepts และ missing_concepts
        expected_total = len(input_data.core_concepts) + len(
            input_data.missing_concepts
        )
        assert len(coverage.expected) == expected_total

    def test_retention_patterns_usage(self):
        """ทดสอบการใช้ retention patterns"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # รวบรวม retention patterns ที่ใช้ทั้งหมด
        all_patterns = set()
        for section in result.outline:
            all_patterns.update(section.retention_tags)

        # ต้องใช้อย่างน้อย 4 แบบ
        assert len(all_patterns) >= 4

        # ต้องมีใน metadata
        assert result.meta.retention_patterns_used
        assert set(result.meta.retention_patterns_used) == all_patterns

    def test_hook_variants_generation(self):
        """ทดสอบการสร้าง hook variants"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # ต้องมี hook variants อย่างน้อย 1 ตัว
        assert len(result.hook_variants) >= 1

        # hook variants ต้องแตกต่างจาก hook หลัก
        main_hook = next(s for s in result.outline if s.section == "Hook").content_draft
        for variant in result.hook_variants:
            assert variant != main_hook

    def test_warnings_generation(self):
        """ทดสอบการสร้างคำเตือน"""
        # สร้าง input ที่มีปัญหาเพื่อทดสอบ warnings
        input_data = ScriptOutlineInput(
            topic_title="หัวข้อทดสอบ",
            summary_bullets=["สรุปทดสอบ"],
            core_concepts=["สติ"],
            missing_concepts=["เมตตา", "กรุณา"],  # มีแนวคิดที่ขาดหาย
            target_minutes=5,  # เวลาสั้นเกินไป
            viewer_persona=ViewerPersona(
                name="ผู้ทดสอบ", pain_points=["ปัญหาทดสอบ"], desired_state="สถานะทดสอบ"
            ),
            style_preferences=StylePreferences(tone="ทดสอบ", avoid=[]),
            retention_goals=RetentionGoals(
                hook_drop_max_pct=30, mid_segment_break_every_sec=120
            ),
        )

        result = self.agent.run(input_data)

        # ควรมี warnings เกี่ยวกับ missing concepts
        assert result.warnings
        missing_warnings = [w for w in result.warnings if "missing concept" in w]
        assert len(missing_warnings) >= 1

    def test_different_topics_produce_different_outlines(self):
        """ทดสอบว่าหัวข้อต่างกันให้ผลลัพธ์ที่แตกต่าง"""
        # หัวข้อที่ 1
        input1 = self._create_sample_input()
        input1.topic_title = "ปล่อยวางความกังวล"

        # หัวข้อที่ 2
        input2 = self._create_sample_input()
        input2.topic_title = "พัฒนาสมาธิเบื้องต้น"

        result1 = self.agent.run(input1)
        result2 = self.agent.run(input2)

        # Hook pattern อาจแตกต่างกัน (ขึ้นกับ hash)
        hook1 = next(s for s in result1.outline if s.section == "Hook")
        hook2 = next(s for s in result2.outline if s.section == "Hook")

        # อย่างน้อยเนื้อหา hook ต้องแตกต่าง
        assert hook1.content_draft != hook2.content_draft

    def test_sleep_topic_includes_closing(self):
        """ทดสอบว่าหัวข้อเกี่ยวกับการนอนมี Calm Closing"""
        input_data = self._create_sample_input()
        input_data.topic_title = "ปล่อยวางความกังวลก่อนนอน"  # มีคำ "นอน"

        result = self.agent.run(input_data)

        section_names = [section.section for section in result.outline]
        assert "Calm Closing" in section_names

    def test_meta_info_completeness(self):
        """ทดสอบความครบถ้วนของ metadata"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        meta = result.meta

        # ตรวจสอบฟิลด์สำคัญ
        assert meta.hook_pattern_selected
        assert meta.retention_patterns_used
        assert isinstance(meta.interrupt_spacing_ok, bool)

        # ตรวจสอบ self_check
        assert hasattr(meta.self_check, "time_within_tolerance")
        assert hasattr(meta.self_check, "has_core_sections")
        assert hasattr(meta.self_check, "no_empty_sections")

    def test_practice_steps_generation(self):
        """ทดสอบการสร้างขั้นตอนการปฏิบัติ"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        practice_section = next(
            s for s in result.outline if s.section == "Practice / Application"
        )

        # ต้องมีขั้นตอน
        assert practice_section.steps
        assert len(practice_section.steps) >= 3

        # ขั้นตอนต้องเป็น string
        for step in practice_section.steps:
            assert isinstance(step, str)
            assert len(step.strip()) > 0

    def test_input_validation(self):
        """ทดสอบการ validate input"""
        # ทดสอบ input ที่ไม่ถูกต้อง
        with pytest.raises(ValueError):
            # ไม่มี summary_bullets
            ScriptOutlineInput(
                topic_title="หัวข้อทดสอบ",
                summary_bullets=[],
                core_concepts=["สติ"],
                target_minutes=10,
                viewer_persona=ViewerPersona(
                    name="ทดสอบ", pain_points=["ปัญหา"], desired_state="สถานะ"
                ),
                style_preferences=StylePreferences(tone="ทดสอบ", avoid=[]),
                retention_goals=RetentionGoals(
                    hook_drop_max_pct=30, mid_segment_break_every_sec=120
                ),
            )

    def test_output_validation(self):
        """ทดสอบการ validate output"""
        input_data = self._create_sample_input()
        result = self.agent.run(input_data)

        # ตรวจสอบว่าผลลัพธ์ผ่าน validation
        assert isinstance(result, ScriptOutlineOutput)

        # ตรวจสอบว่ามี Hook
        hook_sections = [s for s in result.outline if s.section == "Hook"]
        assert len(hook_sections) == 1

    def test_deterministic_behavior(self):
        """ทดสอบว่าผลลัพธ์สม่ำเสมอสำหรับ input เดียวกัน"""
        input_data = self._create_sample_input()

        result1 = self.agent.run(input_data)
        result2 = self.agent.run(input_data)

        # ผลลัพธ์ควรเหมือนกัน (deterministic)
        assert result1.topic == result2.topic
        assert len(result1.outline) == len(result2.outline)

        # Hook pattern ควรเหมือนกัน
        hook1 = next(s for s in result1.outline if s.section == "Hook")
        hook2 = next(s for s in result2.outline if s.section == "Hook")
        assert hook1.hook_pattern == hook2.hook_pattern

    def _create_sample_input(self) -> ScriptOutlineInput:
        """สร้าง sample input สำหรับทดสอบ"""
        return ScriptOutlineInput(
            topic_title="ปล่อยวางความกังวลก่อนนอน",
            summary_bullets=[
                "การสังเกตเวทนาโดยไม่ยึดช่วยคลายกังวล",
                "อานาปานสติช่วงสั้นก่อนหลับลดการวนคิด",
                "การยอมรับความไม่แน่นอนทำให้ใจคลาย",
            ],
            core_concepts=["สติ", "เวทนา", "ปล่อยวาง", "อานาปานสติ"],
            missing_concepts=["เมตตา"],
            target_minutes=10,
            viewer_persona=ViewerPersona(
                name="คนทำงานเมือง",
                pain_points=["นอนไม่ค่อยหลับ", "คิดเรื่องงานซ้ำ", "กังวลอนาคต"],
                desired_state="ใจผ่อนคลาย หลับง่ายขึ้น",
            ),
            style_preferences=StylePreferences(
                tone="อบอุ่น สงบ ไม่สั่งสอน", avoid=["ศัพท์บาลีหนักเกินไปติดๆกัน", "การตำหนิตัวผู้ชม"]
            ),
            retention_goals=RetentionGoals(
                hook_drop_max_pct=30, mid_segment_break_every_sec=120
            ),
        )
