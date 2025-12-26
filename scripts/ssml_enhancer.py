#!/usr/bin/env python3
"""
SSML Enhancer - ปรับปรุงสคริปต์ภาษาไทยให้เป็นธรรมชาติด้วย SSML
แปลงข้อความธรรมดาให้มีการหยุด เน้นเสียง และควบคุมน้ำเสียง

ใช้งาน:
    python ssml_enhancer.py input.txt output.txt
    python ssml_enhancer.py input.txt output.txt --level medium
"""

import re
import argparse
from pathlib import Path
from typing import Tuple


class SSMLEnhancer:
    """แปลงข้อความภาษาไทยเป็น SSML เพื่อให้เสียง TTS เป็นธรรมชาติ"""
    
    def __init__(self, enhancement_level: str = "medium"):
        """
        Args:
            enhancement_level: "light", "medium", "heavy"
                - light: เพิ่ม pause พื้นฐาน
                - medium: เพิ่ม pause + emphasis + prosody
                - heavy: เพิ่มทุกอย่าง + คำถาม + ตัวเลข
        """
        self.level = enhancement_level
    
    def enhance(self, text: str) -> str:
        """แปลงข้อความเป็น SSML"""
        
        # ลบ emoji ออก (TTS ไม่อ่าน)
        text = self._remove_emoji(text)
        
        # แปลง [PAUSE] tags ที่มีอยู่แล้ว (ทำก่อนหมด)
        text = self._convert_pause_tags(text)
        
        if self.level == "heavy":
            # ทำก่อน: เพิ่มน้ำเสียงขึ้นท้ายคำถาม
            text = self._enhance_questions(text)
            
            # ทำก่อน: ชะลอตัวเลข
            text = self._slow_down_numbers(text)
            
            # ทำก่อน: ชะลอคำศัพท์พิเศษ (บาลี/สันสกฤต)
            text = self._slow_down_pali_words(text)
        
        if self.level in ["medium", "heavy"]:
            # เพิ่ม pause ตามเครื่องหมายวรรคตอน
            text = self._add_punctuation_pauses(text)
            
            # ปรับจุดไข่ปลา ...
            text = self._enhance_ellipsis(text)
            
            # เน้นคำสำคัญ (ตัวหนา **)
            text = self._add_emphasis(text)
        
        # Wrap ด้วย <speak> tag
        text = f"<speak>\n{text}\n</speak>"
        
        return text
    
    def _remove_emoji(self, text: str) -> str:
        """ลบ emoji ออกจากข้อความ"""
        # Unicode ranges for emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)
    
    def _convert_pause_tags(self, text: str) -> str:
        """แปลง [PAUSE] tags เป็น SSML"""
        # [PAUSE - นิ่ง 3 วินาที พร้อม soft music] -> <break time="3s"/>
        text = re.sub(
            r'\[PAUSE\s*-\s*นิ่ง\s*(\d+)\s*วินาที[^\]]*\]',
            r'<break time="\1s"/>',
            text
        )
        
        # [PAUSE 2s] -> <break time="2s"/>
        text = re.sub(
            r'\[PAUSE\s+(\d+(?:\.\d+)?)(s|ms)\]',
            r'<break time="\1\2"/>',
            text,
            flags=re.IGNORECASE
        )
        
        # [PAUSE] -> <break time="0.8s"/>
        text = re.sub(
            r'\[PAUSE\]',
            '<break time="0.8s"/>',
            text
        )
        
        return text
    
    def _add_punctuation_pauses(self, text: str) -> str:
        """เพิ่ม pause ตามเครื่องหมายวรรคตอน"""
        # จุด ตกใจ คำถาม - pause ยาว
        text = re.sub(r'([.!?])(\s+)', r'\1<break time="0.6s"/>\2', text)
        
        # จุลภาค - pause สั้น
        text = re.sub(r',(\s+)', r',<break time="0.35s"/>\1', text)
        
        # ขีดกลาง - pause สั้นมาก
        text = re.sub(r'(\s+)-(\s+)', r'\1-<break time="0.25s"/>\2', text)
        
        return text
    
    def _enhance_ellipsis(self, text: str) -> str:
        """ปรับจุดไข่ปลา ... ให้มี pause และพูดช้าลง"""
        # ". .." หรือ "..." -> pause
        text = re.sub(
            r'\.\.\.(\s*)',
            r'<break time="0.6s"/>\1',
            text
        )
        
        return text
    
    def _add_emphasis(self, text: str) -> str:
        """เพิ่มการเน้นเสียงให้คำที่อยู่ใน **คำ**"""
        # **คำ** -> <emphasis>คำ</emphasis>
        text = re.sub(
            r'\*\*(.+?)\*\*',
            r'<emphasis level="strong">\1</emphasis>',
            text
        )
        
        # *คำ* -> <emphasis level="moderate">
        text = re.sub(
            r'\*(.+?)\*',
            r'<emphasis level="moderate">\1</emphasis>',
            text
        )
        
        return text
    
    def _enhance_questions(self, text: str) -> str:
        """เพิ่มน้ำเสียงขึ้นท้ายคำถาม"""
        # หาประโยคคำถามภาษาไทย (ลงท้ายด้วย ?)
        # เพิ่ม pitch ขึ้นเล็กน้อย
        
        def add_question_intonation(match):
            question = match.group(1)
            # ถ้าประโยคสั้นกว่า 100 ตัวอักษร ใช้ pitch สูงกว่า
            if len(question) < 100:
                return f'<prosody pitch="+2st">{question}</prosody>?'
            else:
                return f'<prosody pitch="+1st">{question}</prosody>?'
        
        # Pattern: ตัวอักษรไทย/อังกฤษ/เว้นวรรค + ?
        # ไม่รวม tags
        text = re.sub(
            r'([\u0E00-\u0E7F\w\s,.-]+?)\?',
            add_question_intonation,
            text
        )
        
        return text
    
    def _slow_down_numbers(self, text: str) -> str:
        """ชะลอการพูดตัวเลข/เปอร์เซ็นต์ (ไม่รวมตัวเลขใน tags)"""
        # ตัวเลข + % หรือ ตัวเลขเดี่ยว (ไม่อยู่ใน < >)
        def replace_number(match):
            num = match.group(0)
            return f'<prosody rate="88%">{num}</prosody>'
        
        # จับตัวเลขที่ไม่อยู่ใน < >
        text = re.sub(
            r'(?<![<>])\b(\d+(?:\.\d+)?%?)\b(?![<>])',
            replace_number,
            text
        )
        
        return text
    
    def _slow_down_pali_words(self, text: str) -> str:
        """ชะลอคำบาลี/สันสกฤต"""
        pali_words = [
            'อานาปานสติ',
            'พระไตรปิฎก',
            'มัชฌิมนิกาย',
            'วิสุทธิมรรค',
            'สติปัฏฐาน',
            'อริยสัจ',
            'นิพพาน',
            'สมาธิ',
            'ปัญญา',
            'วิปัสสนา',
            'มหาสติปัฏฐาน'
        ]
        
        for word in pali_words:
            # ชะลอความเร็ว + เพิ่มความชัดเจน
            text = re.sub(
                rf'\b({word})\b',
                r'<prosody rate="85%">\1</prosody>',
                text
            )
        
        return text
    
    def process_file(self, input_path: Path, output_path: Path) -> dict:
        """ประมวลผลไฟล์และบันทึก"""
        # อ่านไฟล์
        with open(input_path, 'r', encoding='utf-8') as f:
            original_text = f.read()
        
        # แปลง
        enhanced_text = self.enhance(original_text)
        
        # บันทึก
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_text)
        
        # สถิติ
        metadata = {
            'original_length': len(original_text),
            'enhanced_length': len(enhanced_text),
            'ssml_tags': len(re.findall(r'<[^>]+>', enhanced_text)),
            'breaks': len(re.findall(r'<break', enhanced_text)),
            'emphasis': len(re.findall(r'<emphasis', enhanced_text)),
            'prosody': len(re.findall(r'<prosody', enhanced_text)),
        }
        
        return metadata


