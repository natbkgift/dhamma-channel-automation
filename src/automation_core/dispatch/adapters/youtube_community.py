from __future__ import annotations

from .base import YoutubeActionAdapter


class YoutubeCommunityAdapter(YoutubeActionAdapter):
    name = "youtube_community"

    def supports(self, target: str, platform: str) -> bool:
        return target == "youtube_community" and platform == "youtube_community"
