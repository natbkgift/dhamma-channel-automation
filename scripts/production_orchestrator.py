#!/usr/bin/env python3
"""
Production Orchestrator - Unified script for all production paths

รัน production phase ทั้ง Path A (manual), Path B (semi-auto), และ Path C (full-auto)
ตาม configuration file
"""

import json
import argparse
from pathlib import Path
import subprocess
import sys


def load_config(config_path: Path) -> dict:
    """โหลด production config"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_command(cmd: list, description: str) -> bool:
    """รันคำสั่งและแสดงผล"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}\n")
    
    try:
        subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ เสร็จสิ้น: {description}\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ล้มเหลว: {description}")
        print(f"ข้อผิดพลาด: {e}\n")
        return False


def run_path_a(config: dict, input_dir: Path):
    """Run Path A: Manual/Free workflow"""
    print("\n" + "="*70)
    print("🅰️  เส้นทาง A: ทำด้วยมือ (ฟรี)")
    print("="*70)
    
    steps = []
    
    # 1. Voiceover preparation
    if config.get('prepare_voiceover', True):
        audio_dir = Path(config.get('audio_dir', 'audio')) / input_dir.name
        steps.append({
            'cmd': [
                sys.executable,
                'scripts/prepare_voiceover.py',
                '--input-dir', str(input_dir),
                '--output-dir', str(audio_dir)
            ],
            'desc': 'เตรียมสคริปต์สำหรับบันทึกเสียง'
        })
    
    # 2. DaVinci Resolve templates
    if config.get('generate_davinci_templates', True):
        template_dir = Path(config.get('template_dir', 'templates')) / input_dir.name
        steps.append({
            'cmd': [
                sys.executable,
                'scripts/generate_davinci_template.py',
                '--input-dir', str(input_dir),
                '--output-dir', str(template_dir),
                '--fps', str(config.get('fps', 30))
            ],
            'desc': 'สร้างเทมเพลตสำหรับ DaVinci Resolve'
        })
    
    # 3. B-roll downloader (if API key provided)
    if config.get('download_broll', False):
        broll_dir = Path(config.get('broll_dir', 'broll')) / input_dir.name
        api_key = config.get('pexels_api_key', '')
        
        cmd = [
            sys.executable,
            'scripts/download_broll.py',
            '--input-dir', str(input_dir),
            '--output-dir', str(broll_dir),
            '--max-videos', str(config.get('max_broll_videos', 10))
        ]
        
        if api_key:
            cmd.extend(['--api-key', api_key])
        else:
            cmd.append('--dry-run')
        
        steps.append({
            'cmd': cmd,
            'desc': 'ดาวน์โหลดวิดีโอ B-roll' if api_key else 'แสดงรายการความต้องการ B-roll (โหมดจำลอง)'
        })
    
    # 4. Canva thumbnail templates
    if config.get('generate_canva_templates', True):
        steps.append({
            'cmd': [
                sys.executable,
                'scripts/generate_canva_templates.py',
                '--input-dir', str(input_dir)
            ],
            'desc': 'สร้างคู่มือและสเปก Thumbnail สำหรับ Canva'
        })
    
    # Run all steps
    success_count = 0
    for step in steps:
        if run_command(step['cmd'], step['desc']):
            success_count += 1
    
    # Summary
    print("\n" + "="*70)
    print(f"✅ เสร็จสิ้นเส้นทาง A: สำเร็จ {success_count}/{len(steps)} ขั้นตอน")
    print("="*70)
    
    print("\n📋 งานที่ต้องทำต่อ (ด้วยมือ):\n")
    print("  1. ✅ พร้อมสคริปต์บันทึกเสียง → บันทึกด้วย Audacity/OBS")
    print("  2. ✅ พร้อมเทมเพลต DaVinci → ตัดต่อวิดีโอ")
    print("  3. ✅ พร้อมคู่มือ Canva → สร้างภาพหน้าปก (Thumbnail)")
    print("  4. ⏳ อัปโหลดขึ้น YouTube ด้วยตนเอง\n")
    
    return success_count == len(steps)


def run_path_b(config: dict, input_dir: Path):
    """Run Path B: Semi-automated workflow (with APIs)"""
    print("\n" + "="*70)
    print("🅱️  เส้นทาง B: กึ่งอัตโนมัติ")
    print("="*70)
    
    # ยังไม่ implement (ต้องมี OpenAI API)
    print("\n⚠️  เส้นทาง B ต้องใช้ API เพิ่มเติม:")
    print("  - OpenAI API สำหรับสร้างเสียง (TTS)")
    print("  - YouTube Data API สำหรับอัปโหลดวิดีโอ")
    print("\n  แนะนำให้รันเส้นทาง A ก่อน แล้วค่อยเพิ่มเสียง/อัปโหลดด้วยมือ")
    print("  หรือรอเวอร์ชันที่รองรับ B แบบครบถ้วน\n")
    
    return run_path_a(config, input_dir)


