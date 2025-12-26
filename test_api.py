"""
Test Real APIs - YouTube Data API + OpenAI GPT-4
ทดสอบการเชื่อมต่อ API จริง
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# โหลด environment variables
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

load_env()

# ========== TEST YOUTUBE API ==========

def test_youtube_api():
    """ทดสอบ YouTube Data API - ค้นหาวิดีโอธรรมะ"""
    print("\n" + "="*60)
    print("  TEST 1: YouTube Data API")
    print("="*60)
    
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    if not api_key or api_key == "your_youtube_api_key_here":
        print("❌ YOUTUBE_API_KEY ไม่ได้ตั้งค่าใน .env")
        print("   กรุณาเพิ่ม API key ของคุณใน .env file")
        return False
    
    print(f"✓ API Key พบ: {api_key[:20]}...")
    
    try:
        from googleapiclient.discovery import build
        
        print("\nกำลังเชื่อมต่อ YouTube API...")
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # ทดสอบ 1: ค้นหาวิดีโอธรรมะ
        print("\n📺 ทดสอบค้นหาวิดีโอ: 'ธรรมะ meditation'")
        search_response = youtube.search().list(
            q='ธรรมะ meditation',
            part='snippet',
            type='video',
            maxResults=5,
            relevanceLanguage='th',
            order='viewCount'
        ).execute()
        
        print(f"\n✓ พบ {len(search_response['items'])} วิดีโอ\n")
        
        results = []
        for i, item in enumerate(search_response['items'], 1):
            video = {
                'rank': i,
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle'],
                'published': item['snippet']['publishedAt'][:10],
                'video_id': item['id']['videoId'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            results.append(video)
            
            print(f"{i}. {video['title']}")
            print(f"   Channel: {video['channel']}")
            print(f"   Published: {video['published']}")
            print(f"   URL: {video['url']}\n")
        
        # ทดสอบ 2: ดึงสถิติวิดีโอ
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        print("\n📊 ทดสอบดึงสถิติวิดีโอ...")
        stats_response = youtube.videos().list(
            part='statistics,snippet',
            id=','.join(video_ids)
        ).execute()
        
        print(f"✓ ดึงสถิติ {len(stats_response['items'])} วิดีโอ\n")
        
        for i, item in enumerate(stats_response['items'], 1):
            stats = item['statistics']
            print(f"{i}. {item['snippet']['title'][:50]}...")
            print(f"   Views: {int(stats.get('viewCount', 0)):,}")
            print(f"   Likes: {int(stats.get('likeCount', 0)):,}")
            print(f"   Comments: {int(stats.get('commentCount', 0)):,}\n")
        
        # บันทึกผล
        output = {
            'test': 'youtube_api',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'api_key_status': 'configured',
            'search_query': 'ธรรมะ meditation',
            'results_count': len(results),
            'videos': results,
            'quota_used': 'approximately 3 units'
        }
        
        output_dir = Path(__file__).parent / "output" / "api_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"youtube_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ บันทึกผลทดสอบ: {output_file.relative_to(Path.cwd())}")
        print("\n" + "="*60)
        print("✅ YouTube API: ทำงานได้ปกติ")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nสาเหตุที่เป็นไปได้:")
        print("1. API Key ไม่ถูกต้อง")
        print("2. YouTube Data API v3 ยังไม่ได้เปิดใช้งาน")
        print("3. Quota เกินกำหนด")
        print("\nวิธีแก้:")
        print("1. ไปที่ https://console.cloud.google.com/apis/credentials")
        print("2. ตรวจสอบ API Key")
        print("3. เปิดใช้งาน YouTube Data API v3")
        return False


# ========== TEST OPENAI API ==========

def test_openai_api():
    """ทดสอบ OpenAI API - สร้างข้อความด้วย GPT-4"""
    print("\n" + "="*60)
    print("  TEST 2: OpenAI GPT-4 API")
    print("="*60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY ไม่ได้ตั้งค่าใน .env")
        print("   กรุณาเพิ่ม API key ของคุณใน .env file")
        return False
    
    print(f"✓ API Key พบ: {api_key[:15]}...")
    
    try:
        from openai import OpenAI
        import httpx
        print("\nกำลังเชื่อมต่อ OpenAI API...")
        # Bypass SSL ใน dev (Windows)
        client = OpenAI(api_key=api_key, http_client=httpx.Client(verify=False))
        print("\n🤖 ใช้ model: gpt-4o-mini")
        print("   (ประหยัดกว่า gpt-4 ราคาถูกกว่า 60 เท่า)")
        # ทดสอบ 2: สร้างข้อความธรรมะสั้นๆ
        print("\n✍️  ทดสอบสร้างเนื้อหา: 'อธิบายอนาปานสติแบบสั้น'")
        
        prompt = """คุณคือครูสอนธรรมะที่เชี่ยวชาญ
        
