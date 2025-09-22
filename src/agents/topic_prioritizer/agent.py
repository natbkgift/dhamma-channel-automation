"""
TopicPrioritizerAgent - Agent สำหรับจัดลำดับความสำคัญของหัวข้อ

Agent นี้รับหัวข้อจาก TrendScout และจัดลำดับความสำคัญตามเกณฑ์ธุรกิจ
โดยพิจารณาจาก ROI, ความเสี่ยง, ความเข้ากับแบรนด์ และความยากในการผลิต
"""

import logging

from automation_core.base_agent import BaseAgent

from .model import (
    PrioritizedTopic,
    PriorityInput,
    PriorityOutput,
    PriorityScore,
)

logger = logging.getLogger(__name__)


class TopicPrioritizerAgent(BaseAgent[PriorityInput, PriorityOutput]):
    """
    Agent สำหรับจัดลำดับความสำคัญของหัวข้อ

    วิธีการทำงาน:
    1. รับหัวข้อจาก TrendScout
    2. คำนวณคะแนนในแต่ละมิติ (ROI, Risk, Brand fit, Production difficulty)
    3. จัดลำดับความสำคัญตามน้ำหนักที่กำหนด
    4. สร้างคำแนะนำสำหรับการผลิต
    """

    def __init__(self):
        super().__init__(
            name="TopicPrioritizerAgent",
            version="1.0.0",
            description="จัดลำดับความสำคัญของหัวข้อตามเกณฑ์ธุรกิจ",
        )

        # น้ำหนักสำหรับการคำนวณคะแนนความสำคัญ
        self.weights = {
            "roi_potential": 0.40,  # ROI คาดการณ์ (40%)
            "risk_level": 0.25,  # ความเสี่ยง (25%) - คะแนนสูง = เสี่ยงน้อย
            "brand_alignment": 0.20,  # ความเข้ากับแบรนด์ (20%)
            "production_difficulty": 0.15,  # ความยากในการผลิต (15%) - คะแนนสูง = ง่าย
        }

    def run(self, input_data: PriorityInput) -> PriorityOutput:
        """ประมวลผลการจัดลำดับความสำคัญของหัวข้อ"""

        logger.info(f"เริ่มจัดลำดับความสำคัญสำหรับ {len(input_data.topics)} หัวข้อ")

        # 1. คำนวณคะแนนความสำคัญสำหรับแต่ละหัวข้อ
        prioritized_topics = []
        for topic in input_data.topics:
            priority_scores = self._calculate_priority_scores(topic, input_data)
            prioritized_topic = PrioritizedTopic(
                original_topic=topic,
                priority_rank=1,  # จะกำหนดใหม่หลังการเรียงลำดับ
                priority_scores=priority_scores,
                business_justification=self._generate_business_justification(
                    topic, priority_scores
                ),
                production_notes=self._generate_production_notes(
                    topic, priority_scores
                ),
            )
            prioritized_topics.append(prioritized_topic)

        # 2. เรียงลำดับตามคะแนนความสำคัญ
        prioritized_topics.sort(
            key=lambda x: x.priority_scores.priority_score, reverse=True
        )

        # 3. กำหนดอันดับใหม่
        for i, prioritized_topic in enumerate(prioritized_topics, 1):
            prioritized_topic.priority_rank = i

        # 4. คำนวณ business alignment
        business_alignment = self._calculate_business_alignment(
            prioritized_topics, input_data.business_goals
        )

        # 5. สร้างคำแนะนำ
        recommendations = self._generate_recommendations(prioritized_topics, input_data)

        logger.info(
            f"จัดลำดับความสำคัญเสร็จสิ้น - หัวข้ออันดับ 1: {prioritized_topics[0].original_topic.title}"
        )

        return PriorityOutput(
            prioritized_topics=prioritized_topics,
            business_alignment=business_alignment,
            recommendations=recommendations,
        )

    def _calculate_priority_scores(
        self, topic, input_data: PriorityInput
    ) -> PriorityScore:
        """คำนวณคะแนนความสำคัญในแต่ละมิติ"""

        # จำลองการคำนวณคะแนน (ในระบบจริงจะใช้ข้อมูลและอัลกอริทึมที่ซับซ้อนกว่า)

        # ROI Potential (พิจารณาจาก predicted views และ brand fit)
        roi_potential = min(
            100, (topic.predicted_14d_views / 1000) + topic.scores.brand_fit * 100
        )

        # Risk Level (คำนวณจาก risk_flags และ freshness)
        risk_level = (
            100 - len(topic.risk_flags) * 20 - (100 - topic.scores.freshness * 100)
        )
        risk_level = max(0, risk_level)

        # Brand Alignment (ใช้คะแนน brand_fit จาก TrendScout)
        brand_alignment = topic.scores.brand_fit * 100  # แปลงจาก 0-1 เป็น 0-100

        # Production Difficulty (พิจารณาจาก pillar และความซับซ้อน)
        difficulty_map = {
            "ธรรมะประยุกต์": 80,  # ง่าย
            "ธรรมะสั้น": 90,  # ง่ายที่สุด
            "เจาะลึก/ซีรีส์": 30,  # ยาก
            "สรุปพระสูตร/หนังสือ": 50,  # ปานกลาง
        }
        production_difficulty = difficulty_map.get(topic.pillar, 60)

        # คำนวณคะแนนรวม
        priority_score = (
            roi_potential * self.weights["roi_potential"]
            + risk_level * self.weights["risk_level"]
            + brand_alignment * self.weights["brand_alignment"]
            + production_difficulty * self.weights["production_difficulty"]
        )

        return PriorityScore(
            roi_potential=roi_potential,
            risk_level=risk_level,
            brand_alignment=brand_alignment,
            production_difficulty=production_difficulty,
            priority_score=priority_score,
        )

    def _generate_business_justification(
        self, topic, priority_scores: PriorityScore
    ) -> str:
        """สร้างเหตุผลเชิงธุรกิจ"""
        justifications = []

        if priority_scores.roi_potential > 80:
            justifications.append("มีศักยภาพ ROI สูง")
        if priority_scores.risk_level > 70:
            justifications.append("ความเสี่ยงต่ำ")
        if priority_scores.brand_alignment > 70:
            justifications.append("สอดคล้องกับแบรนด์")
        if priority_scores.production_difficulty > 70:
            justifications.append("ผลิตได้ง่าย")

        if not justifications:
            justifications.append("เหมาะสมสำหรับการทดลอง")

        return " | ".join(justifications)

    def _generate_production_notes(self, topic, priority_scores: PriorityScore) -> str:
        """สร้างหมายเหตุการผลิต"""
        notes = []

        if priority_scores.production_difficulty < 50:
            notes.append("ต้องการการเตรียมตัวพิเศษ")
        if len(topic.risk_flags) > 0:
            notes.append(f"ระวัง: {', '.join(topic.risk_flags)}")
        if topic.predicted_14d_views > 5000:
            notes.append("คาดว่าจะได้รับความสนใจสูง")

        return " | ".join(notes) if notes else "ไม่มีหมายเหตุพิเศษ"

    def _calculate_business_alignment(
        self,
        prioritized_topics: list[PrioritizedTopic],
        business_goals: dict[str, float],
    ) -> dict[str, float]:
        """คำนวณความสอดคล้องกับเป้าหมายธุรกิจ"""

        # จำลองการคำนวณ business alignment
        alignment = {}

        top_3_topics = prioritized_topics[:3]
        avg_brand_alignment = sum(
            t.priority_scores.brand_alignment for t in top_3_topics
        ) / len(top_3_topics)
        avg_roi_potential = sum(
            t.priority_scores.roi_potential for t in top_3_topics
        ) / len(top_3_topics)

        alignment["brand_consistency"] = avg_brand_alignment / 100
        alignment["revenue_potential"] = avg_roi_potential / 100
        alignment["content_diversity"] = (
            len({t.original_topic.pillar for t in top_3_topics}) / 4.0
        )

        return alignment

    def _generate_recommendations(
        self, prioritized_topics: list[PrioritizedTopic], input_data: PriorityInput
    ) -> list[str]:
        """สร้างคำแนะนำสำหรับการผลิต"""

        recommendations = []

        if len(prioritized_topics) > 0:
            top_topic = prioritized_topics[0]
            recommendations.append(
                f"แนะนำให้ผลิต '{top_topic.original_topic.title}' เป็นอันดับแรก"
            )

            if top_topic.priority_scores.production_difficulty < 50:
                recommendations.append("ควรจัดทีมที่มีประสบการณ์สำหรับหัวข้อแรก")

            high_risk_count = sum(
                1 for t in prioritized_topics[:5] if t.priority_scores.risk_level < 50
            )
            if high_risk_count > 2:
                recommendations.append("พิจารณาลดความเสี่ยงในหัวข้อ Top 5")

            diversity_score = len(
                {t.original_topic.pillar for t in prioritized_topics[:5]}
            )
            if diversity_score < 3:
                recommendations.append("ควรเพิ่มความหลากหลายของเนื้อหา")

        return recommendations
