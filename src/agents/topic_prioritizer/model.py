"""
Pydantic Models สำหรับ TopicPrioritizerAgent
กำหนด Schema สำหรับ Input และ Output ของ Agent
"""

from datetime import datetime

from pydantic import BaseModel, Field, validator

# Import TopicEntry from trend_scout
from ..trend_scout.model import TopicEntry


class PriorityInput(BaseModel):
    """Input สำหรับ TopicPrioritizerAgent"""

    topics: list[TopicEntry] = Field(description="หัวข้อจาก TrendScout")
    business_goals: dict[str, float] = Field(description="เป้าหมายธุรกิจ")
    audience_segments: list[str] = Field(description="กลุ่มเป้าหมาย")

    @validator("topics")
    def validate_topics(cls, v):
        if not v:
            raise ValueError("ต้องมีหัวข้ออย่างน้อย 1 หัวข้อ")
        return v

    @validator("business_goals")
    def validate_business_goals(cls, v):
        if not v:
            raise ValueError("ต้องกำหนดเป้าหมายธุรกิจ")
        return v


class PriorityScore(BaseModel):
    """คะแนนความสำคัญในแต่ละมิติ"""

    roi_potential: float = Field(description="ศักยภาพ ROI (0-100)")
    risk_level: float = Field(description="ระดับความเสี่ยง (0-100)")
    brand_alignment: float = Field(description="ความสอดคล้องกับแบรนด์ (0-100)")
    production_difficulty: float = Field(description="ความยากในการผลิต (0-100)")
    priority_score: float = Field(description="คะแนนความสำคัญรวม (0-100)")

    @validator(
        "roi_potential",
        "risk_level",
        "brand_alignment",
        "production_difficulty",
        "priority_score",
    )
    def validate_score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("คะแนนต้องอยู่ระหว่าง 0-100")
        return v


class PrioritizedTopic(BaseModel):
    """หัวข้อที่ได้รับการจัดลำดับความสำคัญแล้ว"""

    original_topic: TopicEntry = Field(description="หัวข้อต้นฉบับ")
    priority_rank: int = Field(description="อันดับความสำคัญ")
    priority_scores: PriorityScore = Field(description="คะแนนความสำคัญ")
    business_justification: str = Field(description="เหตุผลเชิงธุรกิจ")
    production_notes: str = Field(description="หมายเหตุการผลิต")

    @validator("priority_rank")
    def validate_priority_rank(cls, v):
        if v < 1:
            raise ValueError("อันดับความสำคัญต้องเป็นจำนวนเต็มบวก")
        return v


class PriorityOutput(BaseModel):
    """Output สำหรับ TopicPrioritizerAgent"""

    generated_at: datetime = Field(
        default_factory=datetime.now, description="เวลาที่สร้างผลลัพธ์"
    )
    prioritized_topics: list[PrioritizedTopic] = Field(description="หัวข้อที่จัดลำดับแล้ว")
    business_alignment: dict[str, float] = Field(description="ความสอดคล้องกับเป้าหมาย")
    recommendations: list[str] = Field(description="คำแนะนำ")

    @validator("prioritized_topics")
    def validate_topics_sorted(cls, v):
        if len(v) > 1:
            priorities = [topic.priority_scores.priority_score for topic in v]
            if priorities != sorted(priorities, reverse=True):
                raise ValueError("หัวข้อต้องเรียงตามคะแนนความสำคัญจากมากไปน้อย")
        return v

    @validator("prioritized_topics")
    def validate_topics_limit(cls, v):
        if len(v) > 10:
            raise ValueError("จำนวนหัวข้อที่จัดลำดับต้องไม่เกิน 10 หัวข้อ")
        return v
