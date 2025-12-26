#!/usr/bin/env python3
"""
Google Cloud TTS Generator - สร้างเสียงบรรยายด้วย Google Cloud Text-to-Speech
รองรับเสียงภาษาไทยเนทีฟ (WaveNet & Neural2)
รองรับ [PAUSE] tags สำหรับการหยุดจังหวะธรรมชาติ
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
except ImportError:
    print("❌ ไม่พบ google-cloud-texttospeech library")
    print("💡 ติดตั้งด้วย: pip install google-cloud-texttospeech")
    sys.exit(1)


def load_config():
    """โหลด Google Cloud credentials จาก .env หรือ production_config.json"""
    # ลองโหลดจาก .env ก่อน
    load_dotenv()
    
    # วิธีที่ 1: Service Account JSON file path
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    if credentials_path and Path(credentials_path).exists():
        print(f"✅ พบ credentials file: {credentials_path}")
        return credentials_path, None
    
    # วิธีที่ 2: Service Account JSON content ใน .env
    credentials_json = os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON', '')
    if credentials_json:
        print("✅ พบ credentials JSON ใน .env")
        return None, json.loads(credentials_json)
    
    # วิธีที่ 3: จาก production_config.json
    config_path = Path.cwd() / 'production_config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        credentials_json = config.get('google_cloud_credentials_json', '')
        if credentials_json:
            print("✅ พบ credentials JSON ใน production_config.json")
            if isinstance(credentials_json, str):
                credentials_json = json.loads(credentials_json)
            return None, credentials_json
    
    raise ValueError(
        "❌ ไม่พบ Google Cloud credentials\n"
        "กรุณาตั้งค่าอย่างใดอย่างหนึ่ง:\n"
        "1. GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json ใน .env\n"
        "2. GOOGLE_CLOUD_CREDENTIALS_JSON={...} ใน .env\n"
        "3. google_cloud_credentials_json ใน production_config.json"
    )


def get_available_voices():
    """แสดงรายการเสียงภาษาไทยที่มี"""
    voices = {
        "journey": {
            "th-TH-Journey-D": "🧘‍♂️ ผู้ชาย - อบอุ่น เป็นธรรมชาติ (⭐ แนะนำที่สุด!)",
            "th-TH-Journey-F": "👩 ผู้หญิง - นุ่มนวล เป็นมิตร (⭐ แนะนำ!)",
            "th-TH-Journey-O": "🧘‍♂️ ผู้ชาย - สงบ เหมาะกับธรรมะ",
        },
        "chirp3": {
            "th-TH-Chirp3-HD-Schedar": "🧘‍♂️ ผู้ชาย - นุ่มสงบ (ดี)",
            "th-TH-Chirp3-HD-Achird": "🧘‍♂️ ผู้ชาย - ธรรมชาติ",
            "th-TH-Chirp3-HD-Umbriel": "🧘‍♂️ ผู้ชาย - เสียงลึก",
            "th-TH-Chirp3-HD-Alnilam": "🧘‍♂️ ผู้ชาย - ชัดเจน",
            "th-TH-Chirp3-HD-Charon": "🧘‍♂️ ผู้ชาย - มั่นคง",
            "th-TH-Chirp3-HD-Achernar": "👩 ผู้หญิง - นุ่มนวล",
        },
        "neural2": {
            "th-TH-Neural2-C": "👩 ผู้หญิง - โทนกลาง คุณภาพสูง",
        },
        "wavenet": {
            "th-TH-Wavenet-B": "🧘‍♂️ ผู้ชาย - โทนเป็นกันเอง",
            "th-TH-Wavenet-D": "🧘‍♂️ ผู้ชาย - โทนมั่นใจ",
        },
        "standard": {
            "th-TH-Standard-A": "👩 ผู้หญิง - เสียงมาตรฐาน (ฟรี)",
        }
    }
    return voices


def convert_pause_to_ssml(text: str) -> tuple[str, bool]:
    """
    แปลง [PAUSE] tags เป็น SSML <break> tags
    
    Examples:
        [PAUSE] -> <break time="1s"/>
        [PAUSE 2s] -> <break time="2s"/>
        [PAUSE 500ms] -> <break time="500ms"/>
    
    Returns:
        (converted_text, has_ssml): ข้อความที่แปลงแล้ว และ flag ว่ามี SSML หรือไม่
    """
    has_pause = bool(re.search(r'\[PAUSE[^\]]*\]', text))
    
    if not has_pause:
        return text, False
    
    # แปลง [PAUSE] และ [PAUSE Xs] เป็น SSML
    def replace_pause(match):
        full_match = match.group(0)
        
        # แยก duration ออกมา
        duration_match = re.search(r'\[PAUSE\s+(\d+(?:\.\d+)?)(s|ms)?\]', full_match, re.IGNORECASE)
        
        if duration_match:
            value = duration_match.group(1)
            unit = duration_match.group(2) or 's'  # default เป็นวินาที
            return f'<break time="{value}{unit}"/>'
        else:
            # [PAUSE] แบบไม่มีระบุเวลา ใช้ 1s
            return '<break time="1s"/>'
    
    converted = re.sub(r'\[PAUSE[^\]]*\]', replace_pause, text, flags=re.IGNORECASE)
    
    # Wrap ด้วย <speak> tag สำหรับ SSML
    ssml_text = f"<speak>{converted}</speak>"
    
    return ssml_text, True


def generate_tts_google(
    text: str,
    output_path: Path,
    voice_name: str = "th-TH-Chirp3-HD-Schedar",
    speaking_rate: float = 0.80,
    pitch: float = 0.0,
    credentials_path: str = None,
    credentials_dict: dict = None,
    use_ssml: bool = False
):
    """
    สร้างเสียงจากข้อความด้วย Google Cloud TTS
    
    Args:
        text: ข้อความที่ต้องการแปลงเป็นเสียง
        output_path: ไฟล์เสียงที่ต้องการบันทึก
        voice_name: ชื่อเสียง (th-TH-Wavenet-B, th-TH-Neural2-A, etc.)
        speaking_rate: ความเร็วในการพูด (0.25 - 4.0, ค่าปกติ 1.0)
        pitch: ระดับเสียง (-20.0 - 20.0, ค่าปกติ 0.0)
        credentials_path: path ไปยัง service account JSON file
        credentials_dict: dictionary ของ service account credentials
    """
    print("🎙️ กำลังสร้างเสียงด้วย Google Cloud TTS...")
    
    try:
        # สร้าง client
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client = texttospeech.TextToSpeechClient(credentials=credentials)
        elif credentials_dict:
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            client = texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            # ใช้ default credentials
            client = texttospeech.TextToSpeechClient()
        
        print(f"✅ เชื่อมต่อ Google Cloud TTS สำเร็จ")
        
    except Exception as e:
        print(f"❌ ไม่สามารถเชื่อมต่อ Google Cloud TTS: {e}")
        return False
    
    # ตรวจสอบความยาวข้อความ (Google นับเป็น bytes ไม่ใช่ characters)
    text_bytes = len(text.encode('utf-8'))
    text_length = len(text)
    print(f"📝 ความยาวสคริปต์: {text_length:,} ตัวอักษร ({text_bytes:,} bytes)")
    
    # Google Cloud TTS limit: 5,000 bytes (ไม่ใช่ characters!)
    # ภาษาไทย 1 ตัวอักษร ≈ 3 bytes (UTF-8)
    MAX_BYTES = 4800  # เหลือที่ว่างสำหรับความปลอดภัย
    
    if text_bytes > MAX_BYTES:
        print(f"⚠️ ข้อความยาวเกิน {MAX_BYTES} bytes ({text_bytes:,} bytes) จะแบ่งเป็นหลายส่วน...")
        
        # แบ่งข้อความเป็นส่วนๆ ตาม byte limit
        # แยกที่ . ! ? และ \n (newline) เพื่อให้แต่ละบรรทัดเป็น sentence
        chunks = []
        # ถ้ามี SSML ให้แกะ <speak> ออกก่อนค่อยตัดชิ้น เพื่อไม่ให้แท็กคาบเกี่ยวข้ามชิ้น
        working_text = text
        if use_ssml:
            working_text = working_text.replace('<speak>', '').replace('</speak>', '')
        lines = working_text.split('\n')
        current_chunk = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # ถ้าบรรทัดไม่มีเครื่องหมายจบประโยค ให้เพิ่มจุด (ยกเว้น [PAUSE] และบรรทัดที่เป็น SSML tag ล้วนๆ)
            if not line[-1] in '.!?' and not line.startswith('[PAUSE'):
                tag_like = line.startswith('<') and line.endswith('>')
                if not tag_like:
                    line += '.'
            
            test_chunk = current_chunk + '\n' + line if current_chunk else line
            test_bytes = len(test_chunk.encode('utf-8'))
            
            if test_bytes > MAX_BYTES:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line
            else:
                current_chunk = test_chunk
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        print(f"📦 แบ่งเป็น {len(chunks)} ส่วน")
        
        # สร้างเสียงแต่ละส่วน
        audio_files = []
        for i, chunk in enumerate(chunks, 1):
            chunk_bytes = len(chunk.encode('utf-8'))
            print(f"\n🎙️ ส่วนที่ {i}/{len(chunks)} ({len(chunk):,} ตัวอักษร, {chunk_bytes:,} bytes)")
            
            chunk_output = output_path.parent / f"temp_chunk_{i:03d}.mp3"
            
            # สร้างเสียง (ถ้า text มี SSML อยู่แล้วจาก parent, ใช้ตรงๆ)
            # ถ้ายังไม่มี SSML, แปลง chunk นี้ใหม่
            if use_ssml:
                # wrap ใหม่สำหรับแต่ละ chunk (chunk ณ ตอนนี้ไม่มี <speak> คงค้างแล้ว)
                chunk_ssml_text = f"<speak>{chunk.strip()}</speak>"
                synthesis_input = texttospeech.SynthesisInput(ssml=chunk_ssml_text)
            else:
                # ไม่มี SSML เลย ใช้ text ธรรมดา
                synthesis_input = texttospeech.SynthesisInput(text=chunk)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="th-TH",
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch
            )
            
            # เรียก API พร้อมแสดงตัวอย่างข้อความสั้นๆ สำหรับดีบักเมื่อมีปัญหา
            try:
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            except Exception as e:
                preview = chunk.replace('\n', ' ')[:160]
                print(f"   ⚠️ Chunk {i} failed: {e}\n   ↳ Preview: {preview}...")
                return False
            
            # บันทึกไฟล์
            with open(chunk_output, "wb") as out:
                out.write(response.audio_content)
            
            audio_files.append(chunk_output)
            print(f"   ✓ บันทึก {chunk_output.name}")
        
        # รวมไฟล์เสียง
        print("\n🔄 กำลังรวมไฟล์เสียง...")
        try:
            with open(output_path, 'wb') as outfile:
                for audio_file in audio_files:
                    with open(audio_file, 'rb') as infile:
                        outfile.write(infile.read())
            
            # ลบไฟล์ชั่วคราว
            for audio_file in audio_files:
                audio_file.unlink()
            
            print("   ✓ รวมไฟล์สำเร็จ")
        except Exception as e:
            print(f"   ⚠️ ไม่สามารถรวมไฟล์ได้: {e}")
            return False
    
    else:
        # ข้อความสั้นกว่า 5,000 ตัวอักษร สร้างเลย
        print(f"🔊 Voice: {voice_name}")
        print(f"⚡ Speaking Rate: {speaking_rate}x")
        print(f"🎵 Pitch: {pitch:+.1f}")
        
        try:
            # ใช้ SSML หรือ text ธรรมดา
            if use_ssml:
                synthesis_input = texttospeech.SynthesisInput(ssml=text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="th-TH",
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch
            )
            
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # บันทึกไฟล์
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            return False
    
    # ตรวจสอบไฟล์
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ สร้างเสียงสำเร็จ!")
        print(f"📄 ไฟล์: {output_path}")
        print(f"💾 ขนาด: {size_mb:.2f} MB")
        
        # คำนวณค่าใช้จ่าย
        cost_per_million = 16 if "Wavenet" in voice_name or "Neural" in voice_name else 4
        cost_usd = (text_length / 1_000_000) * cost_per_million
        cost_thb = cost_usd * 35
        
        print(f"💰 ค่าใช้จ่าย: ${cost_usd:.4f} (~{cost_thb:.2f} บาท)")
        
        return True
    else:
        print("❌ ไม่สามารถบันทึกไฟล์ได้")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate TTS audio with Google Cloud Text-to-Speech (Thai voices)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
เสียงภาษาไทยที่มี:
  WaveNet (คุณภาพสูง):
    th-TH-Wavenet-B    ผู้ชาย - โทนเป็นกันเอง (แนะนำ!)
    th-TH-Wavenet-D    ผู้ชาย - โทนมั่นใจ
  
  Neural2 (คุณภาพสูง):
    th-TH-Neural2-A    ผู้หญิง - โทนนุ่มนวล
    th-TH-Neural2-C    ผู้หญิง - โทนกลาง
  
  Standard (ฟรี):
    th-TH-Standard-A   ผู้หญิง - เสียงมาตรฐาน

ตัวอย่าง:
  python tts_generator_google.py --script script.txt --output voice.mp3 --voice th-TH-Wavenet-B
        """
    )
    
    parser.add_argument('--script', type=Path,
                       help='Path to script file (recording_script_SIMPLE.txt)')
    parser.add_argument('--output', type=Path,
                       help='Output audio file path (voiceover_ai.mp3)')
    parser.add_argument('--voice', type=str, default='th-TH-Journey-D',
                       help='Voice name (default: th-TH-Journey-D - ธรรมชาติที่สุด)')
    parser.add_argument('--rate', type=float, default=0.88,
                       help='Speaking rate 0.25-4.0 (default: 0.88 - สมดุล)')
    parser.add_argument('--pitch', type=float, default=0.0,
                       help='Pitch -20.0 to 20.0 (default: 0.0)')
    parser.add_argument('--list-voices', action='store_true',
                       help='List all available Thai voices')
    
    args = parser.parse_args()
    
    # แสดงรายการเสียง
    if args.list_voices:
        print("\n🎙️ เสียงภาษาไทยที่มี:\n")
        voices = get_available_voices()
        for category, voice_list in voices.items():
            print(f"📋 {category.upper()}:")
            for voice_name, description in voice_list.items():
                print(f"   {voice_name:<25} {description}")
            print()
        sys.exit(0)
    
    # ตรวจสอบไฟล์สคริปต์
    if not args.script.exists():
        print(f"❌ ไม่พบไฟล์สคริปต์: {args.script}")
        sys.exit(1)
    
    # อ่านสคริปต์
    with open(args.script, 'r', encoding='utf-8') as f:
        script_text = f.read().strip()
    
    if not script_text:
        print("❌ สคริปต์ว่างเปล่า")
        sys.exit(1)
    
    # แปลง [PAUSE] tags เป็น SSML
    script_text, use_ssml = convert_pause_to_ssml(script_text)
    
    if use_ssml:
        print("⏸️ พบ [PAUSE] tags - ใช้ SSML สำหรับการหยุดจังหวะ")
    
    # โหลด credentials
    try:
        credentials_path, credentials_dict = load_config()
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    
    # สร้างเสียง
    success = generate_tts_google(
        text=script_text,
        output_path=args.output,
        voice_name=args.voice,
        speaking_rate=args.rate,
        pitch=args.pitch,
        credentials_path=credentials_path,
        credentials_dict=credentials_dict,
        use_ssml=use_ssml
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
