"""
Quick YouTube API Test
ทดสอบ YouTube Data API แบบเร็ว
"""
import os
from pathlib import Path

# โหลด .env
env_file = Path(".env")
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

from googleapiclient.discovery import build

print("\n" + "="*60)
print("  🔍 ทดสอบ YouTube Data API")
print("="*60)

api_key = os.getenv("YOUTUBE_API_KEY")
print(f"\n✓ API Key: {api_key[:20]}...\n")

try:
    # สร้าง YouTube client
    print("กำลังเชื่อมต่อ YouTube API...")
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # ทดสอบ 1: ค้นหาวิดีโอธรรมะ
    print("\n📺 ค้นหาวิดีโอ: 'ธรรมะ สมาธิ'\n")
    
    search_response = youtube.search().list(
        q='ธรรมะ สมาธิ',
        part='snippet',
        type='video',
        maxResults=5,
        relevanceLanguage='th',
        order='viewCount'
    ).execute()
    
    print(f"✅ พบ {len(search_response['items'])} วิดีโอ\n")
    print("="*60)
    
    for i, item in enumerate(search_response['items'], 1):
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        published = item['snippet']['publishedAt'][:10]
        video_id = item['id']['videoId']
        
        print(f"\n{i}. {title}")
        print(f"   Channel: {channel}")
        print(f"   Published: {published}")
        print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    
    print("\n" + "="*60)
    
    # ทดสอบ 2: ดึงสถิติวิดีโอ
    print("\n📊 ดึงสถิติวิดีโอ...\n")
    
    video_ids = [item['id']['videoId'] for item in search_response['items']]
    
    stats_response = youtube.videos().list(
        part='statistics,snippet',
        id=','.join(video_ids[:3])  # เอาแค่ 3 อันแรก
    ).execute()
    
    print("="*60)
    for i, item in enumerate(stats_response['items'], 1):
        stats = item['statistics']
        title = item['snippet']['title'][:50]
        
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        
        print(f"\n{i}. {title}...")
        print(f"   👁  Views: {views:,}")
        print(f"   👍 Likes: {likes:,}")
        print(f"   💬 Comments: {comments:,}")
    
    print("\n" + "="*60)
    print("✅ YouTube API ทำงานได้ปกติ!")
    print("="*60)
    print(f"\n💰 Quota ใช้: ~3 units (เหลือ ~9,997/10,000)")
    print("\nพร้อมใช้งานจริงได้เลย! 🚀\n")
    
except Exception as e:
    print("\n" + "="*60)
    print(f"❌ Error: {e}")
    print("="*60)
    
    if "quota" in str(e).lower():
        print("\n⚠️  Quota เกินกำหนด")
        print("   รอพรุ่งนี้หรือ upgrade quota")
    elif "403" in str(e):
        print("\n⚠️  ปัญหาการเข้าถึง")
        print("   1. ตรวจสอบ API Key")
        print("   2. เปิดใช้งาน YouTube Data API v3")
    else:
        print("\n⚠️  ปัญหาอื่นๆ")
        print("   ตรวจสอบ: https://console.cloud.google.com")
