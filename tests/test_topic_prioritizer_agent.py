"""
Test that TopicPrioritizerAgent can be imported and instantiated
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.topic_prioritizer import (
    PriorityInput,
    PriorityOutput,
    TopicPrioritizerAgent,
)
from agents.trend_scout.model import TopicEntry, TopicScore


def test_topic_prioritizer_agent_initialization():
    """Test that TopicPrioritizerAgent can be created"""
    agent = TopicPrioritizerAgent()
    assert agent.name == "TopicPrioritizerAgent"
    assert agent.version == "1.0.0"
    assert "จัดลำดับความสำคัญ" in agent.description


def test_topic_prioritizer_basic_functionality():
    """Test basic functionality of TopicPrioritizerAgent"""
    agent = TopicPrioritizerAgent()

    # Create sample input
    sample_topic = TopicEntry(
        rank=1,
        title="ธรรมะในชีวิตประจำวัน",
        pillar="ธรรมะประยุกต์",
        predicted_14d_views=1000,
        scores=TopicScore(
            search_intent=0.8,
            freshness=0.7,
            evergreen=0.9,
            brand_fit=0.9,  # 4.5/5 ≈ 0.9
            composite=0.85,
        ),
        reason="เข้าใจง่าย เป็นประโยชน์",
        raw_keywords=["ธรรมะ", "ชีวิต"],
        similar_to=[],
        risk_flags=[],
    )

    input_data = PriorityInput(
        topics=[sample_topic],
        business_goals={"engagement": 0.8, "growth": 0.6},
        audience_segments=["คนรุ่นใหม่", "ผู้สนใจธรรมะ"],
    )

    # Run the agent
    result = agent.run(input_data)

    # Verify output
    assert isinstance(result, PriorityOutput)
    assert len(result.prioritized_topics) == 1
    assert len(result.recommendations) > 0
    assert result.prioritized_topics[0].priority_rank == 1
    assert result.prioritized_topics[0].original_topic.title == "ธรรมะในชีวิตประจำวัน"


def test_imports_work():
    """Test that all imports work correctly"""
    from agents import (
        TopicPrioritizerAgent,
        TrendScoutAgent,
    )

    # Verify all classes can be instantiated
    trend_agent = TrendScoutAgent()
    priority_agent = TopicPrioritizerAgent()

    assert trend_agent.name == "TrendScoutAgent"
    assert priority_agent.name == "TopicPrioritizerAgent"
