"""
Demo: ใช้ OpenAI GPT-4 สร้างสคริปต์วิดีโอจริง
"""
import os
from pathlib import Path
import json
from datetime import datetime

# โหลด .env
env_file = Path(".env")
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

from openai import OpenAI
import httpx

def create_script_with_gpt4(topic, duration="8-10 minutes"):
    """สร้างสคริปต์วิดีโอด้วย GPT-4"""
    
    print("\n" + "="*60)
    print(f"  🎬 สร้างสคริปต์: {topic}")
    print("="*60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    # สร้าง client
    http_client = httpx.Client(verify=False)
    client = OpenAI(api_key=api_key, http_client=http_client)
    
    # Prompt สำหรับสร้างสคริปต์
    prompt = f"""คุณคือนักเขียนสคริปต์วิดีโอธรรมะมืออาชีพ

งาน: เขียนสคริปต์วิดีโอหัวข้อ "{topic}"

ข้อกำหนด:
- ความยาว: {duration}
- กลุ่มเป้าหมาย: คนทั่วไป ผู้เริ่มต้น
- น้ำเสียง: เป็นกันเอง อธิบายง่าย
- มีตัวอย่างชีวิตจริง
- อ้างอิงหลักธรรมที่เกี่ยวข้อง

โครงสร้าง:
1. Hook (30 วินาที) - ดึงดูดใจใน 5 วินาทีแรก
2. ปัญหา/บริบท (90 วินาที) - ปัญหาที่ผู้ชมเจอ
3. หลักธรรม (2 นาที) - อธิบายหลักธรรมที่เกี่ยวข้อง
4. วิธีปฏิบัติ (3 นาที) - ขั้นตอนชัดเจน ทำได้จริง
5. ตัวอย่าง (1 นาที) - case study หรือเรื่องจริง
6. สรุป + CTA (30 วินาที) - สรุปและเชิญชวน

เขียนสคริปต์เต็มรูปแบบ พร้อมบอก timing แต่ละส่วน"""

    print("\n📤 ส่งคำขอไปยัง GPT-4o-mini...")
    print(f"Topic: {topic}")
    print(f"Duration: {duration}\n")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "คุณคือนักเขียนสคริปต์วิดีโอธรรมะมืออาชีพ ที่สามารถอธิบายธรรมะให้เข้าใจง่าย น่าสนใจ และเชื่อมโยงกับชีวิตจริง"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        script = response.choices[0].message.content
        tokens = response.usage
        
        print("✅ ได้รับสคริปต์แล้ว!\n")
        print("="*60)
        print("📝 สคริปต์ที่ได้:")
        print("="*60)
        print(script)
        print("="*60)
        
        print(f"\n💰 ข้อมูลการใช้งาน:")
        print(f"   Prompt tokens: {tokens.prompt_tokens}")
        print(f"   Completion tokens: {tokens.completion_tokens}")
        print(f"   Total tokens: {tokens.total_tokens}")
        print(f"   ราคาประมาณ: ${tokens.total_tokens * 0.0000015:.6f}")
        
        # บันทึกผล
        output = {
            "agent": "ScriptWriter_GPT4",
            "topic": topic,
            "duration": duration,
            "script": script,
            "created_at": datetime.now().isoformat(),
            "tokens_used": {
                "prompt": tokens.prompt_tokens,
                "completion": tokens.completion_tokens,
                "total": tokens.total_tokens
            },
            "model": "gpt-4o-mini"
        }
        
        output_dir = Path("output") / "gpt4_scripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # บันทึก JSON
        json_file = output_dir / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # บันทึก Markdown
        md_file = output_dir / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# สคริปต์วิดีโอ: {topic}\n\n")
            f.write(f"**ความยาว:** {duration}\n")
            f.write(f"**สร้างโดย:** GPT-4o-mini\n")
            f.write(f"**วันที่:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(script)
        
        print(f"\n✅ บันทึกสคริปต์:")
        print(f"   📄 {json_file}")
        print(f"   📝 {md_file}")
        
        return output
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


# ========== MAIN ==========

if __name__ == "__main__":
    print("\n" + "🤖 GPT-4 SCRIPT GENERATOR".center(60, "="))
    print("สร้างสคริปต์วิดีโอธรรมะด้วย AI\n")
    
    # ตัวอย่างหัวข้อ
    topics = [
        "ทำสมาธิ 5 นาที ลดความเครียด",
        "วิธีรับมือความโกรธด้วยหลักธรรม",
        "เจริญสติในชีวิตประจำวัน"
    ]
    
    print("หัวข้อที่มี:")
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. {topic}")
    
    print(f"\n  0. ใส่หัวข้อเอง")
    
    try:
        choice = input("\nเลือกหัวข้อ (1-3 หรือ 0): ").strip()
        
        if choice == "0":
            topic = input("ใส่หัวข้อที่ต้องการ: ").strip()
        elif choice in ["1", "2", "3"]:
            topic = topics[int(choice) - 1]
        else:
            print("❌ ตัวเลือกไม่ถูกต้อง")
            exit(1)
        
        # สร้างสคริปต์
        result = create_script_with_gpt4(topic)
        
        if result:
            print("\n" + "="*60)
            print("🎉 สำเร็จ! พร้อมนำไปผลิตวิดีโอได้เลย")
            print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิก")
    except Exception as e:
        print(f"\n❌ Error: {e}")
