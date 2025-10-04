"""Unit tests for CommunityInsightAgent."""

from __future__ import annotations

from datetime import datetime

from agents.community_insight import (
    CommunityInsightAgent,
    CommunityInsightConfig,
    CommunityInsightRequest,
    CommunityInsightResponse,
    CommunityMessage,
)


def build_message(source: str, user_id: str, message: str) -> CommunityMessage:
    return CommunityMessage(
        source=source,
        user_id=user_id,
        message=message,
        timestamp=datetime(2025, 9, 28, 11, 0, 0),
    )


def test_community_insight_agent_basic() -> None:
    agent = CommunityInsightAgent()

    request = CommunityInsightRequest(
        community_data=[
            build_message(
                "YouTubeComment",
                "U1001",
                "อยากให้มีคลิปสอนสมาธิสำหรับวัยรุ่น",
            ),
            build_message(
                "FacebookGroup",
                "U2002",
                "ช่วงนี้เครียดกับงาน อยากได้ธรรมะแก้เครียด",
            ),
            build_message(
                "QAPoll",
                "U3004",
                "คลิปเก่าเรื่องปล่อยวางดีมาก อยากได้อีก",
            ),
        ],
        config=CommunityInsightConfig(
            min_word_count=5,
            track_influencer=["U1001", "U3004"],
            alert_keywords=["เครียด", "วิกฤติ", "ลบ", "ขัดแย้ง"],
        ),
    )

    response = agent.run(request)
    assert isinstance(response, CommunityInsightResponse)

    insight = response.community_insight

    assert [item.theme for item in insight.recurring_theme] == [
        "สมาธิสำหรับวัยรุ่น",
        "ธรรมะแก้เครียด",
        "ปล่อยวาง",
    ]
    assert [item.count for item in insight.recurring_theme] == [1, 1, 1]

    assert [item.concern for item in insight.community_concern] == ["เครียดกับงาน"]
    assert [item.count for item in insight.community_concern] == [1]

    assert len(insight.emerging_topic) == 1
    assert insight.emerging_topic[0].topic == "Q&A วัยรุ่น"
    assert "สมาธิสำหรับวัยรุ่น" in insight.emerging_topic[0].reason

    assert [activity.user_id for activity in insight.influencer_activity] == [
        "U1001",
        "U3004",
    ]

    assert any("เครียด" in alert.message for alert in insight.alert)

    assert "community สนใจธรรมะสำหรับวัยรุ่น" in insight.insight
    assert "ความเครียดเป็น pain point ช่วงนี้" in insight.insight

    assert "ผลิตคอนเทนต์สมาธิสำหรับวัยรุ่น" in insight.actionable_recommendation
    assert "จัด live Q&A แก้เครียด" in insight.actionable_recommendation

    meta = insight.meta
    assert meta is not None
    assert meta.message_count == 3
    assert meta.theme_count == 3
    assert meta.concern_count == 1
    assert meta.alert_count == len(insight.alert)
    assert meta.self_check.all_sections_present is True
    assert meta.self_check.no_empty_fields is True
