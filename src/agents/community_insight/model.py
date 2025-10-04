"""Pydantic models for CommunityInsightAgent."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommunityMessage(BaseModel):
    """Single community interaction message."""

    source: str
    user_id: str
    message: str
    timestamp: datetime


class CommunityInsightConfig(BaseModel):
    """Configuration flags for the insight analysis."""

    min_word_count: int = Field(ge=0)
    track_influencer: list[str] = Field(default_factory=list)
    alert_keywords: list[str] = Field(default_factory=list)


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
