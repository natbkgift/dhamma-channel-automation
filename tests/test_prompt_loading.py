"""
ทดสอบระบบโหลด Prompt Templates
"""

from pathlib import Path

import pytest

from src.automation_core.prompt_loader import (
    PromptLoadError,
    get_prompt_path,
    load_prompt,
)


class TestPromptLoading:
    """ทดสอบการโหลด prompt templates"""

    def test_load_prompt_with_valid_file(self, tmp_path):
        """ทดสอบการโหลด prompt จากไฟล์ที่ถูกต้อง"""
        # สร้างไฟล์ prompt ชั่วคราว
        prompt_file = tmp_path / "test_prompt.txt"
        prompt_content = "This is a test prompt"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        # โหลด prompt
        result = load_prompt(prompt_file)

        assert result == prompt_content

    def test_load_prompt_file_not_found(self):
        """ทดสอบการโหลด prompt จากไฟล์ที่ไม่มี"""
        non_existent_file = "non_existent_prompt.txt"

        with pytest.raises(PromptLoadError, match="ไม่พบไฟล์ prompt"):
            load_prompt(non_existent_file)

    def test_load_prompt_empty_file(self, tmp_path):
        """ทดสอบการโหลด prompt จากไฟล์ว่าง"""
        empty_file = tmp_path / "empty_prompt.txt"
        empty_file.write_text("", encoding="utf-8")

        with pytest.raises(PromptLoadError, match="ไฟล์ prompt ว่าง"):
            load_prompt(empty_file)

    def test_get_prompt_path_basic(self):
        """ทดสอบการสร้าง path สำหรับ prompt"""
        prompt_name = "test_prompt_v1.txt"
        result = get_prompt_path(prompt_name)

        assert isinstance(result, Path)
        assert result.name == prompt_name

    def test_load_prompt_with_encoding(self, tmp_path):
        """ทดสอบการโหลด prompt ด้วย encoding ที่กำหนด"""
        prompt_file = tmp_path / "thai_prompt.txt"
        thai_content = "ทดสอบข้อความภาษาไทย"
        prompt_file.write_text(thai_content, encoding="utf-8")

        result = load_prompt(prompt_file, encoding="utf-8")

        assert result == thai_content
