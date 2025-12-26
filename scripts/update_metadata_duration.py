#!/usr/bin/env python3
"""Update metadata.json with actual audio duration"""
import json
from pathlib import Path
from mutagen.mp3 import MP3
import sys

if len(sys.argv) < 2:
    print("Usage: python update_metadata_duration.py <run_id>")
    sys.exit(1)

run_id = sys.argv[1]
audio_file = Path(f"audio/{run_id}/voiceover_ai.mp3")
meta_path = Path(f"output/{run_id}/metadata.json")

if not audio_file.exists():
    print(f"❌ Audio file not found: {audio_file}")
    sys.exit(1)

# Read duration
audio = MP3(str(audio_file))
duration = audio.info.length

# Load metadata
metadata = {}
if meta_path.exists():
    with open(meta_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

# Update
metadata['actual_duration_seconds'] = round(duration, 2)
metadata['actual_duration_formatted'] = f"{int(duration // 60)}:{int(duration % 60):02d}"

# Save
with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"✅ Updated {meta_path}")
print(f"   Duration: {metadata['actual_duration_formatted']} ({duration:.2f}s)")
