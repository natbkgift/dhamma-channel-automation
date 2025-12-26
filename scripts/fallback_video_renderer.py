#!/usr/bin/env python3
"""
Fallback Video Renderer
- Creates a simple 1080p MP4 video from an audio track
- Uses any images found in broll/ or generates a gradient background
- No DaVinci Resolve required

Dependencies (auto-installed if missing):
- moviepy
- pillow (already in repo)
- imageio[ffmpeg]

Usage:
  python scripts/fallback_video_renderer.py \
    --audio audio/production_xxx/voiceover_ai.mp3 \
    --output video/production_xxx/final_video.mp4 \
    --title "เจริญสติในชีวิตประจำวัน 5 นาที"
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def ensure_package(import_name: str, install_name: Optional[str] = None) -> bool:
    """Import a package, installing it if necessary.
    Supports different pip name via install_name and strips SSL env vars that can break pip.
    """
    try:
        __import__(import_name)
        return True
    except ImportError:
        pkg = install_name or import_name
        print(f"📦 Installing {pkg}...")
        try:
            env = os.environ.copy()
            # Some environments set cert variables that break pip on Windows
            for key in ("REQUESTS_CA_BUNDLE", "PIP_CERT", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
                env.pop(key, None)
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], env=env)
            __import__(import_name)
            return True
        except Exception as e:
            print(f"❌ Failed to install {pkg}: {e}")
            return False


def find_broll_images(broll_dir: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png"}
    files: List[Path] = []
    if broll_dir.exists():
        for p in sorted(broll_dir.rglob("*")):
            if p.suffix.lower() in exts:
                files.append(p)
    return files


def create_gradient_image(path: Path, width: int = 1920, height: int = 1080) -> Path:
    from PIL import Image
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        t = y / (height - 1)
        r = int((255 * (1 - t)) + (255 * t))
        g = int((210 * (1 - t)) + (170 * t))
        b = int((200 * (1 - t)) + (150 * t))
        for x in range(width):
            px[x, y] = (r, g, b)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def render_video(audio_path: Path, output_path: Path, title: Optional[str] = None, broll_dir: Optional[Path] = None) -> int:
    # Ensure deps (moviepy 2.x uses new import structure)
    ok = ensure_package("moviepy", install_name="moviepy") and ensure_package("imageio_ffmpeg", install_name="imageio[ffmpeg]")
    if not ok:
        print("❌ Required packages missing and could not be installed")
        return 1

    # MoviePy 2.x: import directly from moviepy.video/audio, not moviepy.editor
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        # Try old API for backwards compat
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import imageio_ffmpeg
    from PIL import Image, ImageDraw, ImageFont

    # Load audio
    if not audio_path.exists():
        print(f"❌ Audio not found: {audio_path}")
        return 1

    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    # Collect visuals
    images = find_broll_images(broll_dir or Path("broll"))
    temp_dir = output_path.parent / ".tmp_renderer"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if not images:
        # Create a gradient background image
        bg_img = create_gradient_image(temp_dir / "bg.png")
        images = [bg_img]

    # Build clips (slide every 6-8 seconds)
    slide_duration = 7.0
    clips = []
    t = 0.0
    i = 0

    # Prepare title overlay drawing function
    def draw_title_on(path: Path) -> Path:
        if not title:
            return path
        try:
            img = Image.open(path).convert("RGB").resize((1920, 1080))
            draw = ImageDraw.Draw(img)
            # Try to use a Thai font if available
            font_paths = [
                "C:/Windows/Fonts/Sarabun-Bold.ttf",
                "C:/Windows/Fonts/THSarabunNew-Bold.ttf",
                "C:/Windows/Fonts/NotoSansThai-Bold.ttf",
                "C:/Windows/Fonts/Arial.ttf",
            ]
            font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, 72)
                        break
                    except Exception:
                        continue
            if font is None:
                font = ImageFont.load_default()
            # Position and shadow
            x, y = 80, 820
            shadow = 4
            draw.text((x+shadow, y+shadow), title, fill=(0,0,0), font=font)
            draw.text((x, y), title, fill=(255,255,255), font=font)
            out = temp_dir / f"frame_title_{path.stem}.png"
            img.save(out)
            return out
        except Exception:
            return path

    title_applied_images: List[Path] = []
    for img_path in images:
        title_applied_images.append(draw_title_on(img_path))

    while t < duration:
        img_path = title_applied_images[i % len(title_applied_images)]
        clip = ImageClip(str(img_path)).with_duration(min(slide_duration, duration - t))
        clip = clip.resized(new_size=(1920, 1080))
        clips.append(clip)
        t += slide_duration
        i += 1

    video = concatenate_videoclips(clips, method="compose").with_audio(audio)

    # Ensure output dir
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write using ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"🛠️ Using ffmpeg at: {ffmpeg_exe}")

    try:
        # MoviePy 2.x removed verbose and logger params
        video.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="4500k",
            preset="medium",
            threads=2,
            temp_audiofile=str(temp_dir / "temp-audio.m4a"),
            remove_temp=True,
        )
    except Exception as e:
        print(f"❌ Failed to write video: {e}")
        return 1
    finally:
        try:
            audio.close()
            for c in clips:
                c.close()
        except Exception:
            pass

    size_mb = output_path.stat().st_size / (1024*1024)
    print(f"✅ Video rendered: {output_path} ({size_mb:.2f} MB)")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fallback Video Renderer")
    parser.add_argument("--audio", required=True, help="Path to voiceover audio (mp3/wav)")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--title", default=None, help="Optional title text overlay")
    parser.add_argument("--broll-dir", default="broll", help="B-roll images directory")
    args = parser.parse_args()

    audio = Path(args.audio)
    output = Path(args.output)
    broll = Path(args.broll_dir) if args.broll_dir else None

    code = render_video(audio, output, args.title, broll)
    return code


if __name__ == "__main__":
    sys.exit(main())
