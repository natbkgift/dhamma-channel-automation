"""Pydantic models for CommunityInsightAgent."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

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
    track_influencer: List[str] = Field(default_factory=list)
    alert_keywords: List[str] = Field(default_factory=list)


class CommunityInsightRequest(BaseModel):
    """Input payload for the CommunityInsightAgent."""

    community_data: List[CommunityMessage]
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
    recurring_theme: List[RecurringTheme] = Field(default_factory=list)
    community_concern: List[CommunityConcern] = Field(default_factory=list)
    emerging_topic: List[EmergingTopic] = Field(default_factory=list)
    influencer_activity: List[InfluencerActivity] = Field(default_factory=list)
    alert: List[AlertItem] = Field(default_factory=list)
    insight: List[str] = Field(default_factory=list)
    actionable_recommendation: List[str] = Field(default_factory=list)
    meta: Optional[CommunityInsightMeta] = None


class CommunityInsightResponse(BaseModel):
    community_insight: CommunityInsightPayload
