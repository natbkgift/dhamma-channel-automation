#!/usr/bin/env python3
"""
DaVinci Resolve Auto Video Editor
Automatically creates and edits video timeline from production data

Requirements:
1. DaVinci Resolve 19+ installed and running
2. Python API enabled (C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting)
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# DaVinci Resolve API paths (adjust if needed)
RESOLVE_SCRIPT_API = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
RESOLVE_SCRIPT_LIB = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"

# Add to Python path
if os.path.exists(RESOLVE_SCRIPT_API):
    sys.path.append(os.path.join(RESOLVE_SCRIPT_API, "Modules"))


class DaVinciAutoEditor:
    """Auto video editor using DaVinci Resolve API"""
    
    def __init__(self, production_dir: Path):
        self.production_dir = Path(production_dir)
        self.resolve = None
        self.project_manager = None
        self.project = None
        self.media_pool = None
        self.timeline = None
        
        # Load production data
        self.metadata = self._load_json("metadata.json")
        self.voiceover_guide = self._load_json("voiceover_guide.json")
        self.visual_guide = self._load_json("visual_guide.json")
        self.timeline_data = self._load_json("timeline.json")
        
        # Paths
        self.audio_file = self._find_audio_file()
        self.broll_dir = Path("broll")  # B-roll images/videos
        
    def _load_json(self, filename: str) -> dict:
        """Load JSON file from production directory"""
        filepath = self.production_dir / filename
        if not filepath.exists():
            print(f"⚠️  Warning: {filename} not found")
            return {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _find_audio_file(self) -> Optional[Path]:
        """Find voiceover audio file"""
        audio_dir = Path("audio") / self.production_dir.name
        
        # Look for voiceover_ai.mp3 or voiceover.mp3
        for filename in ["voiceover_ai.mp3", "voiceover.mp3", "voiceover.wav"]:
            audio_path = audio_dir / filename
            if audio_path.exists():
                return audio_path
        
        return None
    
    def connect_resolve(self) -> bool:
        """Connect to DaVinci Resolve"""
        try:
            import DaVinciResolveScript as dvr_script
            
            self.resolve = dvr_script.scriptapp("Resolve")
            if not self.resolve:
                print("❌ DaVinci Resolve not running!")
                print("💡 Please open DaVinci Resolve first")
                return False
            
            self.project_manager = self.resolve.GetProjectManager()
            print(f"✅ Connected to DaVinci Resolve {self.resolve.GetVersion()}")
            return True
            
        except ImportError:
            print("❌ Cannot import DaVinci Resolve Script API")
            print(f"💡 Check path: {RESOLVE_SCRIPT_API}")
            print("💡 Make sure DaVinci Resolve is installed")
            return False
        except Exception as e:
            print(f"❌ Error connecting to Resolve: {e}")
            return False
    
    def create_project(self, project_name: str) -> bool:
        """Create new project"""
        try:
            # Create new project
            self.project = self.project_manager.CreateProject(project_name)
            
            if not self.project:
                # Try to open existing project
                self.project = self.project_manager.LoadProject(project_name)
            
            if not self.project:
                print(f"❌ Failed to create/load project: {project_name}")
                return False
            
            # Set project settings
            self.project.SetSetting("timelineFrameRate", "30")
            self.project.SetSetting("timelineResolutionWidth", "1920")
            self.project.SetSetting("timelineResolutionHeight", "1080")
            
            self.media_pool = self.project.GetMediaPool()
            
            print(f"✅ Project created: {project_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating project: {e}")
            return False
    
    def import_media(self) -> bool:
        """Import audio and media files"""
        try:
            # Import audio
            if self.audio_file and self.audio_file.exists():
                audio_abs = str(self.audio_file.absolute())
                imported = self.media_pool.ImportMedia([audio_abs])
                if imported:
                    print(f"✅ Imported audio: {self.audio_file.name}")
                else:
                    print(f"⚠️  Failed to import audio: {self.audio_file.name}")
            else:
                print("⚠️  No audio file found")
                return False
            
            # Import B-roll (if exists)
            if self.broll_dir.exists():
                broll_files = list(self.broll_dir.glob("*.jpg")) + \
                             list(self.broll_dir.glob("*.png")) + \
                             list(self.broll_dir.glob("*.mp4"))
                
                if broll_files:
                    broll_paths = [str(f.absolute()) for f in broll_files[:10]]  # Limit 10
                    imported = self.media_pool.ImportMedia(broll_paths)
                    print(f"✅ Imported {len(broll_files)} B-roll files")
            
            return True
            
        except Exception as e:
            print(f"❌ Error importing media: {e}")
            return False
    
    def create_timeline(self, timeline_name: str) -> bool:
        """Create video timeline"""
        try:
            # Create timeline
            self.timeline = self.media_pool.CreateEmptyTimeline(timeline_name)
            
            if not self.timeline:
                print("❌ Failed to create timeline")
                return False
            
            # Set timeline to current
            self.project.SetCurrentTimeline(self.timeline)
            
            print(f"✅ Timeline created: {timeline_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating timeline: {e}")
            return False
    
    def add_audio_track(self) -> bool:
        """Add audio to timeline"""
        try:
            # Get audio clip from media pool
            root_folder = self.media_pool.GetRootFolder()
            clips = root_folder.GetClipList()
            
            # Find audio clip
            audio_clip = None
            for clip in clips:
                clip_name = clip.GetName()
                if "voiceover" in clip_name.lower():
                    audio_clip = clip
                    break
            
            if not audio_clip:
                print("⚠️  Audio clip not found in media pool")
                return False
            
            # Add to timeline
            success = self.media_pool.AppendToTimeline([audio_clip])
            
            if success:
                print("✅ Audio track added to timeline")
                return True
            else:
                print("❌ Failed to add audio to timeline")
                return False
            
        except Exception as e:
            print(f"❌ Error adding audio: {e}")
            return False
    
    def add_visual_elements(self) -> bool:
        """Add visual elements (placeholders for now)"""
        try:
            # For now, just add a solid color background
            # In future: add B-roll images/videos based on visual_guide
            
            print("⏳ Adding visual elements (basic version)...")
            
            # Get timeline duration
            timeline_duration = self.timeline.GetEndFrame()
            
            # Add video track (DaVinci will use default settings)
            # This is a placeholder - full implementation will add actual visuals
            
            print("✅ Visual elements added (placeholder)")
            return True
            
        except Exception as e:
            print(f"❌ Error adding visuals: {e}")
            return False
    
    def export_video(self, output_path: Path) -> bool:
        """Export timeline as MP4"""
        try:
            # Get current timeline
            if not self.timeline:
                print("❌ No timeline to export")
                return False
            
            # Set render settings
            self.project.SetCurrentTimeline(self.timeline)
            
            # Export settings
            render_settings = {
                "SelectAllFrames": True,
                "TargetDir": str(output_path.parent.absolute()),
                "CustomName": output_path.stem,
                "ExportVideo": True,
                "ExportAudio": True,
                "FormatWidth": 1920,
                "FormatHeight": 1080,
                "FrameRate": 30,
                "VideoQuality": "High",
                "AudioCodec": "AAC",
                "AudioBitDepth": 16,
                "AudioSampleRate": 48000,
            }
            
            # Set render settings
            self.project.SetRenderSettings(render_settings)
            
            # Add to render queue
            render_id = self.project.AddRenderJob()
            
            if not render_id:
                print("❌ Failed to add render job")
                return False
            
            # Start rendering
            self.project.StartRendering(render_id)
            
            print(f"🎬 Rendering started...")
            print(f"💾 Output: {output_path}")
            
            # Wait for render to complete
            while self.project.IsRenderingInProgress():
                time.sleep(2)
                print(".", end="", flush=True)
            
            print("\n✅ Video exported successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting video: {e}")
            return False
    
    def process(self, output_video: Path) -> bool:
        """Full auto-editing process"""
        print("\n" + "="*70)
        print("🎬 DaVinci Resolve Auto Video Editor")
        print("="*70 + "\n")
        
        # Step 1: Connect
        print("📡 Step 1/6: Connecting to DaVinci Resolve...")
        if not self.connect_resolve():
            return False
        
        # Step 2: Create project
        project_name = f"Dhamma_{self.production_dir.name}"
        print(f"\n📂 Step 2/6: Creating project '{project_name}'...")
        if not self.create_project(project_name):
            return False
        
        # Step 3: Import media
        print("\n📥 Step 3/6: Importing media files...")
        if not self.import_media():
            return False
        
        # Step 4: Create timeline
        timeline_name = self.metadata.get('title', 'Dhamma Video')
        print(f"\n🎞️  Step 4/6: Creating timeline '{timeline_name}'...")
        if not self.create_timeline(timeline_name):
            return False
        
        # Step 5: Add tracks
        print("\n🎵 Step 5/6: Adding audio and visuals...")
        if not self.add_audio_track():
            return False
        
        if not self.add_visual_elements():
            return False
        
        # Step 6: Export
        print(f"\n💾 Step 6/6: Exporting video...")
        if not self.export_video(output_video):
            return False
        
        print("\n" + "="*70)
        print("✅ AUTO-EDITING COMPLETED!")
        print("="*70)
        print(f"\n📄 Video file: {output_video}")
        print(f"📊 Project: {project_name}")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DaVinci Resolve Auto Video Editor")
    parser.add_argument("--production-dir", required=True, help="Production directory (e.g., output/production_20251105_183328)")
    parser.add_argument("--output", required=True, help="Output video file (e.g., video/final_video.mp4)")
    
    args = parser.parse_args()
    
    production_dir = Path(args.production_dir)
    output_video = Path(args.output)
    
    # Validate
    if not production_dir.exists():
        print(f"❌ Production directory not found: {production_dir}")
        sys.exit(1)
    
    # Create output directory
    output_video.parent.mkdir(parents=True, exist_ok=True)
    
    # Run editor
    editor = DaVinciAutoEditor(production_dir)
    success = editor.process(output_video)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
