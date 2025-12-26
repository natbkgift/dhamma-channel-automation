"""
TTS Text Preprocessor Agent
ทำความสะอาดและปรับแต่งข้อความก่อนส่งไปสร้างเสียง
เพื่อให้เสียง AI ออกมาธรรมชาติและเหมาะกับช่องธรรมะ
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


class TTSPreprocessor:
    """
    Agent สำหรับปรับแต่งข้อความก่อนทำ TTS
    - ลบแทก markdown, HTML
    - ลบอีโมจิและสัญลักษณ์พิเศษ
    - ปรับคำย่อและตัวเลข
    - จัดการเครื่องหมายวรรคตอน
    """
    
    def __init__(self):
        # รูปแบบที่ต้องลบออก
        self.removal_patterns = [
            # Markdown headers
            (r'^#{1,6}\s+', ''),
            
            # Markdown bold/italic
            (r'\*\*(.+?)\*\*', r'\1'),  # **bold** → bold
            (r'\*(.+?)\*', r'\1'),      # *italic* → italic
            (r'__(.+?)__', r'\1'),      # __bold__ → bold
            (r'_(.+?)_', r'\1'),        # _italic_ → italic
            
            # Markdown links
            (r'\[(.+?)\]\(.+?\)', r'\1'),  # [text](url) → text
            
            # HTML tags
            (r'<[^>]+>', ''),
            
            # Hashtags (แทก)
            (r'#\w+', ''),
            
            # Mentions
            (r'@\w+', ''),
            
            # URLs
            (r'https?://\S+', ''),
            (r'www\.\S+', ''),
            
            # Emojis (Unicode ranges)
            (r'[\U0001F600-\U0001F64F]', ''),  # Emoticons
            (r'[\U0001F300-\U0001F5FF]', ''),  # Symbols & Pictographs
            (r'[\U0001F680-\U0001F6FF]', ''),  # Transport & Map
            (r'[\U0001F1E0-\U0001F1FF]', ''),  # Flags
            (r'[\U00002702-\U000027B0]', ''),  # Dingbats
            (r'[\U000024C2-\U0001F251]', ''),  # Enclosed characters
            
            # อักขระพิเศษที่ไม่ใช่เครื่องหมายวรรคตอน
            (r'[★☆✓✔✗✘►▶◄◀▲▼●○■□]', ''),
            
            # เครื่องหมายคณิตศาสตร์และสัญลักษณ์
            (r'[=]{2,}', ''),  # เท่ากับซ้ำๆ ==== → ลบ
            (r'[-]{3,}', ''),  # ขีดซ้ำๆ ---- → ลบ
            (r'[_]{3,}', ''),  # ขีดล่างซ้ำๆ ____ → ลบ
            (r'[~]{2,}', ''),  # tilde ซ้ำๆ ~~~~ → ลบ
            (r'[+]{2,}', ''),  # บวกซ้ำๆ ++++ → ลบ
            
            # Separator lines (เส้นแบ่ง)
            (r'^[=\-_~+]{3,}$', '', re.MULTILINE),
            
            # Bullet points และ list markers
            (r'^\s*[-•·]\s+', '', re.MULTILINE),
            (r'^\s*\d+\.\s+', '', re.MULTILINE),  # 1. 2. 3.
            
            # ลบวงเล็บเปล่า
            (r'\(\s*\)', ''),
            (r'\[\s*\]', ''),
        ]
        
        # คำย่อที่ควรขยาย
        self.abbreviations = {
            # ภาษาไทย
            'ม.': 'มหาวิทยาลัย',
            'ดร.': 'ดอกเตอร์',
            'ผศ.': 'ผู้ช่วยศาสตราจารย์',
            'รศ.': 'รองศาสตราจารย์',
            'ศ.': 'ศาสตราจารย์',
            'พ.ศ.': 'พุทธศักราช',
            'ค.ศ.': 'คริสต์ศักราช',
            'อ.': 'อำเภอ',
            'จ.': 'จังหวัด',
            'ต.': 'ตำบล',
            
            # ภาษาอังกฤษ
            'Mr.': 'Mister',
            'Mrs.': 'Missis',
            'Dr.': 'Doctor',
            'Prof.': 'Professor',
        }
        
        # คำพิเศษสำหรับธรรมะที่ต้องออกเสียงถูกต้อง
        self.dhamma_terms = {
            'พระพุทธเจ้า': 'พระ-พุทธ-เจ้า',
            'พระอริยเจ้า': 'พระ-อะริยะ-เจ้า',
            'มัชฌิมาปฏิปทา': 'มัด-ฌิ-มา-ปะฏิ-ปะทา',
            'อนาปานสติ': 'อะนา-ปา-นะ-สะติ',
            'วิปัสสนา': 'วิ-ปัด-สะนา',
            'สมถะ': 'สะมะทะ',
            # เพิ่มเติมได้ตามต้องการ
        }
    
    def preprocess(self, text: str) -> Tuple[str, Dict[str, any]]:
        """
        ประมวลผลข้อความทั้งหมด
        
        Returns:
            Tuple[str, Dict]: (ข้อความที่ปรับแล้ว, metadata)
        """
        original_length = len(text)
        metadata = {
            'original_length': original_length,
            'original_bytes': len(text.encode('utf-8')),
            'changes': []
        }
        
        # 1. ลบส่วนที่ไม่ต้องการอ่าน
        text, removed = self._remove_non_speech_content(text)
        if removed:
            metadata['changes'].append(f"Removed: {', '.join(removed)}")
        
        # 2. ทำความสะอาดรูปแบบต่างๆ
        text = self._clean_formatting(text)
        metadata['changes'].append("Cleaned formatting")
        
        # 3. ขยายคำย่อ
        text, expanded = self._expand_abbreviations(text)
        if expanded:
            metadata['changes'].append(f"Expanded {len(expanded)} abbreviations")
        
        # 4. จัดการตัวเลข
        text = self._process_numbers(text)
        metadata['changes'].append("Processed numbers")
        
        # 5. ปรับเครื่องหมายวรรคตอน
        text = self._fix_punctuation(text)
        metadata['changes'].append("Fixed punctuation")
        
        # 6. ลบช่องว่างเกิน
        text = self._clean_whitespace(text)
        
        # 7. แบ่งประโยคยาวเกินไป (ลด max เหลือ 70 เพราะ Google TTS เข้มงวดมาก)
        text = self._split_long_sentences(text, max_length=70)
        
        metadata['final_length'] = len(text)
        metadata['final_bytes'] = len(text.encode('utf-8'))
        metadata['reduction'] = f"{(1 - len(text)/original_length)*100:.1f}%"
        
        return text, metadata
    
    def _remove_non_speech_content(self, text: str) -> Tuple[str, List[str]]:
        """ลบส่วนที่ไม่ควรอ่านออกเสียง"""
        removed = []
        
        # ลบส่วน metadata (บรรทัดที่ขึ้นต้นด้วย emoji หรือ symbols)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # ข้ามบรรทัดว่าง
            if not line:
                cleaned_lines.append('')
                continue
            
            # ลบบรรทัดที่เป็นแทก (ขึ้นต้นด้วย #)
            if line.startswith('#') and ' ' not in line[:20]:
                removed.append('hashtags')
                continue
            
            # ลบบรรทัดที่เป็น metadata (มี emoji หรือ :: ที่ต้นบรรทัด)
            if re.match(r'^[\U0001F300-\U0001F9FF]', line):
                removed.append('emoji lines')
                continue
            
            if line.startswith('::'):
                removed.append('metadata')
                continue
            
            # ลบบรรทัดที่เป็นลิงก์ล้วนๆ
            if line.startswith('http') or line.startswith('www.'):
                removed.append('urls')
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), list(set(removed))
    
    def _clean_formatting(self, text: str) -> str:
        """ลบ markdown และ formatting ต่างๆ"""
        for pattern, replacement, *flags in self.removal_patterns:
            flag = flags[0] if flags else 0
            text = re.sub(pattern, replacement, text, flags=flag)
        
        return text
    
    def _expand_abbreviations(self, text: str) -> Tuple[str, List[str]]:
        """ขยายคำย่อ"""
        expanded = []
        
        for abbr, full in self.abbreviations.items():
            if abbr in text:
                text = text.replace(abbr, full)
                expanded.append(abbr)
        
        return text, expanded
    
    def _process_numbers(self, text: str) -> str:
        """แปลงตัวเลขเป็นคำ (สำหรับเลขง่ายๆ)"""
        
        # แปลงเลขไทย
        thai_numbers = {
            '0': 'ศูนย์', '1': 'หนึ่ง', '2': 'สอง', '3': 'สาม', '4': 'สี่',
            '5': 'ห้า', '6': 'หก', '7': 'เจ็ด', '8': 'แปด', '9': 'เก้า',
            '10': 'สิบ', '20': 'ยี่สิบ', '30': 'สามสิบ', '100': 'หนึ่งร้อย',
        }
        
        # แปลงตัวเลขอย่างง่าย (1-100)
        def replace_simple_number(match):
            num = int(match.group(0))
            if num in range(1, 11):
                return ['หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า', 'สิบ'][num-1]
            elif num == 20:
                return 'ยี่สิบ'
            elif num < 100:
                tens = num // 10
                ones = num % 10
                result = ['', 'สิบ', 'ยี่สิบ', 'สามสิบ', 'สี่สิบ', 'ห้าสิบ', 'หกสิบ', 'เจ็ดสิบ', 'แปดสิบ', 'เก้าสิบ'][tens]
                if ones > 0:
                    if ones == 1 and tens > 0:
                        result += 'เอ็ด'
                    else:
                        result += ['', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า'][ones]
                return result
            return match.group(0)
        
        # แปลงเฉพาะตัวเลข standalone (ไม่ติดกับตัวอักษร)
        text = re.sub(r'\b(\d{1,2})\b', replace_simple_number, text)
        
        # แปลง percentages
        text = re.sub(r'(\d+)%', r'\1 เปอร์เซ็นต์', text)
        
        return text
    
    def _fix_punctuation(self, text: str) -> str:
        """ปรับเครื่องหมายวรรคตอนให้เหมาะกับการอ่าน"""
        
        # ลบอักขระซ้ำๆ ที่ไม่จำเป็น
        text = re.sub(r'[=]{2,}', ' ', text)  # เท่ากับซ้ำๆ
        text = re.sub(r'[-]{3,}', ' ', text)  # ขีดซ้ำๆ
        text = re.sub(r'[_]{3,}', ' ', text)  # ขีดล่างซ้ำๆ
        text = re.sub(r'[~]{2,}', ' ', text)  # tilde ซ้ำๆ
        text = re.sub(r'[+]{2,}', ' ', text)  # บวกซ้ำๆ
        text = re.sub(r'[*]{2,}', ' ', text)  # ดอกจันซ้ำๆ
        
        # เพิ่ม space หลังเครื่องหมายวรรคตอน
        text = re.sub(r'([,.!?;:])([^\s])', r'\1 \2', text)
        
        # ลบ multiple punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{2,}', '...', text)  # ... คือ ellipsis
        
        # แปลง ... เป็นจุด (AI อ่าน ... ได้ไม่ดี)
        text = re.sub(r'\.{3,}', '.', text)
        
        # ลบ punctuation ซ้อนกัน เช่น ,. หรือ ;,
        text = re.sub(r'[,;]\s*[,;.!?]', '.', text)
        
        # แปลง : ที่ไม่ใช่เวลา เป็นจุด
        text = re.sub(r':\s*(?!\d)', '. ', text)
        
        return text
    
    def _clean_whitespace(self, text: str) -> str:
        """ลบช่องว่างเกิน"""
        
        # ลบช่องว่างหลายตัวเป็น 1 ตัว
        text = re.sub(r' +', ' ', text)
        
        # ลบช่องว่างต้น/ท้ายบรรทัด
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        # ลบบรรทัดว่างเกิน
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # ลบช่องว่างก่อนเครื่องหมายวรรคตอน
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        return text.strip()
    
    def _split_long_sentences(self, text: str, max_length: int = 70) -> str:
        """แบ่งประโยคยาวเกินไป - บังคับแยกทุกบรรทัดที่ยาวกว่า max_length"""
        
        lines = text.split('\n')
        result = []
        
        for line in lines:
            line = line.strip()
            if not line:
                result.append('')
                continue
            
            # ถ้าเป็น [PAUSE] เก็บไว้ตามเดิม
            if line.startswith('[PAUSE'):
                result.append(line)
                continue
            
            # บังคับตัดทุกบรรทัดที่ยาวกว่า max_length
            while len(line) > max_length:
                # หาตำแหน่งตัดที่ดีที่สุด (ที่มี space, comma, period)
                cut_pos = max_length
                
                # ลองหา . ก่อน
                last_period = line[:max_length].rfind('.')
                # ลองหา space
                last_space = line[:max_length].rfind(' ')
                # ลองหา comma
                last_comma = line[:max_length].rfind(',')
                
                # เลือกตำแหน่งที่ดีที่สุด
                cut_pos = max(last_period, last_space, last_comma)
                if cut_pos <= 0:
                    cut_pos = max_length
                
                # ตัดและเพิ่มเข้า result
                part = line[:cut_pos+1].strip()
                if part:
                    # เพิ่มจุดถ้าไม่มี
                    if not part.endswith(('.', '!', '?', ']')):
                        part += '.'
                    result.append(part)
                
                # เก็บส่วนที่เหลือ
                line = line[cut_pos+1:].strip()
            
            # เพิ่มส่วนสุดท้าย (ถ้ามี)
            if line:
                if not line.endswith(('.', '!', '?', ']')):
                    line += '.'
                result.append(line)
        
        return '\n'.join(result)
    
    def _split_by_punctuation(self, text: str, max_length: int, result: list):
        """แยกข้อความยาวด้วยเครื่องหมายวรรคตอน - DEPRECATED ใช้ _split_long_sentences แทน"""
        pass
    
    def analyze_text(self, text: str) -> Dict[str, any]:
        """วิเคราะห์ข้อความและแสดงสถิติ"""
        
        analysis = {
            'total_chars': len(text),
            'total_bytes': len(text.encode('utf-8')),
            'total_words': len(text.split()),
            'total_lines': len(text.split('\n')),
            'has_hashtags': bool(re.search(r'#\w+', text)),
            'has_urls': bool(re.search(r'https?://\S+', text)),
            'has_emojis': bool(re.search(r'[\U0001F300-\U0001F9FF]', text)),
            'has_markdown': bool(re.search(r'\*\*|\*|__|_|#{1,6}\s', text)),
            'sentences': len(re.findall(r'[.!?]+', text)),
        }
        
        # ตรวจสอบประโยคยาว
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        long_sentences = [s for s in sentences if len(s) > 150]
        
        analysis['long_sentences'] = len(long_sentences)
        if long_sentences:
            analysis['longest_sentence_chars'] = max(len(s) for s in long_sentences)
        
        return analysis


def process_file(input_path: Path, output_path: Path = None, verbose: bool = True) -> Dict:
    """
    ประมวลผลไฟล์สคริปต์
    
    Args:
        input_path: ไฟล์ input
        output_path: ไฟล์ output (ถ้าไม่ระบุจะเขียนทับ input)
        verbose: แสดงรายละเอียด
    
    Returns:
        Dict: metadata และสถิติ
    """
    
    preprocessor = TTSPreprocessor()
    
    # อ่านไฟล์
    with open(input_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    if verbose:
        print(f"📖 อ่านไฟล์: {input_path}")
        print(f"📊 ขนาดต้นฉบับ: {len(original_text):,} ตัวอักษร")
    
    # วิเคราะห์ต้นฉบับ
    if verbose:
        print("\n🔍 วิเคราะห์ต้นฉบับ:")
        analysis = preprocessor.analyze_text(original_text)
        for key, value in analysis.items():
            if value and value is not False:
                print(f"   • {key}: {value}")
    
    # ประมวลผล
    if verbose:
        print("\n⚙️ กำลังประมวลผล...")
    
    cleaned_text, metadata = preprocessor.preprocess(original_text)
    
    # แสดงผลการเปลี่ยนแปลง
    if verbose:
        print(f"\n✨ ผลลัพธ์:")
        print(f"   • ขนาดเดิม: {metadata['original_length']:,} chars ({metadata['original_bytes']:,} bytes)")
        print(f"   • ขนาดใหม่: {metadata['final_length']:,} chars ({metadata['final_bytes']:,} bytes)")
        print(f"   • ลดลง: {metadata['reduction']}")
        print(f"   • การเปลี่ยนแปลง:")
        for change in metadata['changes']:
            print(f"     - {change}")
    
    # บันทึกไฟล์
    output_path = output_path or input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)
    
    if verbose:
        print(f"\n✅ บันทึกไฟล์: {output_path}")
    
    metadata['input_file'] = str(input_path)
    metadata['output_file'] = str(output_path)
    
    return metadata


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ทำความสะอาดข้อความสำหรับ TTS')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='ไฟล์ input')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='ไฟล์ output (default: {input}_cleaned.txt)')
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
