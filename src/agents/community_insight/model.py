"""Pydantic models for CommunityInsightAgent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CommunityMessage(BaseModel):
    """Single community interaction message."""

    source: str
    user_id: str
    message: str
    timestamp: datetime


class AlertKeywordConfig(BaseModel):
    """Declarative configuration for keyword-triggered alerts."""

    keyword: str
    type: str = "concern"
    message_template: str = "พบข้อความเกี่ยวกับ '{keyword}' ใน community"

    def render_message(self) -> str:
        """Render the alert message using the configured template."""

        return self.message_template.format(keyword=self.keyword)


class CommunityInsightConfig(BaseModel):
    """Configuration flags for the insight analysis."""

    min_word_count: int = Field(ge=0)
    track_influencer: list[str] = Field(default_factory=list)
    alert_keywords: list[AlertKeywordConfig] = Field(default_factory=list)

    @field_validator("alert_keywords", mode="before")
    @classmethod
    def _convert_keywords(cls, value: Any) -> list[AlertKeywordConfig]:
        """Allow shorthand string configuration for alert keywords."""

        if not value:
            return []
        if not isinstance(value, list):
            msg = f"alert_keywords must be a list, got {type(value)!r}"
            raise TypeError(msg)
        converted: list[AlertKeywordConfig] = []
        for item in value:
            if isinstance(item, AlertKeywordConfig):
                converted.append(item)
            elif isinstance(item, str):
                converted.append(AlertKeywordConfig(keyword=item))
            elif isinstance(item, dict):
                converted.append(AlertKeywordConfig(**item))
            else:
                msg = f"Unsupported alert keyword configuration: {item!r}"
                raise TypeError(msg)
        return converted


class CommunityInsightRequest(BaseModel):
    """Input payload for the CommunityInsightAgent."""

    community_data: list[CommunityMessage]
    config: CommunityInsightConfig


class RecurringTheme(BaseModel):
    theme: str
    count: int


class CommunityConcern(BaseModel):
    concern: str
    count: int


class EmergingTopic(BaseModel):
    topic: str
    reason: str


class InfluencerActivity(BaseModel):
    user_id: str
    activity: str


class AlertItem(BaseModel):
    type: str
    message: str


class MetaSelfCheck(BaseModel):
    all_sections_present: bool
    no_empty_fields: bool


class CommunityInsightMeta(BaseModel):
    message_count: int
    theme_count: int
    concern_count: int
    alert_count: int
    self_check: MetaSelfCheck


class CommunityInsightPayload(BaseModel):
    recurring_theme: list[RecurringTheme] = Field(default_factory=list)
    community_concern: list[CommunityConcern] = Field(default_factory=list)
    emerging_topic: list[EmergingTopic] = Field(default_factory=list)
    influencer_activity: list[InfluencerActivity] = Field(default_factory=list)
    alert: list[AlertItem] = Field(default_factory=list)
    insight: list[str] = Field(default_factory=list)
    actionable_recommendation: list[str] = Field(default_factory=list)
    meta: CommunityInsightMeta | None = None


class CommunityInsightResponse(BaseModel):
    community_insight: CommunityInsightPayload
