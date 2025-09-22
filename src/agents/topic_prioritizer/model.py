"""
Pydantic Models สำหรับ TopicPrioritizerAgent
กำหนด Schema สำหรับ Input และ Output ของ Agent
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CandidateTopic(BaseModel):
    """หัวข้อผู้สมัครจาก TrendScoutAgent"""
    
    title: str = Field(description="ชื่อหัวข้อ")
    pillar: str = Field(description="เสาหลักของเนื้อหา")
    predicted_14d_views: int = Field(description="การดูคาดการณ์ 14 วัน")
    scores: Dict[str, float] = Field(description="คะแนนในแต่ละมิติ")
    reason: str = Field(description="เหตุผลที่แนะนำ")
    
    @field_validator("predicted_14d_views")
    @classmethod
    def validate_predicted_views(cls, v):
        if v < 0:
            raise ValueError("การดูคาดการณ์ต้องไม่เป็นลบ")
        return v
    
    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v):
        required_keys = ["search_intent", "freshness", "evergreen", "brand_fit", "composite"]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"ขาดคะแนน {key}")
            if not 0 <= v[key] <= 1:
                raise ValueError(f"คะแนน {key} ต้องอยู่ระหว่าง 0-1")
        return v


class Capacity(BaseModel):
    """ความจุการผลิตต่อสัปดาห์"""
    
    weeks: int = Field(default=4, description="จำนวนสัปดาห์")
    longform_per_week: int = Field(description="วิดีโอยาวต่อสัปดาห์")
    shorts_per_week: int = Field(description="วิดีโอสั้นต่อสัปดาห์")
    
    @field_validator("weeks", "longform_per_week", "shorts_per_week")
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("ค่าต้องเป็นจำนวนเต็มบวก")
        return v


class Rules(BaseModel):
    """กฎและเงื่อนไขการจัดลำดับ"""
    
    min_pillars_diversity: int = Field(default=3, description="จำนวนเสาหลักขั้นต่ำ")
    force_series_prefixes: List[str] = Field(
        default_factory=list, 
        description="คำขึ้นต้นที่บังคับให้เป็นซีรีส์"
    )
    
    @field_validator("min_pillars_diversity")
    @classmethod
    def validate_min_pillars(cls, v):
        if v <= 0:
            raise ValueError("จำนวนเสาหลักขั้นต่ำต้องเป็นจำนวนเต็มบวก")
        return v


class HistoricalContext(BaseModel):
    """ข้อมูลประวัติศาสตร์เพื่อการประเมิน"""
    
    recent_longform_avg_views: int = Field(description="ยอดวิวเฉลี่ยวิดีโอยาว")
    recent_shorts_avg_views: int = Field(description="ยอดวิวเฉลี่ยวิดีโอสั้น")
    pillar_performance: Dict[str, float] = Field(
        description="ประสิทธิภาพแต่ละเสาหลัก (multiplier)"
    )
    
    @field_validator("recent_longform_avg_views", "recent_shorts_avg_views")
    @classmethod
    def validate_views(cls, v):
        if v < 0:
            raise ValueError("ยอดวิวเฉลี่ยต้องไม่เป็นลบ")
        return v


class TopicPrioritizerInput(BaseModel):
    """Input สำหรับ TopicPrioritizerAgent"""
    
    candidate_topics: List[CandidateTopic] = Field(description="หัวข้อผู้สมัครจาก TrendScout")
    strategy_focus: Literal["fast_growth", "evergreen_balance", "depth_series"] = Field(
        description="กลยุทธ์การเน้น"
    )
    capacity: Capacity = Field(description="ความจุการผลิต")
    rules: Rules = Field(default_factory=Rules, description="กฎและเงื่อนไข")
    historical_context: HistoricalContext = Field(description="ข้อมูลประวัติศาสตร์")
    
    @field_validator("candidate_topics")
    @classmethod
    def validate_topics_not_empty(cls, v):
        if not v:
            raise ValueError("ต้องมีหัวข้อผู้สมัครอย่างน้อย 1 หัวข้อ")
        return v


class ScheduledTopic(BaseModel):
    """หัวข้อที่ถูกจัดลำดับและวางแผนแล้ว"""
    
    topic_title: str = Field(description="ชื่อหัวข้อ")
    content_type: Literal["longform", "shorts"] = Field(description="ประเภทเนื้อหา")
    pillar: str = Field(description="เสาหลักของเนื้อหา")
    week: str = Field(description="สัปดาห์ (W1-W4)")
    slot_index: int = Field(description="ลำดับในสัปดาห์")
    priority_score: float = Field(description="คะแนนความสำคัญ")
    expected_role: Literal[
        "traffic_spike", "evergreen_seed", "series_part", "balance_filler", "audience_engagement"
    ] = Field(description="บทบาทที่คาดหวัง")
    series_group: Optional[str] = Field(default=None, description="กลุ่มซีรีส์")
    risk_flags: List[str] = Field(default_factory=list, description="ธงเตือนความเสี่ยง")
    notes: str = Field(default="", description="หมายเหตุ")
    
    @field_validator("priority_score")
    @classmethod
    def validate_priority_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("คะแนนความสำคัญต้องอยู่ระหว่าง 0-100")
        return v
    
    @field_validator("slot_index")
    @classmethod
    def validate_slot_index(cls, v):
        if v < 1:
            raise ValueError("ลำดับในสัปดาห์ต้องเป็นจำนวนเต็มบวก")
        return v


class UnscheduledTopic(BaseModel):
    """หัวข้อที่ไม่ได้รับการจัดตารางเวลา"""
    
    topic_title: str = Field(description="ชื่อหัวข้อ")
    reason: Literal["capacity_full", "low_score", "pillar_overrepresented"] = Field(
        description="เหตุผลที่ไม่ได้รับการจัดตารางเวลา"
    )
    priority_score: float = Field(description="คะแนนความสำคัญ")
    
    @field_validator("priority_score")
    @classmethod
    def validate_priority_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("คะแนนความสำคัญต้องอยู่ระหว่าง 0-100")
        return v


class DiversitySummary(BaseModel):
    """สรุปความหลากหลายของเสาหลัก"""
    
    pillar_counts: Dict[str, int] = Field(description="จำนวนหัวข้อในแต่ละเสาหลัก")
    distinct_pillars: int = Field(description="จำนวนเสาหลักที่แตกต่าง")
    meets_minimum: bool = Field(description="เป็นไปตามความหลากหลายขั้นต่ำ")


class SelfCheck(BaseModel):
    """การตรวจสอบตนเองของผลลัพธ์"""
    
    capacity_respected: bool = Field(description="เคารพความจุที่กำหนด")
    scores_monotonic: bool = Field(description="คะแนนเรียงลำดับถูกต้อง")
    diversity_ok: bool = Field(description="ความหลากหลายเป็นไปตามเกณฑ์")


class Meta(BaseModel):
    """ข้อมูล Meta เกี่ยวกับการประมวลผล"""
    
    total_candidates: int = Field(description="จำนวนหัวข้อผู้สมัครทั้งหมด")
    scheduled_count: int = Field(description="จำนวนหัวข้อที่จัดตารางเวลา")
    unscheduled_count: int = Field(description="จำนวนหัวข้อที่ไม่ได้จัดตารางเวลา")
    pillars_underrepresented: List[str] = Field(
        default_factory=list, 
        description="เสาหลักที่ขาดการแทนตัว"
    )
    adjustments_notes: str = Field(default="", description="หมายเหตุการปรับแต่ง")
    self_check: SelfCheck = Field(description="การตรวจสอบตนเอง")


class WeeksCapacity(BaseModel):
    """ความจุต่อสัปดาห์"""
    
    longform_per_week: int = Field(description="วิดีโอยาวต่อสัปดาห์")
    shorts_per_week: int = Field(description="วิดีโอสั้นต่อสัปดาห์")


class TopicPrioritizerOutput(BaseModel):
    """Output สำหรับ TopicPrioritizerAgent"""
    
    plan_generated_at: datetime = Field(
        default_factory=datetime.now, 
        description="เวลาที่สร้างแผน"
    )
    strategy_focus: str = Field(description="กลยุทธ์ที่ใช้")
    weeks_capacity: WeeksCapacity = Field(description="ความจุต่อสัปดาห์")
    scheduled: List[ScheduledTopic] = Field(description="หัวข้อที่จัดตารางเวลา")
    unscheduled: List[UnscheduledTopic] = Field(
        default_factory=list, 
        description="หัวข้อที่ไม่ได้จัดตารางเวลา"
    )
    diversity_summary: DiversitySummary = Field(description="สรุปความหลากหลาย")
    meta: Meta = Field(description="ข้อมูล Meta")
    
    @field_validator("scheduled")
    @classmethod
    def validate_scheduled_ordering(cls, v):
        """ตรวจสอบการเรียงลำดับคะแนนความสำคัญ"""
        if len(v) > 1:
            # แยกตาม content_type แล้วตรวจสอบการเรียงลำดับ
            longform_scores = [
                topic.priority_score for topic in v if topic.content_type == "longform"
            ]
            shorts_scores = [
                topic.priority_score for topic in v if topic.content_type == "shorts"
            ]
            
            # อนุญาตให้มีการปรับเรียงเล็กน้อยเพื่อ calendar constraints
            # แต่ไม่ควรมีความแตกต่างมากกว่า 10 คะแนน
            def check_loose_ordering(scores):
                for i in range(len(scores) - 1):
                    if scores[i] < scores[i + 1] - 10:
                        return False
                return True
            
            if longform_scores and not check_loose_ordering(longform_scores):
                raise ValueError("หัวข้อ longform ควรเรียงตามคะแนนจากมากไปน้อย")
            if shorts_scores and not check_loose_ordering(shorts_scores):
                raise ValueError("หัวข้อ shorts ควรเรียงตามคะแนนจากมากไปน้อย")
        
        return v


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""
    
    error: Dict[str, Any] = Field(description="ข้อมูลข้อผิดพลาด")
    
    @field_validator("error")
    @classmethod
    def validate_error_structure(cls, v):
        required_keys = ["code", "message"]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"ขาดฟิลด์ {key} ในข้อมูลข้อผิดพลาด")
        return v