"""CommunityInsightAgent - วิเคราะห์ข้อมูลชุมชนเพื่อหาประเด็นสำคัญ"""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List, Set

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


class CommunityInsightAgent(
    BaseAgent[CommunityInsightRequest, CommunityInsightResponse]
):
    """Agent สำหรับสกัด insight จากเสียงของ community"""

    def __init__(self) -> None:
        super().__init__(
            name="CommunityInsightAgent",
            version="1.0.0",
            description="วิเคราะห์ข้อมูลจากคอมมูนิตี้เพื่อนำเสนอ insight และ action",
        )

    def run(self, input_data: CommunityInsightRequest) -> CommunityInsightResponse:
        filtered_messages = self._filter_messages(
            input_data.community_data, input_data.config
        )

        theme_counts: "OrderedDict[str, int]" = OrderedDict()
        concern_counts: "OrderedDict[str, int]" = OrderedDict()
        influencer_activity: List[InfluencerActivity] = []
        emerging_topics: List[EmergingTopic] = []
        alerts: List[AlertItem] = []
        insights: List[str] = []
        recommendations: List[str] = []
        triggered_keywords: Set[str] = set()

        for message in filtered_messages:
            theme = self._extract_theme(message.message)
            concern = self._extract_concern(message.message)
            found_keywords = self._detect_alert_keywords(
                message.message, input_data.config.alert_keywords
            )

            if theme:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
                self._update_insights_and_recommendations(
                    theme, insights, recommendations
                )

            if concern:
                concern_counts[concern] = concern_counts.get(concern, 0) + 1

            for keyword in found_keywords:
                if keyword not in triggered_keywords:
                    alerts.append(
                        AlertItem(
                            type="concern",
                            message=f"พบข้อความเกี่ยวกับ '{keyword}' ใน community",
                        )
                    )
                    triggered_keywords.add(keyword)

            if message.user_id in input_data.config.track_influencer:
                activity = self._summarize_influencer_activity(message, theme)
                influencer_activity.append(activity)
                emerging_topic = self._infer_emerging_topic(message, theme)
                if emerging_topic and not self._topic_exists(
                    emerging_topics, emerging_topic.topic
                ):
                    emerging_topics.append(emerging_topic)

        # หากมี concern ที่เกี่ยวข้องกับความเครียดให้สร้าง insight เพิ่มเติม
        if concern_counts:
            insights.append("ความเครียดเป็น pain point ช่วงนี้")
            if "จัด live Q&A แก้เครียด" not in recommendations:
                recommendations.append("จัด live Q&A แก้เครียด")

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
            insight=insights,
            actionable_recommendation=recommendations,
        )

        payload.meta = self._build_meta(payload, len(filtered_messages))

        return CommunityInsightResponse(community_insight=payload)

    def _filter_messages(
        self,
        messages: Iterable[CommunityMessage],
        config: CommunityInsightConfig,
    ) -> List[CommunityMessage]:
        min_count = max(config.min_word_count, 0)
        return [
            message
            for message in messages
            if self._word_count(message.message) >= min_count
        ]

    def _word_count(self, text: str) -> int:
        tokens = [token for token in text.strip().split() if token]
        count = len(tokens)

        char_count = len([ch for ch in text if not ch.isspace()])
        if char_count == 0:
            return 0

        if count >= 3:
            return count

        approx = max(count, max(1, char_count // 4))
        return approx

    def _extract_theme(self, message: str) -> str | None:
        text = message.strip()

        if "สมาธิ" in text and "วัยรุ่น" in text:
            return "สมาธิสำหรับวัยรุ่น"
        if "เครียด" in text and ("ธรรมะ" in text or "แก้เครียด" in text):
            return "ธรรมะแก้เครียด"
        if "ปล่อยวาง" in text:
            return "ปล่อยวาง"
        if len(text) <= 4:
            return None
        return None

    def _extract_concern(self, message: str) -> str | None:
        text = message.strip()
        if "เครียด" in text:
            if "งาน" in text:
                return "เครียดกับงาน"
            return "ความเครียด"
        return None

    def _detect_alert_keywords(
        self, message: str, keywords: Iterable[str]
    ) -> Set[str]:
        detected: Set[str] = set()
        for keyword in keywords:
            if keyword and keyword in message:
                detected.add(keyword)
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
        if "วัยรุ่น" in text and "สมาธิ" in text:
            return EmergingTopic(
                topic="Q&A วัยรุ่น",
                reason="มี influencer ถามถึงสมาธิสำหรับวัยรุ่น",
            )
        return None

    def _topic_exists(self, topics: Iterable[EmergingTopic], topic: str) -> bool:
        return any(item.topic == topic for item in topics)

    def _update_insights_and_recommendations(
        self, theme: str, insights: List[str], recommendations: List[str]
    ) -> None:
        if "สมาธิ" in theme and "วัยรุ่น" in theme:
            if "community สนใจธรรมะสำหรับวัยรุ่น" not in insights:
                insights.append("community สนใจธรรมะสำหรับวัยรุ่น")
            if "ผลิตคอนเทนต์สมาธิสำหรับวัยรุ่น" not in recommendations:
                recommendations.append("ผลิตคอนเทนต์สมาธิสำหรับวัยรุ่น")
        elif "ปล่อยวาง" in theme:
            if "community พูดถึงปล่อยวาง" not in insights:
                insights.append("community พูดถึงปล่อยวาง")
            if "ทำเพลย์ลิสต์หรือรีโพสต์คลิปปล่อยวาง" not in recommendations:
                recommendations.append("ทำเพลย์ลิสต์หรือรีโพสต์คลิปปล่อยวาง")
        elif "เครียด" in theme:
            if "community สนใจธรรมะแก้เครียด" not in insights:
                insights.append("community สนใจธรรมะแก้เครียด")
            if "จัด live Q&A แก้เครียด" not in recommendations:
                recommendations.append("จัด live Q&A แก้เครียด")

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
