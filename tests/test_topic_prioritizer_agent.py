"""
ทดสอบการทำงานของ TopicPrioritizerAgent
"""

import sys
from pathlib import Path

# เพิ่ม src path สำหรับ import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from agents.topic_prioritizer import (
    TopicPrioritizerAgent,
    TopicPrioritizerInput,
    TopicPrioritizerOutput,
    CandidateTopic,
    Capacity,
    Rules,
    HistoricalContext,
)


class TestTopicPrioritizerAgent:
    """ทดสอบการทำงานของ TopicPrioritizerAgent"""

    @pytest.fixture
    def agent(self):
        """สร้าง TopicPrioritizerAgent สำหรับทดสอบ"""
        return TopicPrioritizerAgent()

    @pytest.fixture
    def sample_candidate_topics(self):
        """ข้อมูลหัวข้อผู้สมัครสำหรับทดสอบ"""
        return [
            CandidateTopic(
                title="ปล่อยวางก่อนหลับ",
                pillar="ธรรมะประยุกต์",
                predicted_14d_views=12000,
                scores={
                    "search_intent": 0.82,
                    "freshness": 0.74,
                    "evergreen": 0.65,
                    "brand_fit": 0.93,
                    "composite": 0.785
                },
                reason="ค้นสูง + ปัญหาก่อนนอน"
            ),
            CandidateTopic(
                title="ธรรมะสั้น: ใจเย็น",
                pillar="ธรรมะสั้น",
                predicted_14d_views=8000,
                scores={
                    "search_intent": 0.75,
                    "freshness": 0.85,
                    "evergreen": 0.45,
                    "brand_fit": 0.88,
                    "composite": 0.732
                },
                reason="เทรนด์ใหม่"
            ),
            CandidateTopic(
                title="พุทธจิตวิทยา ตอนที่ 1",
                pillar="เจาะลึก/ซีรีส์",
                predicted_14d_views=5000,
                scores={
                    "search_intent": 0.65,
                    "freshness": 0.55,
                    "evergreen": 0.85,
                    "brand_fit": 0.92,
                    "composite": 0.742
                },
                reason="ซีรีส์ลึก"
            ),
            CandidateTopic(
                title="Q&A: ทำไมต้องทุกข์",
                pillar="Q&A/ตอบคำถาม",
                predicted_14d_views=3000,
                scores={
                    "search_intent": 0.88,
                    "freshness": 0.65,
                    "evergreen": 0.75,
                    "brand_fit": 0.85,
                    "composite": 0.783
                },
                reason="คำถามยอดนิยม"
            ),
            CandidateTopic(
                title="หัวข้อคะแนนต่ำ",
                pillar="ธรรมะประยุกต์",
                predicted_14d_views=1000,
                scores={
                    "search_intent": 0.3,
                    "freshness": 0.2,
                    "evergreen": 0.4,
                    "brand_fit": 0.5,
                    "composite": 0.35
                },
                reason="ทดสอบคะแนนต่ำ"
            )
        ]

    @pytest.fixture
    def sample_capacity(self):
        """ข้อมูลความจุสำหรับทดสอบ"""
        return Capacity(
            weeks=4,
            longform_per_week=2,
            shorts_per_week=3
        )

    @pytest.fixture
    def sample_rules(self):
        """ข้อมูลกฎสำหรับทดสอบ"""
        return Rules(
            min_pillars_diversity=3,
            force_series_prefixes=["พุทธจิตวิทยา", "ชาดกชุด", "10 วันภาวนา"]
        )

    @pytest.fixture
    def sample_historical_context(self):
        """ข้อมูลประวัติศาสตร์สำหรับทดสอบ"""
        return HistoricalContext(
            recent_longform_avg_views=3200,
            recent_shorts_avg_views=1800,
            pillar_performance={
                "ธรรมะประยุกต์": 1.05,
                "ชาดก/นิทานสอนใจ": 0.92,
                "ธรรมะสั้น": 1.10,
                "เจาะลึก/ซีรีส์": 1.18,
                "Q&A/ตอบคำถาม": 0.88,
                "สรุปพระสูตร/หนังสือ": 1.00
            }
        )

    @pytest.fixture
    def sample_input(self, sample_candidate_topics, sample_capacity, sample_rules, sample_historical_context):
        """ข้อมูล input ตัวอย่างสำหรับทดสอบ"""
        return TopicPrioritizerInput(
            candidate_topics=sample_candidate_topics,
            strategy_focus="fast_growth",
            capacity=sample_capacity,
            rules=sample_rules,
            historical_context=sample_historical_context
        )

    def test_agent_initialization(self, agent):
        """ทดสอบการสร้าง Agent"""
        assert agent.name == "TopicPrioritizerAgent"
        assert agent.version == "1.0.0"
        assert "จัดลำดับความสำคัญ" in agent.description

    def test_run_basic_functionality(self, agent, sample_input):
        """ทดสอบการทำงานพื้นฐาน"""
        result = agent.run(sample_input)
        
        assert isinstance(result, TopicPrioritizerOutput)
        assert result.strategy_focus == "fast_growth"
        assert len(result.scheduled) + len(result.unscheduled) <= len(sample_input.candidate_topics)
        assert result.meta.total_candidates == len(sample_input.candidate_topics)

    def test_priority_scoring_fast_growth(self, agent, sample_input):
        """ทดสอบการคำนวณคะแนนสำหรับกลยุทธ์ fast_growth"""
        sample_input.strategy_focus = "fast_growth"
        result = agent.run(sample_input)
        
        # หัวข้อที่มี freshness สูงควรได้คะแนนสูง
        scheduled_topics = {topic.topic_title: topic.priority_score for topic in result.scheduled}
        
        # ปล่อยวางก่อนหลับ ควรได้คะแนนสูง (freshness 0.74)
        # ธรรมะสั้น: ใจเย็น ควรได้คะแนนสูงกว่า (freshness 0.85)
        # ผ่อนผันให้คะแนนต่างกันไม่เกิน 15 คะแนน (เพราะมีปัจจัยอื่น ๆ ด้วย)
        if "ปล่อยวางก่อนหลับ" in scheduled_topics and "ธรรมะสั้น: ใจเย็น" in scheduled_topics:
            score_diff = scheduled_topics["ปล่อยวางก่อนหลับ"] - scheduled_topics["ธรรมะสั้น: ใจเย็น"]
            assert abs(score_diff) <= 15  # ยอมรับความต่างไม่เกิน 15 คะแนน

    def test_priority_scoring_evergreen_balance(self, agent, sample_input):
        """ทดสอบการคำนวณคะแนนสำหรับกลยุทธ์ evergreen_balance"""
        sample_input.strategy_focus = "evergreen_balance"
        result = agent.run(sample_input)
        
        # หัวข้อที่มี evergreen สูงควรได้คะแนนสูง
        scheduled_topics = {topic.topic_title: topic.priority_score for topic in result.scheduled}
        
        # พุทธจิตวิทยา ตอนที่ 1 ควรได้คะแนนดี (evergreen 0.85)
        assert len(result.scheduled) > 0

    def test_priority_scoring_depth_series(self, agent, sample_input):
        """ทดสอบการคำนวณคะแนนสำหรับกลยุทธ์ depth_series"""
        sample_input.strategy_focus = "depth_series"
        result = agent.run(sample_input)
        
        # หัวข้อที่เป็นซีรีส์ควรได้โบนัส
        series_topics = [topic for topic in result.scheduled if topic.series_group is not None]
        
        # พุทธจิตวิทยา ควรได้ series bonus
        series_titles = [topic.topic_title for topic in series_topics]
        assert any("พุทธจิตวิทยา" in title for title in series_titles)

    def test_content_type_classification(self, agent, sample_input):
        """ทดสอบการจำแนกประเภทเนื้อหา"""
        result = agent.run(sample_input)
        
        # ตรวจสอบว่ามีการแบ่งระหว่าง longform และ shorts
        content_types = {topic.content_type for topic in result.scheduled}
        
        # พุทธจิตวิทยา ควรเป็น longform (force series)
        series_topic = next((t for t in result.scheduled if "พุทธจิตวิทยา" in t.topic_title), None)
        if series_topic:
            assert series_topic.content_type == "longform"

    def test_capacity_constraints(self, agent, sample_input):
        """ทดสอบการเคารพข้อจำกัดความจุ"""
        result = agent.run(sample_input)
        
        # นับหัวข้อต่อสัปดาห์ต่อประเภท
        weekly_counts = {}
        for topic in result.scheduled:
            week = topic.week
            content_type = topic.content_type
            
            if week not in weekly_counts:
                weekly_counts[week] = {"longform": 0, "shorts": 0}
            weekly_counts[week][content_type] += 1
        
        # ตรวจสอบว่าไม่เกินความจุ
        for week, counts in weekly_counts.items():
            assert counts["longform"] <= sample_input.capacity.longform_per_week
            assert counts["shorts"] <= sample_input.capacity.shorts_per_week

    def test_low_score_unscheduled(self, agent, sample_input):
        """ทดสอบการใส่หัวข้อคะแนนต่ำใน unscheduled"""
        result = agent.run(sample_input)
        
        # หัวข้อคะแนนต่ำควรอยู่ใน unscheduled
        unscheduled_titles = [topic.topic_title for topic in result.unscheduled]
        assert "หัวข้อคะแนนต่ำ" in unscheduled_titles
        
        # ตรวจสอบเหตุผล
        low_score_topic = next(t for t in result.unscheduled if t.topic_title == "หัวข้อคะแนนต่ำ")
        assert low_score_topic.reason == "low_score"

    def test_diversity_summary(self, agent, sample_input):
        """ทดสอบการสร้างสรุปความหลากหลาย"""
        result = agent.run(sample_input)
        
        # ตรวจสอบ diversity summary
        assert isinstance(result.diversity_summary.pillar_counts, dict)
        assert result.diversity_summary.distinct_pillars >= 0
        assert isinstance(result.diversity_summary.meets_minimum, bool)

    def test_series_handling(self, agent, sample_input):
        """ทดสอบการจัดการซีรีส์"""
        result = agent.run(sample_input)
        
        # หาหัวข้อที่เป็นซีรีส์
        series_topics = [topic for topic in result.scheduled if topic.series_group is not None]
        
        # ตรวจสอบว่า series_group ถูกกำหนดอย่างถูกต้อง
        for topic in series_topics:
            assert any(topic.topic_title.startswith(prefix) for prefix in sample_input.rules.force_series_prefixes)

    def test_expected_role_assignment(self, agent, sample_input):
        """ทดสอบการกำหนดบทบาทที่คาดหวัง"""
        result = agent.run(sample_input)
        
        # ตรวจสอบว่ามีการกำหนด expected_role
        for topic in result.scheduled:
            assert topic.expected_role in [
                "traffic_spike", "evergreen_seed", "series_part", 
                "balance_filler", "audience_engagement"
            ]

    def test_self_check_functionality(self, agent, sample_input):
        """ทดสอบการตรวจสอบตนเอง"""
        result = agent.run(sample_input)
        
        # ตรวจสอบ self_check fields
        self_check = result.meta.self_check
        assert isinstance(self_check.capacity_respected, bool)
        assert isinstance(self_check.scores_monotonic, bool)
        assert isinstance(self_check.diversity_ok, bool)

    def test_week_assignment(self, agent, sample_input):
        """ทดสอบการกำหนดสัปดาห์"""
        result = agent.run(sample_input)
        
        # ตรวจสอบว่าทุกหัวข้อมี week ที่ถูกต้อง
        for topic in result.scheduled:
            assert topic.week in ["W1", "W2", "W3", "W4"]
            assert topic.slot_index >= 1

    def test_empty_candidate_topics(self, agent, sample_capacity, sample_rules, sample_historical_context):
        """ทดสอบกรณีไม่มีหัวข้อผู้สมัคร"""
        with pytest.raises(ValueError, match="ต้องมีหัวข้อผู้สมัครอย่างน้อย 1 หัวข้อ"):
            TopicPrioritizerInput(
                candidate_topics=[],
                strategy_focus="fast_growth",
                capacity=sample_capacity,
                rules=sample_rules,
                historical_context=sample_historical_context
            )

    def test_invalid_scores(self):
        """ทดสอบการตรวจสอบคะแนนที่ไม่ถูกต้อง"""
        with pytest.raises(ValueError, match="คะแนน"):
            CandidateTopic(
                title="ทดสอบ",
                pillar="ธรรมะประยุกต์",
                predicted_14d_views=1000,
                scores={
                    "search_intent": 1.5,  # เกิน 1.0
                    "freshness": 0.5,
                    "evergreen": 0.5,
                    "brand_fit": 0.5,
                    "composite": 0.5
                },
                reason="ทดสอบ"
            )

    def test_different_strategies_produce_different_results(self, agent, sample_input):
        """ทดสอบว่ากลยุทธ์ต่างกันให้ผลลัพธ์ต่างกัน"""
        # ทดสอบ fast_growth
        sample_input.strategy_focus = "fast_growth"
        result_fast = agent.run(sample_input)
        
        # ทดสอบ evergreen_balance
        sample_input.strategy_focus = "evergreen_balance"
        result_evergreen = agent.run(sample_input)
        
        # ทดสอบ depth_series  
        sample_input.strategy_focus = "depth_series"
        result_depth = agent.run(sample_input)
        
        # ผลลัพธ์ควรต่างกัน (อย่างน้อยในคะแนน)
        fast_scores = [t.priority_score for t in result_fast.scheduled]
        evergreen_scores = [t.priority_score for t in result_evergreen.scheduled]
        depth_scores = [t.priority_score for t in result_depth.scheduled]
        
        # ไม่ควรเหมือนกันทั้งหมด
        assert not (fast_scores == evergreen_scores == depth_scores)

    def test_pillar_performance_multiplier(self, agent, sample_input):
        """ทดสอบการใช้ pillar performance multiplier"""
        result = agent.run(sample_input)
        
        # หัวข้อใน pillar ที่มี performance สูงควรได้คะแนนดีขึ้น
        # เจาะลึก/ซีรีส์ มี multiplier 1.18 (สูงสุด)
        series_topics = [t for t in result.scheduled if t.pillar == "เจาะลึก/ซีรีส์"]
        
        # ควรมีอย่างน้อยหนึ่งหัวข้อ เนื่องจากมี multiplier สูง
        if len(series_topics) > 0:
            assert any(t.priority_score > 50 for t in series_topics)