def main():
    parser = argparse.ArgumentParser(
        description="SSML Enhancer - ปรับสคริปต์ให้เสียง TTS เป็นธรรมชาติ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Enhancement Levels:
  light      เพิ่ม pause พื้นฐานเท่านั้น (เร็ว)
  medium     เพิ่ม pause + emphasis + prosody (แนะนำ)
  heavy      เพิ่มทุกอย่าง รวมถึงคำถาม ตัวเลข (ช้า แต่ละเอียด)

ตัวอย่าง:
  python ssml_enhancer.py script.txt script_ssml.txt
  python ssml_enhancer.py script.txt script_ssml.txt --level heavy
        """
    )
    
    parser.add_argument('input', type=Path, help='Input text file')
    parser.add_argument('output', type=Path, help='Output SSML file')
    parser.add_argument('--level', type=str, default='medium',
                       choices=['light', 'medium', 'heavy'],
                       help='Enhancement level (default: medium)')
    parser.add_argument('--preview', action='store_true',
                       help='แสดงตัวอย่างแทนการบันทึกไฟล์')
    
    args = parser.parse_args()
    
    # ตรวจสอบไฟล์
    if not args.input.exists():
        print(f"❌ ไม่พบไฟล์: {args.input}")
        return 1
    
    print(f"🔧 SSML Enhancer - Level: {args.level}")
    print(f"📄 Input: {args.input}")
    
    # ประมวลผล
    enhancer = SSMLEnhancer(enhancement_level=args.level)
    
    if args.preview:
        # Preview mode
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        
        enhanced = enhancer.enhance(text)
        
        print("\n" + "="*60)
        print("SSML Preview (first 1000 characters):")
        print("="*60)
        print(enhanced[:1000])
        if len(enhanced) > 1000:
            print("\n... (truncated)")
        print("="*60)
        
    else:
        # บันทึกไฟล์
        metadata = enhancer.process_file(args.input, args.output)
        
        print(f"✅ Output: {args.output}")
        print(f"\n📊 Statistics:")
        print(f"   • Original length: {metadata['original_length']:,} chars")
        print(f"   • Enhanced length: {metadata['enhanced_length']:,} chars")
        print(f"   • SSML tags added: {metadata['ssml_tags']}")
        print(f"      - <break>: {metadata['breaks']}")
        print(f"      - <emphasis>: {metadata['emphasis']}")
        print(f"      - <prosody>: {metadata['prosody']}")
        
        print(f"\n💡 Next step:")
        print(f"   python scripts/tts_unified.py \\")
        print(f"     --provider google \\")
        print(f"     --script \"{args.output}\" \\")
        print(f"     --output \"output.mp3\" \\")
        print(f"     --voice th-TH-Journey-D \\")
        print(f"     --rate 0.88")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
