from __future__ import annotations

from typing import Any, Protocol


class DispatchAdapter(Protocol):
    """Protocol สำหรับ adapter ที่สร้าง dispatch actions."""

    name: str

    def supports(self, target: str, platform: str) -> bool:
        """ระบุว่า adapter รองรับคู่ (target, platform) หรือไม่.

        คืนค่า True เมื่อ adapter รองรับ target/platform ที่ระบุ เพื่อให้ registry
        เลือก adapter ที่เหมาะสมที่สุด.
        """

    def build_actions(
        self,
        *,
        short_bytes: int,
        long_bytes: int,
        publish_reason: str,
        target: str,
    ) -> list[dict[str, Any]]:
        """สร้างรายการ action สำหรับ dispatch.

        action ต้องเป็น list ของ dict โดยมี key สำคัญ เช่น:
        - type: "print" หรือ "noop"
        - label: "short", "long", หรือ "publish"
        - bytes: จำนวน bytes ที่จะใช้ (กรณี type="print")
        - reason: เหตุผลในการ publish (กรณี type="noop")
        - adapter: ชื่อ adapter ที่สร้าง action
        - target: เป้าหมายที่เกี่ยวข้องกับ action

        หาก short_bytes หรือ long_bytes เป็นค่าติดลบ ให้ปรับเป็น 0 ก่อนใช้งาน
        เพื่อรักษาสัญญาว่าค่า bytes ต้องไม่ติดลบ.
        """


class YoutubeActionAdapter:
    """Base class ที่แชร์ logic build_actions สำหรับ YouTube adapters."""

    name: str

    def build_actions(
        self,
        *,
        short_bytes: int,
        long_bytes: int,
        publish_reason: str,
        target: str,
    ) -> list[dict[str, Any]]:
        short_b = short_bytes if short_bytes >= 0 else 0
        long_b = long_bytes if long_bytes >= 0 else 0
        return [
            {
                "type": "print",
                "label": "short",
                "bytes": short_b,
                "adapter": self.name,
                "target": target,
            },
            {
                "type": "print",
                "label": "long",
                "bytes": long_b,
                "adapter": self.name,
                "target": target,
            },
            {
                "type": "noop",
                "label": "publish",
                "reason": publish_reason,
                "adapter": self.name,
                "target": target,
            },
        ]
