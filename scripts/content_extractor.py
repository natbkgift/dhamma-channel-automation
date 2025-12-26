"""
Content Extractor Agent
แยกเฉพาะเนื้อหาที่ต้องพากย์เสียงออกมา
ลบ metadata, instructions, stage directions ออกทั้งหมด
"""

import re
from pathlib import Path
from typing import Tuple, Dict, List


class ContentExtractor:
    """
    Agent สำหรับแยกเฉพาะเนื้อหาจริงที่ต้องแปลงเป็นเสียง
    """
    
    def __init__(self):
        # Pattern สำหรับ metadata และ instructions
        self.metadata_patterns = [
            # Section headers
            r'^SECTION\s+\d+/\d+.*?$',
            r'^Time:.*?$',
            r'^Words:.*?$',
            r'^Duration:.*?$',
            
            # Separator lines
            r'^[=\-_~+]{3,}$',
            
            # Markdown headings and bullets (single char lines)
            r'^[#\-]+\s*$',
            r'^[#]{1,6}\s+',  # Markdown headings ## title
            
            # Key-value metadata lines
            r'^[\w\-]+\.\s+.+$',  # title. value, target. value
            r'^[\-]\.\s+.+$',  # -. value
            
            # Timestamps
            r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}',
            r'\(\d+s\)',
            
            # Labels/Headers (ที่ไม่ใช่เนื้อหาจริง)
            r'^(Hook|Introduction|Main Points|Practical Application|Benefits|Conclusion|CTA)\s*(\(.*?\))?:?\s*$',
            r'^Benefits?\s*&?\s*Motivation.*$',
            r'^Conclusion\s*&?\s*CTA.*$',
            r'^VOICEOVER\s+RECORDING\s+SCRIPT.*$',
            r'^\[.*SECTION.*\]$',  # [DEMO SECTION]
            r'^POINT\s+.+$',  # POINT หนึ่ง., POINT 1
            r'^PRACTICAL.*$',  # PRACTICAL.
            # Production notes and headings
            r'^(HOOK|INTRO|INTRODUCTION|MAIN\s+POINTS|PRACTICE|PRACTICAL|BENEFITS?|CONCLUSION|CTA)\b.*$',
            r'^(END\s*SCREEN)\b.*$',
            r'^(BACKGROUND\s*MUSIC|VOICE\.|SOUND\s*EFFECTS|CITATIONS?|KEY\s*POINTS|ICONS?|FONT)\b.*$',
            
            # Technical notes
            r'^Total Duration:.*?$',
            r'^Voice Style:.*?$',
            r'^Speaking Rate:.*?$',
        ]
        
        # Pattern สำหรับ stage directions
        self.direction_patterns = [
            # Square brackets (แต่เก็บ [PAUSE] ไว้!)
            r'\[VISUAL:.*?\]',
            r'\[MUSIC:.*?\]',
            r'\[B-ROLL:.*?\]',
            r'\[DEMO:.*?\]',
            r'\[CUT TO:.*?\]',
            r'\[TRANSITION:.*?\]',
            r'\[TONE:.*?\]',
            r'\[CUE:.*?\]',
            r'\[TEXT[^\]]*\]',
            r'\[CITATION[^\]]*\]',
            r'\[(?!PAUSE\b).*?\]',
            # NOTE: [PAUSE] จะไม่ถูกลบ เพราะต้องใช้ในการพากย์เสียง
            
            # Curly braces (technical instructions)
            r'\{.*?\}',
        ]
        
        # Pattern สำหรับบรรทัดที่เป็น instruction
        self.instruction_lines = [
            r'^-\s*เปิด:',
            r'^-\s*ปัญหา:',
            r'^-\s*คำตอบ:',
            r'^-\s*บอกว่า',
            r'^-\s*ทำไม',
            r'^-\s*ประโยชน์',
            r'^-\s*สรุป:',
            r'^-\s*เชิญชวน:',
            r'^-\s*CTA:',
            r'^-\s*ปิดท้าย:',
            r'^\d+\.\s+',  # numbered lists in instructions
        ]
    
    def extract_content(self, text: str) -> Tuple[str, Dict]:
        """
        แยกเฉพาะเนื้อหาที่ต้องพากย์เสียง
        
        Returns:
            Tuple[str, Dict]: (เนื้อหาสะอาด, metadata)
        """
        original_length = len(text)
        lines = text.split('\n')
        
        content_lines = []
        removed_count = {
            'metadata': 0,
            'directions': 0,
            'instructions': 0,
            'empty': 0
        }
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # ข้ามบรรทัดว่าง
            if not line:
                removed_count['empty'] += 1
                continue
            
            # ตรวจสอบว่าเป็น metadata หรือไม่
            is_metadata = False
            for pattern in self.metadata_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_metadata = True
                    removed_count['metadata'] += 1
                    break
            
            if is_metadata:
                continue
            
            # ตรวจสอบว่าเป็น instruction line หรือไม่
            is_instruction = False
            for pattern in self.instruction_lines:
                if re.match(pattern, line):
                    is_instruction = True
                    removed_count['instructions'] += 1
                    break
            
            if is_instruction:
                # แต่ถ้ามี quote ("...") ให้เอาเฉพาะ quote
                quotes = re.findall(r'"([^"]+)"', line)
                if quotes:
                    content_lines.extend(quotes)
                continue
            
            # ลบ stage directions ออก
            cleaned_line = line
            for pattern in self.direction_patterns:
                before = cleaned_line
                cleaned_line = re.sub(pattern, '', cleaned_line, flags=re.IGNORECASE)
                if before != cleaned_line:
                    removed_count['directions'] += 1
            
            cleaned_line = cleaned_line.strip()
            
            # ถ้ายังเหลือเนื้อหา ให้เก็บไว้
            if cleaned_line and len(cleaned_line) > 2:  # อย่างน้อย 3 ตัวอักษร
                content_lines.append(cleaned_line)
        
        # รวมเนื้อหา
        content = ' '.join(content_lines)
        
        # ทำความสะอาดเพิ่มเติม
        content = self._post_clean(content)
        
        # แยกประโยคยาวออกเป็นบรรทัดใหม่ (สำหรับ TTS)
        content = self._split_long_sentences(content)
        
        # สถิติ
        metadata = {
            'original_length': original_length,
            'original_lines': len(lines),
            'content_length': len(content),
            'content_bytes': len(content.encode('utf-8')),
            'reduction': f"{(1 - len(content)/original_length)*100:.1f}%",
            'removed': removed_count
        }
        
        return content, metadata
    
    def _post_clean(self, text: str) -> str:
        """ทำความสะอาดหลังรวมเนื้อหา"""
        
        # ลบ bullet points ที่เหลือ
        text = re.sub(r'^\s*[-•·]\s*', '', text)
        
        # ลบช่องว่างซ้ำ
        text = re.sub(r'\s+', ' ', text)
        
        # ลบวงเล็บเปล่า
        text = re.sub(r'\(\s*\)', '', text)
        text = re.sub(r'\[\s*\]', '', text)
        
        # แก้เครื่องหมายวรรคตอน
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([,.!?;:])([^\s])', r'\1 \2', text)
        
        # ลบเส้นแบ่งที่เหลือ
        text = re.sub(r'[-=_~+]{3,}', ' ', text)
        
        return text.strip()
    
    def _split_long_sentences(self, text: str) -> str:
        """แยกประโยคยาวออกเป็นบรรทัดใหม่ เพื่อให้ TTS ทำงานได้ดี (max 180 chars/line)"""
        
        # Step 1: แยก [PAUSE] เป็นบรรทัดใหม่ก่อนเสมอ
        text = re.sub(r'\s*(\[PAUSE[^\]]*\])\s*', r'\n\1\n', text)
        
        # Step 2: แทนที่ ... ด้วย . (เพื่อให้แยกประโยคได้)
        text = re.sub(r'\.\.\.+', '. ', text)
        
        # Step 3: แยกประโยคด้วย . ? ! และ :
        sentences = re.split(r'([.?!:])\s+', text)
        
        # รวม sentence กับ punctuation กลับเข้าด้วยกัน
        combined_sentences = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i+1] in '.?!:':
                combined_sentences.append(sentences[i] + sentences[i+1])
                i += 2
            else:
                if sentences[i].strip():
                    combined_sentences.append(sentences[i])
                i += 1
        
        # Step 4: รวมประโยคสั้นๆ เข้าด้วยกัน (ไม่เกิน 180 chars/บรรทัด)
        lines = []
        current_line = ""
        
        for sentence in combined_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # ถ้าเป็น [PAUSE] ให้อยู่บรรทัดเดียวเสมอ
            if sentence.startswith('[PAUSE'):
                if current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                lines.append(sentence)
                continue
            
            # ถ้าประโยคยาวเกิน 180 chars ให้แยกที่ dash (-)
            if len(sentence) > 180:
                parts = sentence.split(' - ')
                for part in parts:
                    part = part.strip()
                    if len(current_line) + len(part) > 180:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = part + " "
                    else:
                        current_line += part + " - "
            elif len(current_line) + len(sentence) > 180:
                if current_line:
                    lines.append(current_line.strip())
                current_line = sentence + " "
            else:
                current_line += sentence + " "
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        return '\n'.join(lines)
    
    def analyze(self, text: str) -> Dict:
        """วิเคราะห์เนื้อหาว่ามีอะไรบ้าง"""
        
        analysis = {
            'total_chars': len(text),
            'total_lines': len(text.split('\n')),
            'has_metadata': bool(re.search(r'SECTION\s+\d+/\d+', text)),
            'has_directions': bool(re.search(r'\[.*?\]', text)),
            'has_instructions': bool(re.search(r'^-\s+', text, re.MULTILINE)),
            'has_timestamps': bool(re.search(r'\d{2}:\d{2}', text)),
        }
        
        # นับจำนวน
        analysis['metadata_lines'] = len(re.findall(r'^SECTION\s+\d+/\d+', text, re.MULTILINE))
        analysis['direction_count'] = len(re.findall(r'\[.*?\]', text))
        analysis['instruction_lines'] = len(re.findall(r'^-\s+', text, re.MULTILINE))
        
        return analysis


