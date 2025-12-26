#!/usr/bin/env python3
"""
TTS Generator - สร้างเสียงบรรยายด้วย OpenAI TTS
"""

import os
import sys
import json
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import httpx

def load_config():
    """โหลด API key จาก .env หรือ production_config.json"""
    # ลองโหลดจาก .env ก่อน
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY', '')
    
    if api_key:
        print("✅ พบ API key จาก .env")
        return api_key
    
    # ถ้าไม่มีใน .env ให้ลองจาก production_config.json
    config_path = Path.cwd() / 'production_config.json'
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('openai_api_key', '')
        
        if api_key:
            print("✅ พบ API key จาก production_config.json")
            return api_key
    
    raise ValueError("❌ ไม่พบ OPENAI_API_KEY ใน .env หรือ production_config.json")
    
    return api_key


def generate_tts(text: str, output_path: Path, voice: str = "alloy", speed: float = 1.0):
    """
    สร้างเสียงจากข้อความด้วย OpenAI TTS
    
    Args:
        text: ข้อความที่ต้องการแปลงเป็นเสียง
        output_path: ไฟล์เสียงที่ต้องการบันทึก
        voice: เสียงที่เลือก (alloy, echo, fable, onyx, nova, shimmer)
        speed: ความเร็วในการพูด (0.25 - 4.0)
    """
    print("🎙️ กำลังสร้างเสียงด้วย OpenAI TTS...")
    
    # โหลด API key
    api_key = load_config()
    
    # ตรวจสอบความยาวข้อความ
    text_length = len(text)
    print(f"📝 ความยาวสคริปต์: {text_length:,} ตัวอักษร")
    
    if text_length > 4096:
        print(f"⚠️ ข้อความยาวเกิน 4096 ตัวอักษร ({text_length:,}) จะแบ่งเป็นหลายส่วน...")
        
        # แบ่งข้อความเป็นส่วนๆ ตามขนาดที่เหมาะสม
        chunk_size = 4000  # เหลือที่ว่างสำหรับความปลอดภัย
        chunks = []
        
        # แบ่งตามประโยค (จบด้วย . ? !)
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # ถ้าเพิ่มประโยคนี้แล้วยาวเกิน ให้เริ่มชิ้นใหม่
            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "."
            else:
                current_chunk += sentence + "."
        
        # เพิ่มชิ้นสุดท้าย
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        print(f"� แบ่งเป็น {len(chunks)} ส่วน")
        
        # สร้างเสียงแต่ละส่วนและรวมกัน
        audio_files = []
        for i, chunk in enumerate(chunks, 1):
            print(f"\n🎙️ ส่วนที่ {i}/{len(chunks)} ({len(chunk):,} ตัวอักษร)")
            
            chunk_output = output_path.parent / f"temp_chunk_{i:03d}.mp3"
            
            # สร้าง client โดยปิด SSL verification
            client = OpenAI(
                api_key=api_key,
                http_client=httpx.Client(verify=False)
            )
            
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=chunk,
                speed=speed
            )
            
            response.stream_to_file(str(chunk_output))
            audio_files.append(chunk_output)
            print(f"   ✓ บันทึก {chunk_output.name}")
        
        # รวมไฟล์เสียงทั้งหมด
        print("\n🔄 กำลังรวมไฟล์เสียง...")
        
        try:
            # วิธีง่ายที่สุด: ต่อไฟล์ MP3 แบบ binary (ใช้ได้กับ MP3)
            with open(output_path, 'wb') as outfile:
                for audio_file in audio_files:
                    with open(audio_file, 'rb') as infile:
                        outfile.write(infile.read())
            
            # ลบไฟล์ชั่วคราว
            for audio_file in audio_files:
                audio_file.unlink()
            
            # ลบ concat_list ถ้ามี
            concat_file = output_path.parent / "concat_list.txt"
            if concat_file.exists():
                concat_file.unlink()
            
            print("   ✓ รวมไฟล์สำเร็จ")
                
        except Exception as e:
            print(f"   ⚠️ ไม่สามารถรวมไฟล์อัตโนมัติได้: {e}")
            print(f"   📁 ไฟล์ส่วนย่อยอยู่ที่: {output_path.parent}")
            print(f"   💡 รวมด้วย Audacity: File > Open > เลือกทั้ง 3 ไฟล์ > Tracks > Mix and Render")
            return False
    
    else:
        # ข้อความสั้นกว่า 4096 ตัวอักษร สร้างเลย
        try:
            # สร้าง client โดยปิด SSL verification
            client = OpenAI(
                api_key=api_key,
                http_client=httpx.Client(verify=False)
            )
            
            response = client.audio.speech.create(
                model="tts-1",  # หรือ tts-1-hd สำหรับคุณภาพสูง
                voice=voice,
                input=text,
                speed=speed
            )
            
            # บันทึกไฟล์
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(str(output_path))
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            return False
        
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            return False
    
    # ตรวจสอบไฟล์
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ สร้างเสียงสำเร็จ!")
        print(f"📄 ไฟล์: {output_path}")
        print(f"💾 ขนาด: {size_mb:.2f} MB")
        return True
    else:
        print("❌ ไม่สามารถบันทึกไฟล์ได้")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio with OpenAI")
    parser.add_argument('--script', type=Path, required=True,
                       help='Path to script file (recording_script_SIMPLE.txt)')
    parser.add_argument('--output', type=Path, required=True,
                       help='Output audio file path (voiceover_ai.mp3)')
    parser.add_argument('--voice', type=str, default='alloy',
                       choices=['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
                       help='Voice to use (default: alloy)')
    parser.add_argument('--speed', type=float, default=1.0,
                       help='Speech speed 0.25-4.0 (default: 1.0)')
    
    args = parser.parse_args()
    
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
    
    # สร้างเสียง
    success = generate_tts(
        text=script_text,
        output_path=args.output,
        voice=args.voice,
        speed=args.speed
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
