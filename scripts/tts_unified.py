#!/usr/bin/env python3
"""
Unified TTS Generator - รองรับหลาย TTS providers
- OpenAI TTS (6 เสียง, รองรับหลายภาษา)
- Google Cloud TTS (เสียงไทยเนทีฟ, คุณภาพสูง)
"""

import os
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Generate TTS audio with multiple providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Providers:
  openai         OpenAI TTS (default) - 6 เสียง, หลายภาษา
  google         Google Cloud TTS - เสียงไทยเนทีฟ (แนะนำ!)

ตัวอย่าง:
  # OpenAI TTS
  python tts_unified.py --provider openai --script script.txt --output voice.mp3 --voice alloy

  # Google Cloud TTS (เสียงไทยชัด! แนะนำ)
  python tts_unified.py --provider google --script script.txt --output voice.mp3 --voice th-TH-Chirp3-HD-Schedar --rate 0.80
  
  # พร้อม Content-Only + Clean (แนะนำสำหรับช่องธรรมะ!)
  python tts_unified.py --provider google --script script.txt --output voice.mp3 --content-only --clean
        """
    )
    
    parser.add_argument('--provider', type=str, default='google',
                       choices=['openai', 'google'],
                       help='TTS provider (default: google)')
    parser.add_argument('--script', type=Path,
                       help='Path to script file')
    parser.add_argument('--output', type=Path,
                       help='Output audio file path')
    parser.add_argument('--voice', type=str,
                       help='Voice name (provider-specific)')
    parser.add_argument('--speed', type=float, default=1.0,
                       help='Speaking speed (OpenAI)')
    parser.add_argument('--rate', type=float, default=1.0,
                       help='Speaking rate (Google)')
    parser.add_argument('--pitch', type=float, default=0.0,
                       help='Pitch (Google only)')
    parser.add_argument('--list-voices', action='store_true',
                       help='List available voices for provider')
    parser.add_argument('--clean', action='store_true',
                       help='ทำความสะอาดข้อความด้วย TTS Preprocessor (แนะนำ!)')
    parser.add_argument('--content-only', action='store_true',
                       help='แยกเฉพาะเนื้อหาพากย์ ลบ metadata/คำสั่ง (แนะนำ!)')
    parser.add_argument('--preview', action='store_true',
                       help='แสดงตัวอย่างข้อความหลัง preprocess (ไม่สร้างเสียง)')
    
    args = parser.parse_args()
    
    # ถ้าต้องการแยกเฉพาะเนื้อหา (Content-Only Mode)
    if args.content_only and args.script:
        from content_extractor import ContentExtractor
        
        print("📝 แยกเฉพาะเนื้อหาพากย์ (Content-Only Mode)...")
        extractor = ContentExtractor()
        
        # อ่านไฟล์
        with open(args.script, 'r', encoding='utf-8') as f:
            original_text = f.read()
        
        # แยกเนื้อหา
        content_text, content_meta = extractor.extract_content(original_text)
        
        # แสดงสถิติ
        print(f"   • ขนาดเดิม: {content_meta['original_length']:,} chars")
        print(f"   • เนื้อหาเท่านั้น: {content_meta['content_length']:,} chars")
        print(f"   • ลดลง: {content_meta['reduction']}")
        print(f"   • ลบ metadata: {content_meta['removed']['metadata']} บรรทัด")
        print(f"   • ลบ directions: {content_meta['removed']['directions']} ชิ้น")
        
        # บันทึกไฟล์ชั่วคราว
        temp_script = args.script.parent / f"{args.script.stem}_content_only{args.script.suffix}"
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(content_text)
        
        print(f"   ✓ บันทึกไฟล์ชั่วคราว: {temp_script}")
        
        # ใช้ไฟล์ที่แยกเนื้อหาแล้ว
        args.script = temp_script
    
    # ถ้าต้องการทำความสะอาดข้อความ
    if args.clean and args.script:
        from tts_preprocessor import TTSPreprocessor
        
        print("🧹 ทำความสะอาดข้อความด้วย TTS Preprocessor...")
        preprocessor = TTSPreprocessor()
        
        # อ่านไฟล์
        with open(args.script, 'r', encoding='utf-8') as f:
            original_text = f.read()
        
        # ประมวลผล
        cleaned_text, metadata = preprocessor.preprocess(original_text)
        
        # แสดงสถิติ
        print(f"   • ขนาดเดิม: {metadata['original_length']:,} chars")
        print(f"   • ขนาดใหม่: {metadata['final_length']:,} chars")
        print(f"   • การเปลี่ยนแปลง: {', '.join(metadata['changes'][:3])}")
        
        # ถ้าเป็น preview mode ให้แสดงข้อความและหยุด
        if args.preview:
            print("\n📄 ข้อความหลัง preprocess:\n")
            print("=" * 60)
            print(cleaned_text[:500])
            if len(cleaned_text) > 500:
                print("\n... (แสดงเฉพาะ 500 ตัวอักษรแรก)")
            print("=" * 60)
            print(f"\nความยาวทั้งหมด: {len(cleaned_text):,} ตัวอักษร")
            return 0
        
        # บันทึกไฟล์ชั่วคราว
        temp_script = args.script.parent / f"{args.script.stem}_cleaned{args.script.suffix}"
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        print(f"   ✓ บันทึกไฟล์ชั่วคราว: {temp_script}")
        
        # ใช้ไฟล์ที่ทำความสะอาดแล้ว
        args.script = temp_script
    
    # เลือก provider
    if args.provider == 'openai':
        # ใช้ OpenAI TTS
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from tts_generator import main as openai_main
        
        if args.list_voices:
            print("\n🎙️ OpenAI TTS Voices:\n")
            voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
            descriptions = {
                'alloy': 'ผู้ชายหนุ่ม กลางๆ สบายๆ',
                'echo': 'ผู้ชายโทนลึก มั่นใจ',
                'fable': 'ผู้ชายโทนสูง พูดชัด',
                'onyx': 'ผู้ชายโทนต่ำ น่าเชื่อถือ',
                'nova': 'ผู้หญิงโทนกลาง เป็นมิตร',
                'shimmer': 'ผู้หญิงโทนสูง สดใส'
            }
            for voice in voices:
                print(f"   {voice:<15} {descriptions[voice]}")
            print("\n⚠️ หมายเหตุ: เสียงออกแบบมาสำหรับภาษาอังกฤษ ภาษาไทยอาจไม่ชัด")
            return 0
        
        # รันด้วย OpenAI
        voice = args.voice or 'alloy'
        sys.argv = [
            'tts_generator.py',
            '--script', str(args.script),
            '--output', str(args.output),
            '--voice', voice,
            '--speed', str(args.speed)
        ]
        openai_main()
        
    elif args.provider == 'google':
        # ใช้ Google Cloud TTS
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from tts_generator_google import main as google_main
        
        if args.list_voices:
            sys.argv = ['tts_generator_google.py', '--list-voices']
            google_main()
            return 0
        
        # รันด้วย Google
        voice = args.voice or 'th-TH-Wavenet-B'
        sys.argv = [
            'tts_generator_google.py',
            '--script', str(args.script),
            '--output', str(args.output),
            '--voice', voice,
            '--rate', str(args.rate),
            '--pitch', str(args.pitch)
        ]
        google_main()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ ยกเลิกโดยผู้ใช้")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
        sys.exit(1)
