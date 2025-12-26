#!/usr/bin/env python3
"""
DaVinci Resolve Timeline Generator - Path A (Video Editing Helper)

สร้าง EDL/CSV timeline template จาก visual_guide.json และ voiceover audio
สำหรับ import เข้า DaVinci Resolve
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict
import csv


def load_visual_guide(guide_path: Path) -> dict:
    """โหลด visual guide"""
    with open(guide_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_timestamp(ts: str) -> tuple:
    """แปลง timestamp string เป็น (start_sec, end_sec)"""
    # Format: "00:00-00:30" หรือ "00:00 - 00:30"
    ts = ts.replace(' ', '')
    if '-' in ts:
        start, end = ts.split('-')
        return time_to_seconds(start), time_to_seconds(end)
    return 0, 0


def time_to_seconds(time_str: str) -> float:
    """แปลง MM:SS หรือ HH:MM:SS เป็นวินาที"""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def seconds_to_timecode(seconds: float, fps: int = 30) -> str:
    """แปลงวินาทีเป็น timecode (HH:MM:SS:FF)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds % 1) * fps)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def generate_edl(visual_guide: dict, output_path: Path, fps: int = 30):
    """สร้าง EDL file (Edit Decision List) สำหรับ DaVinci Resolve"""
    
    scenes = visual_guide.get('scenes', [])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("TITLE: Dhamma Video Timeline\n")
        f.write(f"FCM: NON-DROP FRAME\n\n")
        
        for i, scene in enumerate(scenes, 1):
            # Parse timestamp
            timestamp = scene.get('timestamp', '00:00-00:00')
            start_sec, end_sec = parse_timestamp(timestamp)
            duration = end_sec - start_sec
            
            # Scene type
            scene_type = scene.get('type', 'B-roll')
            description = scene.get('description', '')
            
            # EDL format
            # 001  AX       V     C        00:00:00:00 00:00:05:00 00:00:00:00 00:00:05:00
            # * FROM CLIP NAME: clip.mp4
            
            tc_start = seconds_to_timecode(start_sec, fps)
            tc_end = seconds_to_timecode(end_sec, fps)
            
            f.write(f"{i:03d}  AX       V     C        {tc_start} {tc_end} {tc_start} {tc_end}\n")
            f.write(f"* FROM CLIP NAME: {scene_type}_{i:02d}.mp4\n")
            f.write(f"* COMMENT: {description[:60]}\n")
            f.write(f"\n")
    
    print(f"✅ สร้างไฟล์ EDL แล้ว: {output_path.name}")


def generate_csv_timeline(visual_guide: dict, output_path: Path):
    """สร้าง CSV timeline สำหรับ import เข้า DaVinci Resolve"""
    
    scenes = visual_guide.get('scenes', [])
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Headers
        writer.writerow([
            'Scene', 'Start Time', 'End Time', 'Duration (s)', 
            'Type', 'Description', 'B-roll File', 'Text Overlay', 'Notes'
        ])
        
        for i, scene in enumerate(scenes, 1):
            timestamp = scene.get('timestamp', '00:00-00:00')
            start_sec, end_sec = parse_timestamp(timestamp)
            duration = end_sec - start_sec
            
            scene_type = scene.get('type', 'Unknown')
            description = scene.get('description', '')
            
            # Handle text_overlay (อาจเป็น dict หรือ list)
            text_overlay_data = scene.get('text_overlay', {})
            if isinstance(text_overlay_data, dict):
                text_overlay = text_overlay_data.get('main', '')
            elif isinstance(text_overlay_data, list):
                text_overlay = text_overlay_data[0] if text_overlay_data else ''
            else:
                text_overlay = ''
            
            # แนะนำชื่อไฟล์ B-roll
            broll_file = f"broll_{i:02d}.mp4" if scene_type == 'B-roll' else ""
            
            # Notes จาก suggestions
            suggestions = scene.get('suggestions', [])
            notes = '; '.join(suggestions[:2]) if suggestions else ''
            
            writer.writerow([
                i,
                timestamp.split('-')[0].strip(),
                timestamp.split('-')[1].strip() if '-' in timestamp else '',
                duration,
                scene_type,
                description,
                broll_file,
                text_overlay,
                notes
            ])
    
    print(f"✅ สร้างไฟล์ CSV Timeline แล้ว: {output_path.name}")