def run_path_c(config: dict, input_dir: Path):
    """Run Path C: Full automation (with all APIs)"""
    print("\n" + "="*70)
    print("🅲️  เส้นทาง C: อัตโนมัติเต็มรูปแบบ")
    print("="*70)
    
    # ยังไม่ implement (ต้องมี APIs หลายตัว)
    print("\n⚠️  เส้นทาง C ต้องใช้หลาย API:")
    print("  - ElevenLabs สำหรับเสียงคุณภาพสูง")
    print("  - Stock video APIs สำหรับ B-roll")
    print("  - DALL-E สำหรับสร้าง Thumbnail")
    print("  - YouTube Data API สำหรับอัปโหลด")
    print("\n  แนะนำให้เริ่มจากเส้นทาง A แล้วค่อยเพิ่ม API ทีละส่วน\n")
    
    return run_path_a(config, input_dir)


def main():
    parser = argparse.ArgumentParser(description="Production Orchestrator - Run production workflow")
    parser.add_argument('--config', type=Path, default=Path('production_config.json'),
                       help='Production config file (default: production_config.json)')
    parser.add_argument('--input-dir', type=Path, required=True,
                       help='Input directory with pipeline output (e.g., output/production_complete_001)')
    parser.add_argument('--path', choices=['A', 'B', 'C'], default=None,
                       help='Force specific path (A=free, B=semi-auto, C=full-auto). If not specified, uses config.')
    
    args = parser.parse_args()
    
    # Load config หรือสร้าง default
    if args.config.exists():
        config = load_config(args.config)
        print(f"✅ Loaded config: {args.config}")
    else:
        print(f"⚠️  Config not found, using defaults")
        config = {
            'path': 'A',
            'prepare_voiceover': True,
            'generate_davinci_templates': True,
            'download_broll': False,
            'generate_canva_templates': True,
            'fps': 30,
            'max_broll_videos': 10
        }
    
    # Override path ถ้าระบุ
    if args.path:
        config['path'] = args.path
    
    path = config.get('path', 'A')
    
    print("\n" + "="*70)
    print("🎬 ตัวจัดการกระบวนการผลิต (Production Orchestrator)")
    print("="*70)
    print(f"\n📂 โฟลเดอร์อินพุต: {args.input_dir}")
    
    path_names = {'A': 'ทำด้วยมือ (ฟรี)', 'B': 'กึ่งอัตโนมัติ', 'C': 'อัตโนมัติเต็มรูปแบบ'}
    print(f"🎯 เส้นทาง: {path} ({path_names[path]})")
    print(f"⚙️  ไฟล์ตั้งค่า: {args.config if args.config.exists() else 'ค่าเริ่มต้น'}\n")
    
    # ตรวจสอบ input directory
    if not args.input_dir.exists():
        print(f"❌ ไม่พบโฟลเดอร์อินพุต: {args.input_dir}")
        return 1
    
    # ตรวจสอบไฟล์ที่จำเป็น
    required_files = ['script_validated.md', 'voiceover_guide.json', 'visual_guide.json', 'thumbnail_concepts.json']
    missing_files = [f for f in required_files if not (args.input_dir / f).exists()]
    
    if missing_files:
        print(f"⚠️  คำเตือน: ไฟล์ต่อไปนี้หายไปในโฟลเดอร์อินพุต:")
        for f in missing_files:
            print(f"   - {f}")
        print("\n  ดำเนินการต่อไปโดยข้ามไฟล์ที่หายไป...\n")
    
    # Run ตาม path
    if path == 'A':
        success = run_path_a(config, args.input_dir)
    elif path == 'B':
        success = run_path_b(config, args.input_dir)
    elif path == 'C':
        success = run_path_c(config, args.input_dir)
    else:
        print(f"❌ Unknown path: {path}")
        return 1
    
    if success:
        print("\n🎉 กระบวนการผลิตเสร็จสมบูรณ์!")
        print(f"\n📂 ไปที่โฟลเดอร์ผลลัพธ์:")
        print(f"   - audio/{args.input_dir.name}/")
        print(f"   - templates/{args.input_dir.name}/")
        print(f"   - templates/canva/")
        if config.get('download_broll'):
            print(f"   - broll/{args.input_dir.name}/")
        return 0
    else:
        print("\n⚠️  บางขั้นตอนล้มเหลว โปรดดูรายละเอียดข้อผิดพลาดด้านบน")
        return 1


if __name__ == '__main__':
    sys.exit(main())
