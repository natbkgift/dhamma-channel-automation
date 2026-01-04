from __future__ import annotations

from .base import YoutubeActionAdapter


class YoutubeAdapter(YoutubeActionAdapter):
    name = "youtube"

    def supports(self, target: str, platform: str) -> bool:
        return target == "youtube" and platform == "youtube"
