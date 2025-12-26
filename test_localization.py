"""
ทดสอบ LocalizationSubtitleAgent
"""
import sys
from pathlib import Path

# เพิ่ม src ไปใน Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.localization_subtitle import (
    LocalizationSubtitleAgent,
    LocalizationSubtitleInput,
    SubtitleSegment
)

def main():
    print("🎬 ทดสอบ LocalizationSubtitleAgent\n")
    
    # สร้าง agent
    agent = LocalizationSubtitleAgent()
    
    # สร้างข้อมูล input
    input_data = LocalizationSubtitleInput(
        base_start_time="00:00:05,000",
        approved_script=[
            SubtitleSegment(
                segment_type="intro",
                text="ยินดีต้อนรับสู่ธรรมะดีดี [CIT:123]",
                est_seconds=6
            ),
            SubtitleSegment(
                segment_type="teaching",
                text="วันนี้เราจะมาเรียนรู้เรื่องการฝึกสมาธิ (หยุด 2 วิ)",
                est_seconds=8
            ),
            SubtitleSegment(
                segment_type="teaching",
                text="การหายใจเข้าออกอย่างมีสติ [CIT:456] เป็นพื้นฐานสำคัญ",
                est_seconds=7
            ),
            SubtitleSegment(
                segment_type="conclusion",
                text="ขอให้ทุกท่านมีความสุข (หยุด 1 วิ) สวัสดีครับ",
                est_seconds=5
            ),
        ],
    )
    
    # รัน agent
    print("⚙️ กำลังประมวลผล...")
    result = agent.run(input_data)
    
    # แสดงผลลัพธ์
    print("\n📝 ไฟล์ SRT ที่สร้าง:")
    print("=" * 60)
    print(result.srt)
    print("=" * 60)
    
    print("\n🌍 สรุปภาษาอังกฤษ:")
    print("-" * 60)
    print(result.english_summary)
    print("-" * 60)
    
    print(f"\n📊 Metadata:")
    print(f"  - จำนวน segments: {result.meta.segments_count}")
    print(f"  - ระยะเวลารวม: {result.meta.duration_total} วินาที")
    print(f"  - บรรทัดทั้งหมด: {result.meta.lines}")
    print(f"  - เวลาต่อเนื่อง: {result.meta.time_continuity_ok}")
    print(f"  - ไม่มีการซ้อนทับ: {result.meta.no_overlap}")
    print(f"  - ตรวจสอบ OK: {result.meta.self_check}")
    
    if result.warnings:
        print(f"\n⚠️ คำเตือน:")
        for warning in result.metadata.warnings:
            print(f"  - {warning}")
    
    print("\n✅ ทดสอบสำเร็จ!")

if __name__ == "__main__":
    main()
