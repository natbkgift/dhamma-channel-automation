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

    assert set(insight.insight) == {
        "community สนใจธรรมะสำหรับวัยรุ่น",
        "community สนใจธรรมะแก้เครียด",
        "community พูดถึงปล่อยวาง",
        "ความเครียดเป็น pain point ช่วงนี้",
    }

    assert set(insight.actionable_recommendation) == {
        "จัด live Q&A แก้เครียด",
        "ทำเพลย์ลิสต์หรือรีโพสต์คลิปปล่อยวาง",
        "ผลิตคอนเทนต์สมาธิสำหรับวัยรุ่น",
    }

    meta = insight.meta
    assert meta is not None
    assert meta.message_count == 3
    assert meta.theme_count == 3
    assert meta.concern_count == 1
    assert meta.alert_count == len(insight.alert)
    assert meta.self_check.all_sections_present is True
    assert meta.self_check.no_empty_fields is True


def test_community_insight_agent_handles_empty_dataset() -> None:
    agent = CommunityInsightAgent()

    request = CommunityInsightRequest(
        community_data=[],
        config=CommunityInsightConfig(
            min_word_count=3,
            track_influencer=["U9999"],
            alert_keywords=["ลบ"],
        ),
    )

    response = agent.run(request)

    insight = response.community_insight
    assert insight.recurring_theme == []
    assert insight.community_concern == []
    assert insight.emerging_topic == []
    assert insight.influencer_activity == []
    assert insight.alert == []
    assert insight.insight == []
    assert insight.actionable_recommendation == []
    assert insight.meta is not None
    assert insight.meta.message_count == 0
    assert insight.meta.theme_count == 0
    assert insight.meta.concern_count == 0
    assert insight.meta.alert_count == 0


def test_community_insight_agent_filters_short_messages() -> None:
    agent = CommunityInsightAgent()

    request = CommunityInsightRequest(
        community_data=[
            build_message("YouTubeComment", "U1", "สู้ๆ"),
            build_message("YouTubeComment", "U2", "ปล่อยวางแล้วสบายใจ"),
        ],
        config=CommunityInsightConfig(
            min_word_count=3,
            track_influencer=[],
            alert_keywords=["เครียด"],
        ),
    )

    response = agent.run(request)

    insight = response.community_insight
    assert [item.theme for item in insight.recurring_theme] == ["ปล่อยวาง"]
    assert insight.meta is not None
    assert insight.meta.message_count == 1


def test_community_insight_agent_no_alerts_when_keywords_absent() -> None:
    agent = CommunityInsightAgent()

    request = CommunityInsightRequest(
        community_data=[
            build_message(
                "FacebookGroup",
                "U5000",
                "อยากฟังเรื่องการภาวนาในที่ทำงาน",
            )
        ],
        config=CommunityInsightConfig(
            min_word_count=1,
            track_influencer=[],
            alert_keywords=["วิกฤติ"],
        ),
    )

    response = agent.run(request)
    insight = response.community_insight

    assert insight.alert == []
    assert "วิกฤติ" not in "".join(item.theme for item in insight.recurring_theme)


def test_community_insight_agent_ignores_untracked_influencers() -> None:
    agent = CommunityInsightAgent()

    request = CommunityInsightRequest(
        community_data=[
            build_message(
                "YouTubeComment",
                "U7777",
                "อยากให้มีคอร์สสมาธิสำหรับวัยรุ่น",
            )
        ],
        config=CommunityInsightConfig(
            min_word_count=1,
            track_influencer=[],
            alert_keywords=["เครียด"],
        ),
    )

    response = agent.run(request)
    insight = response.community_insight

    assert insight.influencer_activity == []
