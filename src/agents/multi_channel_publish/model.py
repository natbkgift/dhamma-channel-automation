"""Data models for the Multi-Channel Publish agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PublishAssets(BaseModel):
    """Asset references required for publishing."""

    video: str | None = Field(None, description="Main horizontal video asset")
    vertical_video: str | None = Field(
        None, description="Vertical/short-form video asset for short platforms"
    )
    thumbnail: str | None = Field(None, description="Thumbnail image asset")


class PublishRequest(BaseModel):
    """Input payload for the multi-channel publish agent."""

    content_id: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    schedule: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping between channel name and ISO datetime schedule",
    )
    privacy: dict[str, str] = Field(
        default_factory=dict,
        description="Privacy setting per channel",
    )
    assets: PublishAssets
    channels: list[str] = Field(default_factory=list)
    extra_setting: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    def ensure_tags_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("tags ต้องเป็น list ของ string")
        return value


class MultiChannelPublishInput(BaseModel):
    """Wrapper model around publish request."""

    publish_request: PublishRequest


class ChannelPublishPayload(BaseModel):
    """Channel-specific mapped payload."""

    channel: str
    mapped_data: dict[str, Any]
    status: Literal["ready", "pending", "missing_data", "error", "published"]
    suggestion: list[str] = Field(default_factory=list)


class MultiChannelPublishLogEntry(BaseModel):
    """Logging entry describing mapping process."""

    timestamp: datetime
    event: str
    channel: str
    status: Literal["success", "warning", "failed"]
    message: str


class MultiChannelPublishOutput(BaseModel):
    """Result from the multi-channel publish agent."""

    multi_channel_publish_payload: list[ChannelPublishPayload]
    multi_channel_publish_log: list[MultiChannelPublishLogEntry]
    warnings: list[str]
    errors: list[str]
