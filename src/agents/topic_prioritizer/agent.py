"""
TopicPrioritizerAgent - Agent สำหรับจัดลำดับความสำคัญและสร้างปฏิทินการผลิต
"""

import json
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

from automation_core.base_agent import BaseAgent
from automation_core.prompt_loader import get_prompt_path, load_prompt
from automation_core.utils.scoring import calculate_composite_score

from .model import (
    CandidateTopic,
    DiversitySummary,
    ErrorResponse,
    Meta,
    ScheduledTopic,
    SelfCheck,
    TopicPrioritizerInput,
    TopicPrioritizerOutput,
    UnscheduledTopic,
    WeeksCapacity,
)


class TopicPrioritizerAgent(BaseAgent[TopicPrioritizerInput, TopicPrioritizerOutput]):
    """Agent สำหรับจัดลำดับความสำคัญและสร้างปฏิทินการผลิต"""

    def __init__(self):
        super().__init__(
            name="TopicPrioritizerAgent",
            version="1.0.0",
            description="จัดลำดับความสำคัญของหัวข้อและสร้างปฏิทินการผลิต",
        )

    def run(self, input_data: TopicPrioritizerInput) -> TopicPrioritizerOutput:
        """ประมวลผลการจัดลำดับความสำคัญและสร้างปฏิทิน"""

        try:
            # 1. คำนวณคะแนนความสำคัญสำหรับแต่ละหัวข้อ
            scored_topics = self._calculate_priority_scores(input_data)

            # 2. จำแนกประเภทเนื้อหา (longform/shorts)
            classified_topics = self._classify_content_types(scored_topics, input_data)

            # 3. สร้างตารางเวลาการผลิต
            scheduled, unscheduled = self._create_production_schedule(
                classified_topics, input_data
            )

            # 4. สร้างสรุปความหลากหลายและตรวจสอบ
            diversity_summary = self._create_diversity_summary(scheduled, input_data)
            self_check = self._perform_self_check(scheduled, unscheduled, input_data)

            # 5. สร้างข้อมูล Meta
            meta = Meta(
                total_candidates=len(input_data.candidate_topics),
                scheduled_count=len(scheduled),
                unscheduled_count=len(unscheduled),
                pillars_underrepresented=self._find_underrepresented_pillars(
                    scheduled, input_data
                ),
                adjustments_notes=f"{input_data.strategy_focus} emphasis applied",
                self_check=self_check,
            )

            return TopicPrioritizerOutput(
                plan_generated_at=datetime.now(),
                strategy_focus=input_data.strategy_focus,
                weeks_capacity=WeeksCapacity(
                    longform_per_week=input_data.capacity.longform_per_week,
                    shorts_per_week=input_data.capacity.shorts_per_week,
                ),
                scheduled=scheduled,
                unscheduled=unscheduled,
                diversity_summary=diversity_summary,
                meta=meta,
            )

        except Exception as e:
            # ถ้าเกิดข้อผิดพลาด ส่งคืน ErrorResponse format
            error_response = ErrorResponse(
                error={
                    "code": "PROCESSING_ERROR",
                    "message": f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}",
                    "suggested_fix": "ตรวจสอบข้อมูลนำเข้าและลองใหม่",
                }
            )
            # ในกรณีจริงควรส่ง ErrorResponse แต่เนื่องจาก type hint ต้อง return TopicPrioritizerOutput
            # จึงสร้าง minimal output แทน
            return self._create_minimal_output(input_data, str(e))

    def _calculate_priority_scores(
        self, input_data: TopicPrioritizerInput
    ) -> List[Tuple[CandidateTopic, float, str]]:
        """คำนวณคะแนนความสำคัญสำหรับแต่ละหัวข้อ"""

        scored_topics = []
        
        # หาค่าสูงสุดของ predicted_14d_views เพื่อ normalize
        max_predicted_views = max(
            topic.predicted_14d_views for topic in input_data.candidate_topics
        )
        
        for topic in input_data.candidate_topics:
            priority_score = self._calculate_single_priority_score(
                topic, input_data, max_predicted_views
            )
            content_type = self._determine_content_type(topic, input_data)
            scored_topics.append((topic, priority_score, content_type))

        # เรียงลำดับตามคะแนนจากมากไปน้อย
        scored_topics.sort(key=lambda x: x[1], reverse=True)
        
        return scored_topics

    def _calculate_single_priority_score(
        self, topic: CandidateTopic, input_data: TopicPrioritizerInput, max_views: int
    ) -> float:
        """คำนวณคะแนนความสำคัญสำหรับหัวข้อเดียว"""

        # Base score จาก composite และ predicted views
        normalized_views = min(topic.predicted_14d_views / max_views, 1.0) if max_views > 0 else 0
        base_score = topic.scores["composite"] * 70 + normalized_views * 30

        # Strategy adjustments
        adjustments = 0
        if input_data.strategy_focus == "fast_growth":
            adjustments += topic.scores["freshness"] * 10 + topic.scores["search_intent"] * 5
        elif input_data.strategy_focus == "evergreen_balance":
            adjustments += topic.scores["evergreen"] * 8 + topic.scores["brand_fit"] * 4
        elif input_data.strategy_focus == "depth_series":
            adjustments += topic.scores["brand_fit"] * 8 + topic.scores["evergreen"] * 6
            # Series bonus
            series_bonus = self._calculate_series_bonus(topic, input_data.rules.force_series_prefixes)
            adjustments += series_bonus

        # Pillar performance multiplier
        pillar_multiplier = input_data.historical_context.pillar_performance.get(topic.pillar, 1.0)
        final_score = (base_score + adjustments) * pillar_multiplier

        # Clip to 0-100 range
        return max(0, min(100, final_score))

    def _calculate_series_bonus(self, topic: CandidateTopic, force_series_prefixes: List[str]) -> float:
        """คำนวณโบนัสสำหรับซีรีส์"""
        for prefix in force_series_prefixes:
            if topic.title.startswith(prefix):
                return 6.0
        return 0.0

    def _determine_content_type(self, topic: CandidateTopic, input_data: TopicPrioritizerInput) -> str:
        """กำหนดประเภทเนื้อหา (longform/shorts)"""
        
        # ตรวจสอบว่าเป็น forced series หรือไม่
        for prefix in input_data.rules.force_series_prefixes:
            if topic.title.startswith(prefix):
                return "longform"
        
        # ตรวจสอบความลึกและ predicted views
        has_depth = topic.scores["evergreen"] > 0.65 or topic.scores["brand_fit"] > 0.85
        meets_views_threshold = topic.predicted_14d_views >= input_data.historical_context.recent_longform_avg_views
        
        if has_depth and meets_views_threshold:
            return "longform"
        elif topic.scores["search_intent"] > 0.7 and topic.scores["evergreen"] < 0.55:
            return "shorts"
        else:
            # Default decision based on predicted views
            return "longform" if meets_views_threshold else "shorts"

    def _classify_content_types(
        self, scored_topics: List[Tuple[CandidateTopic, float, str]], input_data: TopicPrioritizerInput
    ) -> List[Tuple[CandidateTopic, float, str]]:
        """จำแนกประเภทเนื้อหาสำหรับหัวข้อทั้งหมด"""
        # Content type already determined in scoring step
        return scored_topics

    def _create_production_schedule(
        self, classified_topics: List[Tuple[CandidateTopic, float, str]], input_data: TopicPrioritizerInput
    ) -> Tuple[List[ScheduledTopic], List[UnscheduledTopic]]:
        """สร้างตารางเวลาการผลิต"""

        scheduled = []
        unscheduled = []
        
        # ติดตามความจุต่อสัปดาห์
        weekly_capacity = {
            f"W{i+1}": {
                "longform": input_data.capacity.longform_per_week,
                "shorts": input_data.capacity.shorts_per_week,
                "longform_count": 0,
                "shorts_count": 0,
            }
            for i in range(input_data.capacity.weeks)
        }
        
        # ติดตามการกระจายของ pillar
        weekly_pillar_counts = {
            f"W{i+1}": {} for i in range(input_data.capacity.weeks)
        }

        for topic, priority_score, content_type in classified_topics:
            # ตรวจสอบคะแนนขั้นต่ำ
            if priority_score < 40:
                unscheduled.append(UnscheduledTopic(
                    topic_title=topic.title,
                    reason="low_score",
                    priority_score=priority_score
                ))
                continue

            # หาสัปดาห์ที่เหมาะสม
            target_week = self._find_best_week_for_topic(
                topic, content_type, weekly_capacity, weekly_pillar_counts
            )

            if target_week is None:
                unscheduled.append(UnscheduledTopic(
                    topic_title=topic.title,
                    reason="capacity_full",
                    priority_score=priority_score
                ))
                continue

            # จัดลำดับ slot_index
            slot_index = weekly_capacity[target_week][f"{content_type}_count"] + 1
            
            # กำหนดบทบาทที่คาดหวัง
            expected_role = self._determine_expected_role(topic, priority_score, input_data.strategy_focus)
            
            # ตรวจสอบซีรีส์
            series_group = self._determine_series_group(topic, input_data.rules.force_series_prefixes)
            
            # สร้าง risk flags
            risk_flags = self._generate_risk_flags(topic, weekly_pillar_counts[target_week])
            
            # สร้างหมายเหตุ
            notes = self._generate_notes(topic, priority_score, input_data.strategy_focus)

            scheduled_topic = ScheduledTopic(
                topic_title=topic.title,
                content_type=content_type,
                pillar=topic.pillar,
                week=target_week,
                slot_index=slot_index,
                priority_score=priority_score,
                expected_role=expected_role,
                series_group=series_group,
                risk_flags=risk_flags,
                notes=notes
            )

            scheduled.append(scheduled_topic)
            
            # อัปเดตการนับ
            weekly_capacity[target_week][f"{content_type}_count"] += 1
            weekly_pillar_counts[target_week][topic.pillar] = weekly_pillar_counts[target_week].get(topic.pillar, 0) + 1

        return scheduled, unscheduled

    def _find_best_week_for_topic(
        self, topic: CandidateTopic, content_type: str, weekly_capacity: Dict, weekly_pillar_counts: Dict
    ) -> str | None:
        """หาสัปดาห์ที่เหมาะสมที่สุดสำหรับหัวข้อ"""
        
        for week in sorted(weekly_capacity.keys()):
            week_info = weekly_capacity[week]
            
            # ตรวจสอบความจุ
            if week_info[f"{content_type}_count"] >= week_info[content_type]:
                continue
            
            # ตรวจสอบการกระจายของ pillar (ไม่ให้เกิน 50% ในสัปดาห์)
            total_topics_in_week = week_info["longform_count"] + week_info["shorts_count"]
            pillar_count_in_week = weekly_pillar_counts[week].get(topic.pillar, 0)
            
            if total_topics_in_week > 0 and (pillar_count_in_week + 1) / (total_topics_in_week + 1) > 0.5:
                # ลองสัปดาห์ถัดไป
                continue
            
            return week
        
        return None

    def _determine_expected_role(self, topic: CandidateTopic, priority_score: float, strategy_focus: str) -> str:
        """กำหนดบทบาทที่คาดหวัง"""
        
        if priority_score >= 80:
            return "traffic_spike"
        elif topic.scores["evergreen"] > 0.75:
            return "evergreen_seed"
        elif any(topic.title.startswith(prefix) for prefix in ["พุทธจิตวิทยา", "ชาดกชุด", "10 วันภาวนา"]):
            return "series_part"
        elif topic.scores["search_intent"] > 0.8:
            return "audience_engagement"
        else:
            return "balance_filler"

    def _determine_series_group(self, topic: CandidateTopic, force_series_prefixes: List[str]) -> str | None:
        """กำหนดกลุ่มซีรีส์"""
        for prefix in force_series_prefixes:
            if topic.title.startswith(prefix):
                return prefix
        return None

    def _generate_risk_flags(self, topic: CandidateTopic, weekly_pillar_count: Dict) -> List[str]:
        """สร้าง risk flags"""
        flags = []
        
        # ตรวจสอบ pillar overload
        total_week_topics = sum(weekly_pillar_count.values())
        if total_week_topics > 0 and weekly_pillar_count.get(topic.pillar, 0) / total_week_topics > 0.4:
            flags.append("pillar_overload")
        
        # ตรวจสอบคะแนนต่ำ
        if topic.scores["composite"] < 0.6:
            flags.append("low_confidence")
        
        return flags

    def _generate_notes(self, topic: CandidateTopic, priority_score: float, strategy_focus: str) -> str:
        """สร้างหมายเหตุ"""
        notes = []
        
        if topic.scores["freshness"] > 0.8:
            notes.append("สดใหม่สูง")
        if topic.scores["search_intent"] > 0.8:
            notes.append("ความต้องการค้นหาสูง")
        if strategy_focus == "fast_growth" and priority_score >= 85:
            notes.append("เหมาะกลยุทธ์เร่งการเติบโต")
            
        return " • ".join(notes) if notes else "หัวข้อมาตรฐาน"

    def _create_diversity_summary(self, scheduled: List[ScheduledTopic], input_data: TopicPrioritizerInput) -> DiversitySummary:
        """สร้างสรุปความหลากหลายของเสาหลัก"""
        
        pillar_counts = {}
        for topic in scheduled:
            pillar_counts[topic.pillar] = pillar_counts.get(topic.pillar, 0) + 1
        
        distinct_pillars = len(pillar_counts)
        meets_minimum = distinct_pillars >= input_data.rules.min_pillars_diversity
        
        return DiversitySummary(
            pillar_counts=pillar_counts,
            distinct_pillars=distinct_pillars,
            meets_minimum=meets_minimum
        )

    def _find_underrepresented_pillars(self, scheduled: List[ScheduledTopic], input_data: TopicPrioritizerInput) -> List[str]:
        """หาเสาหลักที่ขาดการแทนตัว"""
        
        # รายการเสาหลักที่ควรมี (จาก TrendScoutAgent)
        expected_pillars = [
            "ธรรมะประยุกต์",
            "ชาดก/นิทานสอนใจ", 
            "ธรรมะสั้น",
            "เจาะลึก/ซีรีส์",
            "Q&A/ตอบคำถาม",
            "สรุปพระสูตร/หนังสือ"
        ]
        
        scheduled_pillars = {topic.pillar for topic in scheduled}
        underrepresented = [pillar for pillar in expected_pillars if pillar not in scheduled_pillars]
        
        return underrepresented

    def _perform_self_check(
        self, scheduled: List[ScheduledTopic], unscheduled: List[UnscheduledTopic], input_data: TopicPrioritizerInput
    ) -> SelfCheck:
        """ตรวจสอบผลลัพธ์ด้วยตัวเอง"""
        
        # ตรวจสอบความจุ
        weekly_counts = {}
        for topic in scheduled:
            week = topic.week
            if week not in weekly_counts:
                weekly_counts[week] = {"longform": 0, "shorts": 0}
            weekly_counts[week][topic.content_type] += 1
        
        capacity_respected = True
        for week, counts in weekly_counts.items():
            if (counts["longform"] > input_data.capacity.longform_per_week or 
                counts["shorts"] > input_data.capacity.shorts_per_week):
                capacity_respected = False
                break
        
        # ตรวจสอบการเรียงลำดับคะแนน (แบบหลวม)
        longform_scores = [t.priority_score for t in scheduled if t.content_type == "longform"]
        shorts_scores = [t.priority_score for t in scheduled if t.content_type == "shorts"]
        
        def check_loose_monotonic(scores):
            for i in range(len(scores) - 1):
                if scores[i] < scores[i + 1] - 10:  # อนุญาตความคลาดเคลื่อน 10 คะแนน
                    return False
            return True
        
        scores_monotonic = (check_loose_monotonic(longform_scores) and 
                           check_loose_monotonic(shorts_scores))
        
        # ตรวจสอบความหลากหลาย
        diversity_summary = self._create_diversity_summary(scheduled, input_data)
        diversity_ok = diversity_summary.meets_minimum
        
        return SelfCheck(
            capacity_respected=capacity_respected,
            scores_monotonic=scores_monotonic,
            diversity_ok=diversity_ok
        )

    def _create_minimal_output(self, input_data: TopicPrioritizerInput, error_msg: str) -> TopicPrioritizerOutput:
        """สร้าง output ขั้นต่ำเมื่อเกิดข้อผิดพลาด"""
        
        return TopicPrioritizerOutput(
            plan_generated_at=datetime.now(),
            strategy_focus=input_data.strategy_focus,
            weeks_capacity=WeeksCapacity(
                longform_per_week=input_data.capacity.longform_per_week,
                shorts_per_week=input_data.capacity.shorts_per_week,
            ),
            scheduled=[],
            unscheduled=[],
            diversity_summary=DiversitySummary(
                pillar_counts={},
                distinct_pillars=0,
                meets_minimum=False
            ),
            meta=Meta(
                total_candidates=len(input_data.candidate_topics),
                scheduled_count=0,
                unscheduled_count=0,
                pillars_underrepresented=[],
                adjustments_notes=f"Error occurred: {error_msg}",
                self_check=SelfCheck(
                    capacity_respected=True,
                    scores_monotonic=True,
                    diversity_ok=False
                )
            )
        )