def generate_text_overlays(visual_guide: dict, output_path: Path):
    """สร้างรายการ text overlays สำหรับใส่ในวิดีโอ"""
    
    scenes = visual_guide.get('scenes', [])
    overlays = []
    
    for i, scene in enumerate(scenes, 1):
        text_data = scene.get('text_overlay', {})
        
        # Handle different text_overlay formats
        text_main = ''
        text_style = 'default'
        text_position = 'center'
        text_font_size = 'medium'
        
        if isinstance(text_data, dict):
            text_main = text_data.get('main', '')
            text_style = text_data.get('style', 'default')
            text_position = text_data.get('position', 'center')
            text_font_size = text_data.get('font_size', 'medium')
        elif isinstance(text_data, list) and text_data:
            text_main = text_data[0] if isinstance(text_data[0], str) else ''
        
        if text_main:
            timestamp = scene.get('timestamp', '00:00-00:00')
            start_sec, _ = parse_timestamp(timestamp)
            
            overlays.append({
                'scene': i,
                'timestamp': timestamp,
                'start_sec': start_sec,
                'text': text_main,
                'style': text_style,
                'position': text_position,
                'font_size': text_font_size
            })
    
    # Save as JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_overlays': len(overlays),
            'overlays': overlays,
            'instructions': {
                'davinci_resolve': 'Use Fusion > Text+ node for each overlay',
                'timing': 'Match start_sec to timeline position',
                'styling': 'Adjust font size and position as specified'
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ สร้างคู่มือ Text Overlays แล้ว: {output_path.name}")
    print(f"   จำนวน overlays: {len(overlays)}")


def generate_markdown_guide(visual_guide: dict, output_path: Path):
    """สร้างคู่มือการ edit แบบ markdown"""
    
    scenes = visual_guide.get('scenes', [])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 🎬 Video Editing Guide - DaVinci Resolve\n\n")
        f.write("## Timeline Overview\n\n")
        f.write(f"- **Total Scenes:** {len(scenes)}\n")
        f.write(f"- **Total Duration:** {visual_guide.get('total_duration', 'N/A')}\n")
        f.write(f"- **Format:** 1080p 30fps (or 4K if available)\n\n")
        
        f.write("---\n\n")
        f.write("## Scene-by-Scene Breakdown\n\n")
        
        for i, scene in enumerate(scenes, 1):
            timestamp = scene.get('timestamp', '00:00-00:00')
            scene_type = scene.get('type', 'Unknown')
            description = scene.get('description', '')
            mood = scene.get('mood', '')
            
            # Handle text_overlay safely
            text_overlay = scene.get('text_overlay', {})
            text_main = ''
            text_style = 'default'
            text_position = 'center'
            
            if isinstance(text_overlay, dict):
                text_main = text_overlay.get('main', '')
                text_style = text_overlay.get('style', 'default')
                text_position = text_overlay.get('position', 'center')
            elif isinstance(text_overlay, list) and text_overlay:
                text_main = text_overlay[0] if isinstance(text_overlay[0], str) else ''
            
            suggestions = scene.get('suggestions', [])
            
            f.write(f"### Scene {i}: {timestamp}\n\n")
            f.write(f"**Type:** {scene_type}  \n")
            f.write(f"**Description:** {description}  \n")
            if mood:
                f.write(f"**Mood:** {mood}  \n")
            f.write("\n")
            
            if text_main:
                f.write(f"**📝 Text Overlay:**\n")
                f.write(f"- Text: \"{text_main}\"\n")
                f.write(f"- Style: {text_style}\n")
                f.write(f"- Position: {text_position}\n")
                f.write("\n")
            
            if suggestions:
                f.write(f"**💡 Suggestions:**\n")
                for sug in suggestions:
                    f.write(f"- {sug}\n")
                f.write("\n")
            
            f.write(f"**🎥 Action:**\n")
            if scene_type == 'B-roll':
                f.write(f"1. Import B-roll file: `broll_{i:02d}.mp4`\n")
                f.write(f"2. Place on timeline at {timestamp.split('-')[0]}\n")
                f.write(f"3. Trim to match end time: {timestamp.split('-')[1] if '-' in timestamp else 'N/A'}\n")
            else:
                f.write(f"1. Record/import footage for this scene\n")
                f.write(f"2. Place on timeline at {timestamp.split('-')[0]}\n")
            
            f.write("\n---\n\n")
        
        f.write("## 🛠️ DaVinci Resolve Workflow\n\n")
        f.write("### 1. Setup Project\n")
        f.write("- Create new project: `Dhamma_Video_001`\n")
        f.write("- Settings: 1920x1080, 30fps, Rec.709\n\n")
        
        f.write("### 2. Import Media\n")
        f.write("- Import voiceover audio: `audio/voiceover.mp3`\n")
        f.write("- Import all B-roll videos from `broll/` folder\n\n")
        
        f.write("### 3. Edit Timeline\n")
        f.write("- Place voiceover on Audio Track 1\n")
        f.write("- Use this guide to place B-roll on Video Track 1\n")
        f.write("- Add text overlays using Fusion > Text+\n\n")
        
        f.write("### 4. Color Grading\n")
        f.write("- Apply consistent color grade across all clips\n")
        f.write("- Warm tones for meditation scenes\n")
        f.write("- Soft contrast\n\n")
        
        f.write("### 5. Export\n")
        f.write("- Format: MP4 (H.264)\n")
        f.write("- Resolution: 1080p or 4K\n")
        f.write("- Bitrate: 10-15 Mbps (1080p) or 35-45 Mbps (4K)\n")
        f.write("- Audio: AAC 192 kbps\n")
    
    print(f"✅ สร้างคู่มือการตัดต่อแล้ว: {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate DaVinci Resolve timeline templates")
    parser.add_argument('--input-dir', type=Path, required=True,
                       help='Input directory with visual_guide.json')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory for templates (default: templates/)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Timeline framerate (default: 30)')
    
    args = parser.parse_args()
    
    # Paths
    input_dir = args.input_dir
    output_dir = args.output_dir or Path('templates')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    guide_file = input_dir / 'visual_guide.json'
    
    # ตรวจสอบไฟล์
    if not guide_file.exists():
        print(f"❌ ข้อผิดพลาด: ไม่พบไฟล์ {guide_file}!")
        return
    
    print("🎬 ตัวสร้างเทมเพลต DaVinci Resolve")
    print(f"📂 อินพุต: {input_dir}")
    print(f"📂 เอาต์พุต: {output_dir}")
    print(f"🎞️  อัตราเฟรม: {args.fps}\n")
    
    # โหลด visual guide
    visual_guide = load_visual_guide(guide_file)
    scenes = visual_guide.get('scenes', [])
    
    if not scenes:
        print("❌ ไม่พบซีนใน visual_guide.json!")
        return
    
    print(f"✅ พบ {len(scenes)} ซีน\n")
    
    # สร้างไฟล์ต่างๆ
    print("📄 กำลังสร้างไฟล์...\n")
    
    # 1. EDL file
    edl_file = output_dir / 'timeline.edl'
    generate_edl(visual_guide, edl_file, args.fps)
    
    # 2. CSV timeline
    csv_file = output_dir / 'timeline.csv'
    generate_csv_timeline(visual_guide, csv_file)
    
    # 3. Text overlays
    overlays_file = output_dir / 'text_overlays.json'
    generate_text_overlays(visual_guide, overlays_file)
    
    # 4. Markdown editing guide
    guide_md = output_dir / 'EDITING_GUIDE.md'
    generate_markdown_guide(visual_guide, guide_md)
    
    print("\n✅ สร้างไฟล์เทมเพลตทั้งหมดเรียบร้อย!")
    print("\n🎯 ขั้นตอนถัดไป:")
    print("   1. เปิดโปรแกรม DaVinci Resolve")
    print("   2. สร้างโปรเจกต์ใหม่ (1920x1080, 30fps)")
    print("   3. นำเข้าไฟล์เสียงบันทึก (voiceover)")
    print("   4. นำเข้าคลิป B-roll")
    print(f"   5. ใช้ไฟล์ {guide_md.name} เป็นแนวทางการตัดต่อ")
    print(f"   6. ตัวเลือก: นำเข้า {edl_file.name} เพื่อโครงสร้างไทม์ไลน์อัตโนมัติ")
    print("\n💡 เคล็ดลับ: ทำตาม EDITING_GUIDE.md ทีละขั้นตอนเพื่อผลลัพธ์ดีที่สุด")


if __name__ == '__main__':
    main()
