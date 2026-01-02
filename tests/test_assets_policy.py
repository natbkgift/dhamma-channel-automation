"""
เทสต์สำหรับ enforce นโยบายการจัดการ assets ในโปรเจกต์

เทสต์นี้ตรวจสอบว่านโยบายการใช้งานไฟล์ในไดเรกทอรี assets ถูกปฏิบัติตามอย่างเข้มงวด:
- ห้ามมีไฟล์ฟอนต์แบบไบนารี (.ttf, .otf, .woff, .woff2, .eot, .ttc) ใน repo
- โครงสร้างไดเรกทอรี assets ต้องตรงตามที่กำหนด
- ข้ามการตรวจสอบใน venv, site-packages และ development tool directories
- จำกัดขนาดไฟล์ placeholder และ asset โดยรวม
- ล็อก assets/fonts/ ให้มีได้เฉพาะ README.md
"""

import shutil
import subprocess
from pathlib import Path

import pytest

MAX_ASSET_BYTES = 1_000_000
MAX_PLACEHOLDER_BYTES = 10_000
ALLOWED_FONTS_DIR_FILES = {"README.md"}
FORBIDDEN_FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2", ".eot", ".ttc"}
IGNORE_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    ".tox",
    "htmlcov",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}


def _is_ignored(path: Path, repo_root: Path) -> bool:
    """
    ตรวจสอบว่าพาธที่กำหนดควรถูกข้ามการตรวจสอบหรือไม่

    Args:
        path: พาธของไฟล์หรือไดเรกทอรีที่ต้องการตรวจสอบ
        repo_root: พาธรากของ repository

    Returns:
        True ถ้าควรข้ามการตรวจสอบ, False ถ้าควรตรวจสอบ
    """
    rel = path.relative_to(repo_root)
    return any(part in IGNORE_DIR_NAMES for part in rel.parts)


def _sorted_files(root: Path) -> list[Path]:
    """
    รวบรวมไฟล์ทั้งหมดใน root แบบ recursive โดยข้ามไดเรกทอรีที่ไม่ต้องการตรวจสอบ

    Args:
        root: พาธรากที่ต้องการค้นหาไฟล์

    Returns:
        รายการไฟล์ที่เรียงลำดับแล้ว
    """
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _is_ignored(path, root):
            continue
        files.append(path)
    return sorted(files, key=str)


def _git_tracked_files(repo_root: Path) -> list[Path] | None:
    """
    ดึงรายการไฟล์ที่ถูก track โดย git ใน repository

    Args:
        repo_root: พาธรากของ repository

    Returns:
        รายการไฟล์ที่เรียงลำดับแล้ว หรือ None ถ้าไม่สามารถดึงได้
    """
    git = shutil.which("git")
    if git is None:
        return None
    if not (repo_root / ".git").exists():
        return None

    try:
        result = subprocess.run(
            [git, "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    raw = result.stdout
    paths = [
        p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\x00") if p
    ]
    return sorted((repo_root / p for p in paths), key=str)


def test_assets_policy() -> None:
    """
    ทดสอบว่านโยบายการใช้งานไฟล์ในไดเรกทอรี assets ถูกปฏิบัติตาม

    เทสต์นี้ตรวจสอบ:
    - มีไดเรกทอรี assets อยู่ในโปรเจกต์
    - ไม่มีไฟล์ฟอนต์แบบไบนารีที่นามสกุลต้องห้ามใน repo
    - โครงสร้างและไฟล์ที่จำเป็นตาม policy มีครบถ้วน
    - ไฟล์ placeholder และ asset ไม่เกินขนาดที่กำหนด
    - assets/fonts/ มีเฉพาะ README.md เท่านั้น
    """
    repo_root = Path(__file__).resolve().parents[1]
    assets_dir = repo_root / "assets"
    errors: list[tuple[str, str]] = []

    if not assets_dir.exists():
        errors.append(
            ("assets/", "assets/ directory is required by policy but is missing.")
        )

    tracked = _git_tracked_files(repo_root)
    repo_files = tracked if tracked is not None else _sorted_files(repo_root)

    for path in repo_files:
        if path.suffix.lower() in FORBIDDEN_FONT_EXTS:
            rel_posix = path.relative_to(repo_root).as_posix()
            errors.append((rel_posix, f"Forbidden font binary found: {rel_posix}"))

    if assets_dir.exists():
        required_files = [
            assets_dir / "images" / "placeholders" / "README.md",
            assets_dir / "audio" / "placeholders" / "README.md",
            assets_dir / "fonts" / "README.md",
        ]
        for required_file in required_files:
            rel_posix = required_file.relative_to(repo_root).as_posix()
            if not required_file.is_file():
                errors.append((rel_posix, f"Required asset file missing: {rel_posix}"))

        for path in _sorted_files(assets_dir):
            rel_assets = path.relative_to(assets_dir)
            rel_repo = path.relative_to(repo_root)
            rel_posix = rel_repo.as_posix()
            if ".." in rel_assets.parts:
                errors.append(
                    (rel_posix, f"Asset path traversal detected: {rel_posix}")
                )
            if (
                "placeholders" in rel_assets.parts
                and path.stat().st_size > MAX_PLACEHOLDER_BYTES
            ):
                errors.append(
                    (
                        rel_posix,
                        f"Placeholder file exceeds {MAX_PLACEHOLDER_BYTES} bytes: {rel_posix}",
                    )
                )
            if path.stat().st_size > MAX_ASSET_BYTES:
                errors.append(
                    (
                        rel_posix,
                        f"Asset file exceeds {MAX_ASSET_BYTES} bytes: {rel_posix}",
                    )
                )

        fonts_dir = assets_dir / "fonts"
        if not fonts_dir.exists():
            errors.append(
                (
                    "assets/fonts/",
                    "assets/fonts/ directory is required by policy but is missing.",
                )
            )
        else:
            if not (fonts_dir / "README.md").is_file():
                errors.append(
                    (
                        "assets/fonts/README.md",
                        "assets/fonts/ must contain README.md only.",
                    )
                )
            for entry in sorted(fonts_dir.iterdir(), key=lambda p: p.name):
                if entry.name not in ALLOWED_FONTS_DIR_FILES:
                    rel = entry.relative_to(repo_root)
                    rel_posix = rel.as_posix()
                    errors.append(
                        (
                            rel_posix,
                            f"assets/fonts/ must not contain extra entries: {rel_posix}",
                        )
                    )

    if errors:
        errors.sort(key=lambda item: item[0])
        message = "Assets policy violations:\n" + "\n".join(
            f"- {error_message}" for _, error_message in errors
        )
        pytest.fail(message)