กรุณาอธิบาย "อนาปานสติ" แบบสั้นๆ ภายใน 3-4 ประโยค 
ให้เข้าใจง่าย เหมาะสำหรับผู้เริ่มต้น"""

        print(f"\nPrompt: {prompt.strip()}\n")
        print("กำลังรอคำตอบจาก GPT-4...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # ใช้ gpt-4o-mini ประหยัดกว่า
            messages=[
                {"role": "system", "content": "คุณคือครูสอนธรรมะที่อธิบายได้เข้าใจง่าย"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        
        print("\n" + "─"*60)
        print("📝 คำตอบจาก GPT-4:")
        print("─"*60)
        print(answer)
        print("─"*60)
        
        # แสดงข้อมูลการใช้งาน
        usage = response.usage
        print(f"\n💰 Token Usage:")
        print(f"   Prompt tokens: {usage.prompt_tokens}")
        print(f"   Completion tokens: {usage.completion_tokens}")
        print(f"   Total tokens: {usage.total_tokens}")
        
        # ทดสอบ 3: สร้างหัวข้อวิดีโอ
        print("\n\n💡 ทดสอบสร้างไอเดียหัวข้อวิดีโอ...")
        
        response2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "คุณคือผู้เชี่ยวชาญคอนเทนต์ธรรมะบน YouTube"},
                {"role": "user", "content": "เสนอ 3 หัวข้อวิดีโอธรรมะที่น่าสนใจสำหรับคนรุ่นใหม่ (แต่ละหัวข้อไม่เกิน 15 คำ)"}
            ],
            max_tokens=150,
            temperature=0.8
        )
        
        topics = response2.choices[0].message.content
        
        print("\n📺 หัวข้อที่แนะนำ:")
        print("─"*60)
        print(topics)
        print("─"*60)
        
        # บันทึกผล
        output = {
            'test': 'openai_api',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'api_key_status': 'configured',
            'model_used': 'gpt-4o-mini',
            'test_1': {
                'task': 'อธิบายอนาปานสติ',
                'response': answer,
                'tokens': usage.total_tokens
            },
            'test_2': {
                'task': 'เสนอหัวข้อวิดีโอ',
                'response': topics,
                'tokens': response2.usage.total_tokens
            }
        }
        
        output_dir = Path(__file__).parent / "output" / "api_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"openai_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ บันทึกผลทดสอบ: {output_file.relative_to(Path.cwd())}")
        print("\n" + "="*60)
        print("✅ OpenAI API: ทำงานได้ปกติ")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nสาเหตุที่เป็นไปได้:")
        print("1. API Key ไม่ถูกต้อง")
        print("2. ไม่มี credits เหลือ")
        print("3. Rate limit exceeded")
        print("\nวิธีแก้:")
        print("1. ตรวจสอบ API Key ที่ https://platform.openai.com/api-keys")
        print("2. ตรวจสอบ usage ที่ https://platform.openai.com/usage")
        print("3. เติม credits ถ้าจำเป็น")
        return False


# ========== TEST COMBINED ==========

def test_combined_workflow():
    """ทดสอบเวิร์กโฟลว์รวม: YouTube → OpenAI"""
    print("\n" + "="*60)
    print("  TEST 3: Combined Workflow")
    print("  YouTube Search → GPT-4 Analysis")
    print("="*60)
    
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not youtube_key or not openai_key:
        print("❌ ต้องมี API keys ทั้ง YouTube และ OpenAI")
        return False
    
    try:
        from googleapiclient.discovery import build
        from openai import OpenAI
        import httpx
        # Step 1: ค้นหาวิดีโอธรรมะยอดนิยม
        print("\n1️⃣  ค้นหาวิดีโอธรรมะยอดนิยมจาก YouTube...")
        youtube = build('youtube', 'v3', developerKey=youtube_key)
        search_response = youtube.search().list(
            q='ธรรมะ สมาธิ',
            part='snippet',
            type='video',
            maxResults=3,
            relevanceLanguage='th',
            order='viewCount'
        ).execute()
        video_titles = [item['snippet']['title'] for item in search_response['items']]
        print(f"✓ พบ {len(video_titles)} วิดีโอ:")
        for i, title in enumerate(video_titles, 1):
            print(f"   {i}. {title}")
        # Step 2: ให้ GPT-4 วิเคราะห์เทรนด์
        print("\n2️⃣  ส่งให้ GPT-4 วิเคราะห์เทรนด์...")
        client = OpenAI(api_key=openai_key, http_client=httpx.Client(verify=False))
        prompt = f"""วิเคราะห์หัวข้อวิดีโอธรรมะยอดนิยมเหล่านี้:

