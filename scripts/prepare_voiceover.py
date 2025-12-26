#!/usr/bin/env python3
"""
Voiceover Preparation Script - Path A (Manual Recording Helper)

แปลง script_validated.md เป็นไฟล์ที่ใช้งานง่ายสำหรับบันทึกเสียง
รวมถึง timing guide, pause markers, และ pronunciation tips
"""

import json
import argparse
from pathlib import Path
import re


def load_script(script_path: Path) -> str:
    """โหลด validated script"""
    with open(script_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_voiceover_guide(guide_path: Path) -> dict:
    """โหลด voiceover guide สำหรับ technical specs"""
    with open(guide_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_script_sections(script_content: str) -> list:
    """แยก script ออกเป็น sections พร้อม timestamps"""
    sections = []
    
    # Pattern 1: ### [00:00 - 00:30] Title
    # Pattern 2: ### Point 1: Title (1:30-2:30)
    # Pattern 3: ## [00:00 - 00:30] Title
    
    # ลองหา pattern แบบ [HH:MM - HH:MM]
    pattern1 = r'###?\s+\[(\d+:\d+)\s*-\s*(\d+:\d+)\]\s+(.+?)(?=###?|\Z)'
    matches = list(re.finditer(pattern1, script_content, re.DOTALL))
    
    if not matches:
        # ลอง pattern แบบ (HH:MM-HH:MM)
        pattern2 = r'###?\s+.+?\((\d+:\d+)-(\d+:\d+)\)(.+?)(?=###?|\Z)'
        matches = list(re.finditer(pattern2, script_content, re.DOTALL))
    
    if not matches:
        # ถ้าไม่มี timestamp ให้แบ่งเป็น sections ตาม ### headings
        # และประมาณเวลาจาก content
        pattern3 = r'###\s+(.+?)(?=###|\Z)'
        matches = list(re.finditer(pattern3, script_content, re.DOTALL))
        
        # ประมาณเวลา 10 นาที = 600 วินาที แบ่งตามจำนวน sections
        total_duration = 600
        section_duration = total_duration // len(matches) if matches else 60
        
        for i, match in enumerate(matches):
            title = match.group(1).split('\n')[0].strip()
            content = match.group(1).strip()
            
            start_sec = i * section_duration
            end_sec = (i + 1) * section_duration
            duration = end_sec - start_sec
            
            # นับจำนวนคำ
            words = len(re.findall(r'[\u0E00-\u0E7Fa-zA-Z]+', content))
            
            sections.append({
                'start': seconds_to_time(start_sec),
                'end': seconds_to_time(end_sec),
                'duration_sec': duration,
                'title': title,
                'content': content,
                'word_count': words,
                'suggested_wpm': words / (duration / 60) if duration > 0 else 120
            })
        
        return sections
    
    # ถ้ามี timestamp
    for match in matches:
        start_time = match.group(1)
        end_time = match.group(2)
        title = match.group(3).split('\n')[0].strip() if len(match.groups()) > 2 else "Section"
        content = match.group(3).strip() if len(match.groups()) > 2 else match.group(0)
        
        # คำนวณระยะเวลา
        start_sec = time_to_seconds(start_time)
        end_sec = time_to_seconds(end_time)
        duration = end_sec - start_sec
        
        # นับจำนวนคำ (รองรับภาษาไทย)
        words = len(re.findall(r'[\u0E00-\u0E7Fa-zA-Z]+', content))
        
        sections.append({
            'start': start_time,
            'end': end_time,
            'duration_sec': duration,
            'title': title,
            'content': content,
            'word_count': words,
            'suggested_wpm': words / (duration / 60) if duration > 0 else 120
        })
    
    return sections


def time_to_seconds(time_str: str) -> int:
    """แปลง MM:SS เป็นวินาที"""
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def seconds_to_time(seconds: int) -> str:
    """แปลงวินาทีเป็น MM:SS"""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


def add_pause_markers(text: str) -> str:
    """เพิ่ม pause markers สำหรับการอ่าน"""
    # Pause หลังจุด (1 วินาที)
    text = re.sub(r'\.(\s+)', r'. [PAUSE 1s]\1', text)
    
    # Pause หลังเครื่องหมายจุลภาค (0.5 วินาที)
    text = re.sub(r',(\s+)', r', [PAUSE 0.5s]\1', text)
    
    # Pause หลังหัวข้อ (1.5 วินาที)
    text = re.sub(r'(^#+\s+.+)$', r'\1 [PAUSE 1.5s]', text, flags=re.MULTILINE)
    
    return text


def create_recording_script(sections: list, guide: dict, output_dir: Path):
    """สร้างไฟล์สำหรับบันทึกเสียง"""
    
    # 1. Simple text script (อ่านง่าย)
    simple_script = output_dir / "recording_script_SIMPLE.txt"
    with open(simple_script, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("  VOICEOVER RECORDING SCRIPT - SIMPLE VERSION\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Duration: {sum(s['duration_sec'] for s in sections)} seconds\n")
        f.write(f"Voice Style: {guide.get('voice_profile', {}).get('tone', 'warm, calm')}\n")
        f.write(f"Speaking Rate: {guide.get('voice_profile', {}).get('speaking_rate', '120 wpm')}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        for i, section in enumerate(sections, 1):
            f.write(f"SECTION {i}/{len(sections)}\n")
            f.write(f"Time: {section['start']} - {section['end']} ({section['duration_sec']}s)\n")
            f.write(f"Words: {section['word_count']} (~{section['suggested_wpm']:.0f} wpm)\n")
            f.write("-" * 80 + "\n\n")
            
            # แยกเฉพาะ dialogue/narration (ไม่เอา headers)
            content_lines = []
            for line in section['content'].split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('**'):
                    # ลบ markdown formatting
                    line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)  # Bold
                    line = re.sub(r'\*(.+?)\*', r'\1', line)      # Italic
                    content_lines.append(line)
            
            f.write('\n'.join(content_lines))
            f.write("\n\n" + "=" * 80 + "\n\n")
    
    # 2. Detailed script with pause markers
    detailed_script = output_dir / "recording_script_DETAILED.txt"
    with open(detailed_script, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("  VOICEOVER RECORDING SCRIPT - WITH TIMING MARKERS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("INSTRUCTIONS:\n")
        f.write("- [PAUSE Xs] = หยุดชั่วคราว X วินาที\n")
        f.write("- [BREATH] = หายใจ (ไม่ให้ได้ยิน)\n")
        f.write("- [EMPHASIS] = เน้นน้ำเสียง\n")
        f.write("- Speed: ต้องอ่านให้ครบตามเวลาที่กำหนด\n\n")
        f.write("=" * 80 + "\n\n")
        
        for i, section in enumerate(sections, 1):
            f.write(f"═══ SECTION {i}/{len(sections)} ═══\n")
            f.write(f"⏱  {section['start']} → {section['end']} ({section['duration_sec']}s)\n")
            f.write(f"📝 {section['word_count']} words @ ~{section['suggested_wpm']:.0f} wpm\n")
            f.write(f"🎯 TARGET: Finish in {section['duration_sec']} seconds\n")
            f.write("─" * 80 + "\n\n")
            
            # เพิ่ม pause markers
            content_with_pauses = add_pause_markers(section['content'])
            
            # ลบ markdown headers แต่เก็บ pause
            lines = []
            for line in content_with_pauses.split('\n'):
                if line.strip() and not line.strip().startswith('#'):
                    line = re.sub(r'\*\*(.+?)\*\*', r'[EMPHASIS]\1[/EMPHASIS]', line)
                    lines.append(line)
            
            f.write('\n'.join(lines))
            f.write("\n\n[BREATH]\n")
            f.write("=" * 80 + "\n\n")
    
    # 3. JSON metadata สำหรับ automation ภายหลัง
    metadata = output_dir / "recording_metadata.json"
    with open(metadata, 'w', encoding='utf-8') as f:
        json.dump({
            'total_duration': sum(s['duration_sec'] for s in sections),
            'total_words': sum(s['word_count'] for s in sections),
            'sections': sections,
            'voice_guide': guide,
            'recording_tips': {
                'microphone': 'Use quality microphone in quiet room',
                'format': 'Record in WAV (48kHz, 16-bit) or MP3 (192+ kbps)',
                'room_treatment': 'Use blankets/foam to reduce echo',
                'hydration': 'Drink water before recording (avoid coffee/dairy)',
                'takes': 'Record 2-3 takes per section, pick the best',
                'editing': 'Use Audacity: Noise Reduction + Normalize to -3dB'
            }
        }, f, ensure_ascii=False, indent=2)
    
    # 4. Section breakdown (แยกไฟล์ละ section สำหรับ record ทีละส่วน)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)
    
    for i, section in enumerate(sections, 1):
        section_file = sections_dir / f"section_{i:02d}_{section['start'].replace(':', '')}-{section['end'].replace(':', '')}.txt"
        with open(section_file, 'w', encoding='utf-8') as f:
            f.write(f"SECTION {i}/{len(sections)}\n")
            f.write(f"Duration: {section['duration_sec']}s | Words: {section['word_count']} | Target: {section['suggested_wpm']:.0f} wpm\n")
            f.write("─" * 60 + "\n\n")
            
            # Clean content
            for line in section['content'].split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('**'):
                    line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
                    f.write(line + '\n')
    
    return simple_script, detailed_script, metadata, sections_dir


def main():
    parser = argparse.ArgumentParser(description="Prepare voiceover recording scripts")
    parser.add_argument('--input-dir', type=Path, required=True,
                       help='Input directory with script_validated.md and voiceover_guide.json')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory (default: audio/)')
    
    args = parser.parse_args()
    
    # Paths
    input_dir = args.input_dir
    output_dir = args.output_dir or Path('audio')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    script_file = input_dir / 'script_validated.md'
    guide_file = input_dir / 'voiceover_guide.json'
    
    # ตรวจสอบไฟล์
    if not script_file.exists():
        print(f"❌ Error: {script_file} not found!")
        return
    
    if not guide_file.exists():
        print(f"⚠️  Warning: {guide_file} not found, using defaults")
        guide = {'voice_profile': {'tone': 'warm, calm', 'speaking_rate': '120 wpm'}}
    else:
        guide = load_voiceover_guide(guide_file)
    
    print("🎙️  Preparing voiceover recording scripts...")
    print(f"📂 Input: {input_dir}")
    print(f"📂 Output: {output_dir}\n")
    
    # โหลดและประมวลผล
    script_content = load_script(script_file)
    sections = extract_script_sections(script_content)
    
    if not sections:
        print("❌ No sections found in script!")
        return
    
    print(f"✅ Found {len(sections)} sections")
    print(f"⏱  Total duration: {sum(s['duration_sec'] for s in sections)} seconds")
    print(f"📝 Total words: {sum(s['word_count'] for s in sections)}\n")
    
    # สร้างไฟล์
    simple, detailed, metadata, sections_dir = create_recording_script(sections, guide, output_dir)
    
    print("✅ Generated files:")
    print(f"   📄 {simple.name} - Simple script for reading")
    print(f"   📄 {detailed.name} - Detailed with timing markers")
    print(f"   📄 {metadata.name} - JSON metadata")
    print(f"   📁 {sections_dir.name}/ - Individual section files ({len(sections)} files)\n")
    
    print("🎯 NEXT STEPS:")
    print("   1. Read through recording_script_SIMPLE.txt")
    print("   2. Practice pronunciation and pacing")
    print("   3. Set up microphone in quiet room")
    print("   4. Record using Audacity or OBS Studio")
    print("   5. Follow timing in recording_script_DETAILED.txt")
    print("   6. Save as WAV (48kHz, 16-bit) or MP3 (192+ kbps)")
    print("\n💡 TIP: Record section-by-section using files in sections/ folder")


if __name__ == '__main__':
    main()
