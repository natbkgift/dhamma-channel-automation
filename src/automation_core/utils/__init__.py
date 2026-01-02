"""
ฟังก์ชันช่วยเหลือต่างๆ สำหรับระบบ Automation
"""

from importlib import import_module
from types import ModuleType


def _export_public_names(module: ModuleType) -> list[str]:
    """
    ส่งออกชื่อสาธารณะทั้งหมดจากโมดูลที่ระบุมายังโมดูลนี้

    เลือกใช้ __all__ ถ้ามี; ถ้าไม่มีก็ใช้ชื่อที่ไม่ขึ้นต้นด้วย "_"
    """
    public_names = getattr(module, "__all__", None)
    if public_names is None:
        public_names = [name for name in dir(module) if not name.startswith("_")]

    exported: list[str] = []
    for name in public_names:
        globals()[name] = getattr(module, name)
        exported.append(name)
    return exported


# นำเข้าโมดูลย่อยแล้วส่งออกฟังก์ชัน/ตัวแปรสาธารณะทั้งหมด
_env_module = import_module(".env", __package__)
_scoring_module = import_module(".scoring", __package__)
_text_module = import_module(".text", __package__)

__all__: list[str] = []
__all__ += _export_public_names(_env_module)
__all__ += _export_public_names(_scoring_module)
__all__ += _export_public_names(_text_module)