{chr(10).join(f'{i}. {title}' for i, title in enumerate(video_titles, 1))}

กรุณาวิเคราะห์:
1. เทรนด์ที่เห็นได้ชัด
2. สิ่งที่คนสนใจ
3. แนะนำหัวข้อใหม่ที่น่าจะฮิต 2 หัวข้อ

ตอบแบบกระชับ"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "คุณคือนักวิเคราะห์เทรนด์คอนเทนต์ธรรมะ"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        analysis = response.choices[0].message.content
        
        print("\n" + "─"*60)
        print("📊 การวิเคราะห์จาก GPT-4:")
        print("─"*60)
        print(analysis)
        print("─"*60)
        
        # บันทึกผล
        output = {
            'test': 'combined_workflow',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'step_1': {
                'source': 'YouTube Data API',
                'query': 'ธรรมะ สมาธิ',
                'videos_found': len(video_titles),
                'titles': video_titles
            },
            'step_2': {
                'source': 'OpenAI GPT-4',
                'task': 'วิเคราะห์เทรนด์',
                'analysis': analysis,
                'tokens_used': response.usage.total_tokens
            }
        }
        
        output_dir = Path(__file__).parent / "output" / "api_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"combined_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ บันทึกผลทดสอบ: {output_file.relative_to(Path.cwd())}")
        print("\n" + "="*60)
        print("✅ Combined Workflow: ทำงานได้ปกติ")
        print("   YouTube + OpenAI ทำงานร่วมกันได้ดี!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


# ========== MAIN ==========

def main():
    print("\n" + "🔬 API TESTING TOOL".center(60, "="))
    print("Testing YouTube Data API + OpenAI GPT-4\n")
    
    results = {
        'youtube': False,
        'openai': False,
        'combined': False
    }
    
    # Test 1: YouTube API
    try:
        results['youtube'] = test_youtube_api()
    except KeyboardInterrupt:
        print("\n\n⚠️  ผู้ใช้ยกเลิก")
        return
    except Exception as e:
        print(f"\n❌ YouTube API Test Failed: {e}")
    
    input("\n\nกด Enter เพื่อทดสอบ OpenAI API...")
    
    # Test 2: OpenAI API
    try:
        results['openai'] = test_openai_api()
    except KeyboardInterrupt:
        print("\n\n⚠️  ผู้ใช้ยกเลิก")
        return
    except Exception as e:
        print(f"\n❌ OpenAI API Test Failed: {e}")
    
    # Test 3: Combined (ถ้า 2 ตัวแรกผ่าน)
    if results['youtube'] and results['openai']:
        input("\n\nกด Enter เพื่อทดสอบ Combined Workflow...")
        try:
            results['combined'] = test_combined_workflow()
        except Exception as e:
            print(f"\n❌ Combined Test Failed: {e}")
    
    # สรุปผล
    print("\n\n" + "="*60)
    print("  📊 สรุปผลการทดสอบ")
    print("="*60)
    
    status_icon = lambda x: "✅" if x else "❌"
    
    print(f"\n{status_icon(results['youtube'])} YouTube Data API: {'ผ่าน' if results['youtube'] else 'ไม่ผ่าน'}")
    print(f"{status_icon(results['openai'])} OpenAI GPT-4 API: {'ผ่าน' if results['openai'] else 'ไม่ผ่าน'}")
    print(f"{status_icon(results['combined'])} Combined Workflow: {'ผ่าน' if results['combined'] else 'ไม่ผ่าน/ข้าม'}")
    
    all_passed = results['youtube'] and results['openai']
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ระบบพร้อมใช้งานจริง!")
        print("   สามารถเริ่มสร้างคอนเทนต์อัตโนมัติได้แล้ว")
    else:
        print("⚠️  กรุณาแก้ไข API keys ก่อนใช้งาน")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการทดสอบ")
        sys.exit(0)