def process_file(input_path: Path, output_path: Path = None, verbose: bool = True) -> Dict:
    """
    ประมวลผลไฟล์สคริปต์
    """
    
    extractor = ContentExtractor()
    
    # อ่านไฟล์
    with open(input_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    if verbose:
        print(f"📖 อ่านไฟล์: {input_path}")
        print(f"📊 ขนาดต้นฉบับ: {len(original_text):,} ตัวอักษร\n")
    
    # วิเคราะห์ต้นฉบับ
    if verbose:
        print("🔍 วิเคราะห์โครงสร้าง:")
        analysis = extractor.analyze(original_text)
        print(f"   • มี Section headers: {analysis['metadata_lines']} บรรทัด")
        print(f"   • มี Stage directions: {analysis['direction_count']} ชิ้น")
        print(f"   • มี Instructions: {analysis['instruction_lines']} บรรทัด\n")
    
    # แยกเนื้อหา
    if verbose:
        print("⚙️ กำลังแยกเนื้อหา...\n")
    
    content, metadata = extractor.extract_content(original_text)
    
    # แสดงผล
    if verbose:
        print("✨ ผลลัพธ์:")
        print(f"   • ขนาดเดิม: {metadata['original_length']:,} chars")
        print(f"   • ขนาดเนื้อหา: {metadata['content_length']:,} chars ({metadata['content_bytes']:,} bytes)")
        print(f"   • ลดลง: {metadata['reduction']}")
        print(f"\n   🗑️ ลบออก:")
        print(f"   • Metadata: {metadata['removed']['metadata']} บรรทัด")
        print(f"   • Directions: {metadata['removed']['directions']} ชิ้น")
        print(f"   • Instructions: {metadata['removed']['instructions']} บรรทัด")
        print(f"   • บรรทัดว่าง: {metadata['removed']['empty']} บรรทัด")
    
    # บันทึกไฟล์
    output_path = output_path or input_path.parent / f"{input_path.stem}_content_only{input_path.suffix}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if verbose:
        print(f"\n✅ บันทึกไฟล์: {output_path}")
    
    metadata['input_file'] = str(input_path)
    metadata['output_file'] = str(output_path)
    
    return metadata


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='แยกเฉพาะเนื้อหาที่ต้องพากย์เสียง')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='ไฟล์ input')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='ไฟล์ output (default: {input}_content_only.txt)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='ไม่แสดงรายละเอียด')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    if not input_path.exists():
        print(f"❌ ไม่พบไฟล์: {input_path}")
        exit(1)
    
    metadata = process_file(input_path, output_path, verbose=not args.quiet)
    
    print(f"\n🎉 เสร็จสิ้น!")
