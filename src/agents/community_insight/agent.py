"""CommunityInsightAgent - วิเคราะห์ข้อมูลชุมชนเพื่อหาประเด็นสำคัญ"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from pythainlp import word_tokenize

from automation_core.base_agent import BaseAgent

from .model import (
    AlertItem,
    CommunityConcern,
    CommunityInsightConfig,
    CommunityInsightMeta,
    CommunityInsightPayload,
    CommunityInsightRequest,
    CommunityInsightResponse,
    CommunityMessage,
    EmergingTopic,
    InfluencerActivity,
    MetaSelfCheck,
    RecurringTheme,
)
from .rules import CommunityInsightRules, ConcernRule, ThemeRule, load_rules


class CommunityInsightAgent(
    BaseAgent[CommunityInsightRequest, CommunityInsightResponse]
):
    """Agent สำหรับสกัด insight จากเสียงของ community"""

    def __init__(self, rules: CommunityInsightRules | None = None) -> None:
        super().__init__(
            name="CommunityInsightAgent",
            version="1.1.0",
            description="วิเคราะห์ข้อมูลจากคอมมูนิตี้เพื่อนำเสนอ insight และ action",
        )
        self._rules = rules or load_rules()

    def run(self, input_data: CommunityInsightRequest) -> CommunityInsightResponse:
        filtered_messages = self._filter_messages(
            input_data.community_data, input_data.config
        )

        theme_counts: OrderedDict[str, int] = OrderedDict()
        concern_counts: OrderedDict[str, int] = OrderedDict()
        influencer_activity: list[InfluencerActivity] = []
        emerging_topics: list[EmergingTopic] = []
        alerts: list[AlertItem] = []
        insights: set[str] = set()
        recommendations: set[str] = set()
        triggered_alert_messages: set[str] = set()

        for message in filtered_messages:
            theme_rule = self._match_theme(message.message)
            concern_rule = self._match_concern(message.message)
            keyword_alerts = self._detect_alert_keywords(
                message.message, input_data.config.alert_keywords
            )

            if theme_rule:
                theme_counts[theme_rule.theme] = (
                    theme_counts.get(theme_rule.theme, 0) + 1
                )
                insights.update(theme_rule.insights)
                recommendations.update(theme_rule.recommendations)

            if concern_rule:
                concern_counts[concern_rule.concern] = (
                    concern_counts.get(concern_rule.concern, 0) + 1
                )
                for alert in concern_rule.alerts:
                    if alert.message not in triggered_alert_messages:
                        alerts.append(alert)
                        triggered_alert_messages.add(alert.message)

            for alert_message in keyword_alerts:
                if alert_message not in triggered_alert_messages:
                    alerts.append(
                        AlertItem(
                            type="concern",
                            message=alert_message,
                        )
                    )
                    triggered_alert_messages.add(alert_message)

            if message.user_id in input_data.config.track_influencer:
                activity = self._summarize_influencer_activity(
                    message, theme_rule.theme if theme_rule else None
                )
                influencer_activity.append(activity)
                emerging_topic = self._infer_emerging_topic(
                    message, theme_rule.theme if theme_rule else None
                )
                if emerging_topic and not self._topic_exists(
                    emerging_topics, emerging_topic.topic
                ):
                    emerging_topics.append(emerging_topic)

            self._update_default_concern_responses(
                message.message, insights, recommendations
            )

        payload = CommunityInsightPayload(
            recurring_theme=[
                RecurringTheme(theme=theme, count=count)
                for theme, count in theme_counts.items()
            ],
            community_concern=[
                CommunityConcern(concern=concern, count=count)
                for concern, count in concern_counts.items()
            ],
            emerging_topic=emerging_topics,
            influencer_activity=influencer_activity,
            alert=alerts,
            insight=sorted(insights),
            actionable_recommendation=sorted(recommendations),
        )

        payload.meta = self._build_meta(payload, len(filtered_messages))

        return CommunityInsightResponse(community_insight=payload)

    def _filter_messages(
        self,
        messages: Iterable[CommunityMessage],
        config: CommunityInsightConfig,
    ) -> list[CommunityMessage]:
        min_count = max(config.min_word_count, 0)
        return [
            message
            for message in messages
            if self._word_count(message.message) >= min_count
        ]

    def _word_count(self, text: str) -> int:
        """Count words using Thai word tokenisation for higher accuracy."""

        tokens = [
            token
            for token in word_tokenize(text, engine="newmm")
            if token.strip()
        ]
        return len(tokens)

    def _match_theme(self, message: str) -> ThemeRule | None:
        text = message.strip()
        for rule in self._rules.themes:
            if all(keyword in text for keyword in rule.keywords):
                return rule
        return None

    def _match_concern(self, message: str) -> ConcernRule | None:
        text = message.strip()
        for rule in self._rules.concerns:
            if all(keyword in text for keyword in rule.keywords):
                return rule
        return None

    def _detect_alert_keywords(
        self, message: str, keywords: Iterable[str]
    ) -> set[str]:
        detected = set()
        for keyword in keywords:
            if keyword and keyword in message:
                detected.add(f"พบข้อความเกี่ยวกับ '{keyword}' ใน community")
        return detected

    def _summarize_influencer_activity(
        self, message: CommunityMessage, theme: str | None
    ) -> InfluencerActivity:
        text = message.message
        if "ดีมาก" in text and "อยากได้อีก" in text and theme:
            activity = "รีวิวคลิปปล่อยวาง, กระตุ้นความสนใจ"
        elif "อยาก" in text and theme:
            activity = f"เสนอหัวข้อ{theme}"
        elif theme:
            activity = f"กระตุ้นการสนทนาเรื่อง{theme}"
        else:
            activity = "มีส่วนร่วมในบทสนทนา"
        return InfluencerActivity(user_id=message.user_id, activity=activity)

    def _infer_emerging_topic(
        self, message: CommunityMessage, theme: str | None
    ) -> EmergingTopic | None:
        if not theme:
            return None
        text = message.message
        for rule in self._rules.emerging_topics:
            if rule.theme == theme and all(
                keyword in text for keyword in rule.trigger_keywords
            ):
                return EmergingTopic(topic=rule.topic, reason=rule.reason)
        return None

    def _topic_exists(self, topics: Iterable[EmergingTopic], topic: str) -> bool:
        return any(item.topic == topic for item in topics)

    def _update_default_concern_responses(
        self, message: str, insights: set[str], recommendations: set[str]
    ) -> None:
        text = message.strip()
        for rule in self._rules.default_concern_responses:
            if all(keyword in text for keyword in rule.keywords):
                insights.update(rule.insights)
                recommendations.update(rule.recommendations)

    def _build_meta(
        self, payload: CommunityInsightPayload, message_count: int
    ) -> CommunityInsightMeta:
        fields = [
            payload.recurring_theme,
            payload.community_concern,
            payload.emerging_topic,
            payload.influencer_activity,
            payload.alert,
            payload.insight,
            payload.actionable_recommendation,
        ]
        all_sections_present = all(field is not None for field in fields)
        no_empty_fields = all(len(field) > 0 for field in fields if isinstance(field, list))

        return CommunityInsightMeta(
            message_count=message_count,
            theme_count=len(payload.recurring_theme),
            concern_count=len(payload.community_concern),
            alert_count=len(payload.alert),
            self_check=MetaSelfCheck(
                all_sections_present=all_sections_present,
                no_empty_fields=no_empty_fields,
            ),
        )
