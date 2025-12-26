#!/usr/bin/env python3
"""
Full Auto Production Orchestrator
Complete automation: Content → TTS → Video → Thumbnail → Upload

Usage:
    python scripts/full_auto_orchestrator.py --topic "Topic Title"
    
Or use batch file:
    C_create_video_full_auto.bat
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json


def get_audio_duration(audio_file: Path) -> float:
    """Get duration in seconds from audio file using mutagen"""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_file))
        return audio.info.length
    except ImportError:
        # Fallback: try using ffprobe if mutagen not available
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 
                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                 str(audio_file)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
    except Exception:
        pass
    return 0.0


class FullAutoOrchestrator:
    """Orchestrate complete video production"""
    
    def __init__(self, topic: str = None):
        self.topic = topic
        self.run_id = f"production_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path("output") / self.run_id
        self.audio_dir = Path("audio") / self.run_id
        self.video_dir = Path("video") / self.run_id
        self.thumbnail_dir = Path("thumbnails") / self.run_id
        
        # Create directories
        for dir_path in [self.output_dir, self.audio_dir, self.video_dir, self.thumbnail_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.voiceover_file = self.audio_dir / "voiceover_ai.mp3"
        self.video_file = self.video_dir / "final_video.mp4"
        self.thumbnail_file = self.thumbnail_dir / "thumbnail.png"
        
    def step1_content_generation(self) -> bool:
        """Step 1: AI Content Generation (17 agents)"""
        print("\n" + "="*70)
        print("📝 STEP 1/5: AI Content Generation (17 Agents)")
        print("="*70)
        
        cmd = [
            sys.executable,
            "orchestrator.py",
            "--pipeline", "pipelines/video_complete.yaml",
            "--run-id", self.run_id,
        ]
        
        if self.topic:
            cmd.extend(["--topic", self.topic])
        
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print("❌ Content generation failed")
            return False
        
        print("✅ Content generation completed")
        return True
    
    def step2_tts_generation(self) -> bool:
        """Step 2: Text-to-Speech (Google Cloud TTS)"""
        print("\n" + "="*70)
        print("🎙️  STEP 2/5: Text-to-Speech Generation")
        print("="*70)
        
        # Find script file
        script_file = self.output_dir / "script.md"
        if not script_file.exists():
            # Try alternative names
            for name in ["recording_script.txt", "script.txt", "script_validated.md"]:
                alt = self.output_dir / name
                if alt.exists():
                    script_file = alt
                    break
        
        if not script_file.exists():
            print(f"❌ Script file not found in {self.output_dir}")
            return False
        
        cmd = [
            sys.executable,
            "scripts/tts_unified.py",
            "--provider", "google",
            "--script", str(script_file),
            "--output", str(self.voiceover_file),
            "--voice", "th-TH-Chirp3-HD-Schedar",
            "--rate", "0.8",
            "--content-only"
        ]
        
        result = subprocess.run(cmd)
        
        if result.returncode != 0 or not self.voiceover_file.exists():
            print("❌ TTS generation failed")
            return False
        
        print(f"✅ TTS generation completed: {self.voiceover_file}")
        
        # Update metadata with actual audio duration
        self._update_metadata_with_duration()
        
        return True
    
    def _update_metadata_with_duration(self):
        """Update metadata.json with actual audio duration"""
        try:
            duration_sec = get_audio_duration(self.voiceover_file)
            if duration_sec > 0:
                meta_path = self.output_dir / "metadata.json"
                
                # Load existing metadata
                metadata = {}
                if meta_path.exists():
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                
                # Add actual duration
                metadata['actual_duration_seconds'] = round(duration_sec, 2)
                metadata['actual_duration_formatted'] = f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}"
                
                # Save back
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                print(f"   ⏱️  Duration: {metadata['actual_duration_formatted']} ({duration_sec:.1f}s)")
        except Exception as e:
            print(f"   ⚠️  Could not update duration: {e}")
    
    def step3_video_editing(self) -> bool:
        """Step 3: Auto Video Editing (DaVinci Resolve)"""
        print("\n" + "="*70)
        print("🎬 STEP 3/5: Auto Video Editing (DaVinci Resolve or Fallback)")
        print("="*70)
        
        print("💡 Will try DaVinci Resolve first; if unavailable, will use fallback renderer")
        print(f"   - Audio: {self.voiceover_file}")
        print(f"   - Guide: {self.output_dir}/PRODUCTION_GUIDE.html")
        
        # 1) Try DaVinci Resolve
        cmd = [
            sys.executable,
            "scripts/davinci_auto_editor.py",
            "--production-dir", str(self.output_dir),
            "--output", str(self.video_file)
        ]
        
        result = subprocess.run(cmd)
        
        if result.returncode == 0 and self.video_file.exists():
            print(f"✅ Video editing completed: {self.video_file}")
            return True
        
        print("⚠️  DaVinci Resolve not available or failed. Falling back to simple renderer...")
        
        # Read title from metadata if exists
        title = None
        meta_path = self.output_dir / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    title = meta.get('title')
            except Exception:
                pass
        
        # 2) Fallback renderer
        fallback_cmd = [
            sys.executable,
            "scripts/fallback_video_renderer.py",
            "--audio", str(self.voiceover_file),
            "--output", str(self.video_file)
        ]
        if title:
            fallback_cmd.extend(["--title", title])
        
        fb_result = subprocess.run(fallback_cmd)
        if fb_result.returncode != 0 or not self.video_file.exists():
            print("❌ Fallback renderer failed")
            return False
        
        print(f"✅ Video rendered: {self.video_file}")
        return True
    
    def step4_thumbnail_generation(self) -> bool:
        """Step 4: AI Thumbnail Generation"""
        print("\n" + "="*70)
        print("🎨 STEP 4/5: AI Thumbnail Generation")
        print("="*70)
        
        cmd = [
            sys.executable,
            "scripts/thumbnail_generator_ai.py",
            "--production-dir", str(self.output_dir),
            "--output", str(self.thumbnail_file),
            "--concept", "0"
        ]
        
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print("⚠️  Thumbnail generation failed")
            print("💡 You can create manually using Canva")
            print(f"   Guide: {self.output_dir}/canva_thumbnail_guide.txt")
            return True  # Don't fail completely
        
        print(f"✅ Thumbnail generated: {self.thumbnail_file}")
        return True
    
    def step5_youtube_upload(self) -> bool:
        """Step 5: YouTube Upload"""
        print("\n" + "="*70)
        print("📤 STEP 5/5: YouTube Upload")
        print("="*70)
        
        # Check if video exists
        if not self.video_file.exists():
            print("⚠️  Video file not found - upload skipped")
            print(f"   Expected: {self.video_file}")
            print("💡 Edit video manually, then upload using:")
            print(f"   python scripts/youtube_uploader.py --production-dir {self.output_dir} --video [your_video.mp4]")
            return True
        
        print("💡 This will upload to YouTube")
        response = input("🤔 Ready to upload? (y/n): ")
        
        if response.lower() != 'y':
            print("⏭️  Upload skipped")
            print(f"💡 To upload later:")
            print(f"   python scripts/youtube_uploader.py --production-dir {self.output_dir} --video {self.video_file} --thumbnail {self.thumbnail_file}")
            return True
        
        cmd = [
            sys.executable,
            "scripts/youtube_uploader.py",
            "--production-dir", str(self.output_dir),
            "--video", str(self.video_file),
        ]
        
        if self.thumbnail_file.exists():
            cmd.extend(["--thumbnail", str(self.thumbnail_file)])
        
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print("⚠️  YouTube upload failed")
            return False
        
        print("✅ YouTube upload completed!")
        return True
    
    def run(self) -> bool:
        """Run full automation pipeline"""
        print("\n" + "="*80)
        print("🚀 FULL AUTO VIDEO PRODUCTION - PATH C")
        print("="*80)
        print(f"\n🆔 Run ID: {self.run_id}")
        if self.topic:
            print(f"📌 Topic: {self.topic}")
        print(f"📂 Output: {self.output_dir}")
        print("\n" + "="*80 + "\n")
        
        # Track time
        start_time = datetime.now()
        
        # Execute steps
        steps = [
            (self.step1_content_generation, "AI Content Generation"),
            (self.step2_tts_generation, "TTS Generation"),
            (self.step3_video_editing, "Video Editing"),
            (self.step4_thumbnail_generation, "Thumbnail Generation"),
            (self.step5_youtube_upload, "YouTube Upload"),
        ]
        
        for i, (step_func, step_name) in enumerate(steps, 1):
            try:
                success = step_func()
                if not success:
                    print(f"\n❌ {step_name} failed - stopping pipeline")
                    return False
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Pipeline interrupted by user")
                return False
            except Exception as e:
                print(f"\n❌ Error in {step_name}: {e}")
                return False
        
        # Success!
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*80)
        print("✅ FULL AUTO PRODUCTION COMPLETED!")
        print("="*80)
        print(f"\n⏱️  Total time: {duration}")
        print(f"\n📂 Output files:")
        print(f"   • Content: {self.output_dir}")
        print(f"   • Audio: {self.voiceover_file}")
        if self.video_file.exists():
            print(f"   • Video: {self.video_file}")
        if self.thumbnail_file.exists():
            print(f"   • Thumbnail: {self.thumbnail_file}")
        
        print(f"\n📄 Production Guide: {self.output_dir}/PRODUCTION_GUIDE.html")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Auto Video Production")
    parser.add_argument("--topic", help="Video topic (optional - will pick from database)")
    
    args = parser.parse_args()
    
    # Run orchestrator
    orchestrator = FullAutoOrchestrator(topic=args.topic)
    success = orchestrator.run()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
