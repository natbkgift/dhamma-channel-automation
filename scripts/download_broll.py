#!/usr/bin/env python3
"""
B-roll Video Downloader - Path A (Free Assets)

ดาวน์โหลด B-roll videos จาก Pexels API (ฟรี) ตาม visual_guide.json
"""

import json
import argparse
import requests
from pathlib import Path
import time
from typing import List, Dict


def load_visual_guide(guide_path: Path) -> dict:
    """โหลด visual guide"""
    with open(guide_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def search_pexels_videos(query: str, api_key: str, per_page: int = 5) -> List[Dict]:
    """ค้นหาวิดีโอจาก Pexels API"""
    if not api_key or api_key == 'YOUR_PEXELS_API_KEY':
        print(f"⚠️  No API key - skipping search for: {query}")
        return []
    
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "medium"  # medium = 1280x720
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for video in data.get('videos', []):
            # หา HD video file
            video_files = video.get('video_files', [])
            hd_file = None
            
            for vf in video_files:
                if vf.get('quality') == 'hd' and vf.get('width') >= 1280:
                    hd_file = vf
                    break
            
            if not hd_file and video_files:
                hd_file = video_files[0]  # fallback
            
            if hd_file:
                videos.append({
                    'id': video['id'],
                    'url': hd_file['link'],
                    'width': hd_file['width'],
                    'height': hd_file['height'],
                    'duration': video.get('duration', 0),
                    'photographer': video['user']['name']
                })
        
        return videos
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error searching Pexels: {e}")
        return []


def download_video(url: str, output_path: Path) -> bool:
    """ดาวน์โหลดวิดีโอ"""
    try:
        print(f"   Downloading: {output_path.name}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        print(f"   ✅ Downloaded: {file_size:.1f} MB")
        return True
    
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def extract_broll_requirements(visual_guide: dict) -> List[Dict]:
    """แยก B-roll requirements จาก visual guide"""
    requirements = []
    
    # จาก scenes
    for scene in visual_guide.get('scenes', []):
        if scene.get('type') == 'B-roll' or 'b-roll' in scene.get('description', '').lower():
            requirements.append({
                'timestamp': scene.get('timestamp', 'unknown'),
                'type': 'scene',
                'description': scene.get('description', ''),
                'suggestions': scene.get('suggestions', [])
            })
    
    # จาก b_roll_footage
    for broll in visual_guide.get('b_roll_footage', []):
        requirements.append({
            'timestamp': broll.get('timestamp', 'unknown'),
            'type': 'b-roll',
            'description': broll.get('description', ''),
            'keywords': broll.get('keywords', [])
        })
    
    return requirements


def generate_search_queries(requirements: List[Dict]) -> List[str]:
    """สร้าง search queries จาก requirements"""
    queries = []
    
    for req in requirements:
        # ใช้ keywords ถ้ามี
        if 'keywords' in req and req['keywords']:
            queries.extend(req['keywords'][:2])  # เอาแค่ 2 keywords แรก
        
        # ใช้ description ถ้าเป็นภาษาอังกฤษ
        desc = req.get('description', '')
        if desc and any(c.isascii() and c.isalpha() for c in desc):
            # แปลงเป็น search query
            query = desc.lower()
            # ลบคำที่ไม่สำคัญ
            stopwords = ['the', 'a', 'an', 'of', 'with', 'for', 'person', 'people']
            words = [w for w in query.split() if w not in stopwords and len(w) > 3]
            if words:
                queries.append(' '.join(words[:3]))  # เอาแค่ 3 คำแรก
    
    # ลบ duplicates และจำกัดจำนวน
    unique_queries = list(set(queries))[:10]  # สูงสุด 10 queries
    
    # ถ้าไม่มี queries ให้ใช้ generic
    if not unique_queries:
        unique_queries = [
            "meditation peaceful",
            "nature calm",
            "breathing mindfulness",
            "zen garden",
            "sunset relaxing"
        ]
    
    return unique_queries


def main():
    parser = argparse.ArgumentParser(description="Download B-roll videos from Pexels")
    parser.add_argument('--input-dir', type=Path, required=True,
                       help='Input directory with visual_guide.json')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory for B-roll videos (default: broll/)')
    parser.add_argument('--api-key', type=str, default=None,
                       help='Pexels API key (get free at https://www.pexels.com/api/)')
    parser.add_argument('--max-videos', type=int, default=10,
                       help='Maximum number of videos to download (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be downloaded without downloading')
    
    args = parser.parse_args()
    
    # Paths
    input_dir = args.input_dir
    output_dir = args.output_dir or Path('broll')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    guide_file = input_dir / 'visual_guide.json'
    
    # ตรวจสอบไฟล์
    if not guide_file.exists():
        print(f"❌ Error: {guide_file} not found!")
        return
    
    # API key
    api_key = args.api_key
    if not api_key:
        print("⚠️  No Pexels API key provided!")
        print("   Get free API key at: https://www.pexels.com/api/")
        print("   Usage: --api-key YOUR_KEY")
        print("\n   Running in DRY RUN mode (showing search queries only)\n")
        args.dry_run = True
        api_key = 'YOUR_PEXELS_API_KEY'
    
    print("🎬 B-roll Video Downloader")
    print(f"📂 Input: {input_dir}")
    print(f"📂 Output: {output_dir}")
    print(f"🔑 API Key: {'✅ Provided' if api_key != 'YOUR_PEXELS_API_KEY' else '❌ Missing'}")
    print(f"📊 Max videos: {args.max_videos}\n")
    
    # โหลด visual guide
    visual_guide = load_visual_guide(guide_file)
    
    # แยก B-roll requirements
    requirements = extract_broll_requirements(visual_guide)
    print(f"✅ Found {len(requirements)} B-roll requirements\n")
    
    # สร้าง search queries
    queries = generate_search_queries(requirements)
    print(f"🔍 Generated {len(queries)} search queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    print()
    
    if args.dry_run:
        print("🏃 DRY RUN - No files will be downloaded")
        print("\nTo actually download, provide --api-key and remove --dry-run")
        return
    
    # ดาวน์โหลด
    downloaded = 0
    download_info = []
    
    for query in queries:
        if downloaded >= args.max_videos:
            break
        
        print(f"🔍 Searching: '{query}'")
        videos = search_pexels_videos(query, api_key, per_page=2)
        
        if not videos:
            print("   No videos found\n")
            continue
        
        print(f"   Found {len(videos)} videos")
        
        # ดาวน์โหลดวิดีโอแรก
        video = videos[0]
        filename = f"broll_{downloaded+1:02d}_{query.replace(' ', '_')[:20]}.mp4"
        output_path = output_dir / filename
        
        if output_path.exists():
            print(f"   ⏭️  Skipping (already exists): {filename}\n")
            downloaded += 1
            continue
        
        if download_video(video['url'], output_path):
            downloaded += 1
            download_info.append({
                'file': filename,
                'query': query,
                'duration': video['duration'],
                'resolution': f"{video['width']}x{video['height']}",
                'photographer': video['photographer']
            })
            print()
        
        # Rate limiting (Pexels: 200 requests/hour)
        time.sleep(2)
    
    # สร้าง metadata
    if download_info:
        metadata_file = output_dir / 'broll_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_videos': len(download_info),
                'source': 'Pexels (free)',
                'downloads': download_info,
                'license': 'Pexels License - Free for personal and commercial use',
                'attribution': 'Optional but appreciated'
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Downloaded {len(download_info)} videos")
        print(f"📄 Metadata saved: {metadata_file.name}")
    else:
        print("\n⚠️  No videos downloaded")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Review downloaded B-roll videos")
    print("   2. Import into DaVinci Resolve or video editor")
    print("   3. Use visual_guide.json to match B-roll to timestamps")
    print("   4. Trim and edit as needed")


if __name__ == '__main__':
    main()
