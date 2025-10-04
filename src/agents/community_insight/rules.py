"""Utility functions for loading rule configuration for the CommunityInsightAgent."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import resources

from .model import AlertItem


@dataclass(frozen=True)
class ThemeRule:
    theme: str
    keywords: tuple[str, ...]
    insights: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConcernRule:
    concern: str
    keywords: tuple[str, ...]
    alerts: tuple[AlertItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EmergingTopicRule:
    theme: str
    topic: str
    reason: str
    trigger_keywords: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConcernResponseRule:
    keywords: tuple[str, ...]
    insights: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class InfluencerActivityRule:
    keywords: tuple[str, ...]
    activity_with_theme: str | None = None
    activity_without_theme: str | None = None


@dataclass(frozen=True)
class InfluencerActivityDefaults:
    with_theme: str
    without_theme: str


@dataclass(frozen=True)
class CommunityInsightRules:
    themes: tuple[ThemeRule, ...]
    concerns: tuple[ConcernRule, ...]
    emerging_topics: tuple[EmergingTopicRule, ...]
    default_concern_responses: tuple[ConcernResponseRule, ...]
    influencer_activity_rules: tuple[InfluencerActivityRule, ...]
    influencer_activity_defaults: InfluencerActivityDefaults


def load_rules() -> CommunityInsightRules:
    """Load rule definitions from the bundled JSON configuration file."""

    with (
        resources.files(__package__)
        .joinpath("rules.json")
        .open("r", encoding="utf-8") as fp
    ):
        raw = json.load(fp)

    def _as_tuple(items: Iterable[str]) -> tuple[str, ...]:
        return tuple(str(item) for item in items)

    themes = tuple(
        ThemeRule(
            theme=entry["theme"],
            keywords=_as_tuple(entry.get("keywords", [])),
            insights=_as_tuple(entry.get("insights", [])),
            recommendations=_as_tuple(entry.get("recommendations", [])),
        )
        for entry in raw.get("themes", [])
    )

    concerns = tuple(
        ConcernRule(
            concern=entry["concern"],
            keywords=_as_tuple(entry.get("keywords", [])),
            alerts=tuple(
                AlertItem(type=alert["type"], message=alert["message"])
                for alert in entry.get("alerts", [])
            ),
        )
        for entry in raw.get("concerns", [])
    )

    emerging_topics = tuple(
        EmergingTopicRule(
            theme=entry["theme"],
            topic=entry["topic"],
            reason=entry["reason"],
            trigger_keywords=_as_tuple(entry.get("trigger_keywords", [])),
        )
        for entry in raw.get("emerging_topics", [])
    )

    default_concern_responses = tuple(
        ConcernResponseRule(
            keywords=_as_tuple(entry.get("keywords", [])),
            insights=_as_tuple(entry.get("insights", [])),
            recommendations=_as_tuple(entry.get("recommendations", [])),
        )
        for entry in raw.get("default_concern_responses", [])
    )

    influencer_activity_data = raw.get("influencer_activity", {})
    influencer_activity_rules = tuple(
        InfluencerActivityRule(
            keywords=_as_tuple(entry.get("keywords", [])),
            activity_with_theme=entry.get("activity_with_theme"),
            activity_without_theme=entry.get("activity_without_theme"),
        )
        for entry in influencer_activity_data.get("rules", [])
    )

    defaults_data = influencer_activity_data.get("defaults", {})
    influencer_defaults = InfluencerActivityDefaults(
        with_theme=defaults_data.get("with_theme", "กระตุ้นการสนทนาเรื่อง{theme}"),
        without_theme=defaults_data.get("without_theme", "มีส่วนร่วมในบทสนทนา"),
    )

    return CommunityInsightRules(
        themes=themes,
        concerns=concerns,
        emerging_topics=emerging_topics,
        default_concern_responses=default_concern_responses,
        influencer_activity_rules=influencer_activity_rules,
        influencer_activity_defaults=influencer_defaults,
    )
