"""
Quick OpenAI API Test
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

from openai import OpenAI
import httpx

print("กำลังทดสอบ OpenAI API...\n")

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key[:15]}...\n")

# สร้าง client โดย bypass SSL verification (สำหรับทดสอบ)
http_client = httpx.Client(verify=False)
client = OpenAI(api_key=api_key, http_client=http_client)

print("ส่งคำถาม: อธิบายอนาปานสติใน 2-3 ประโยค\n")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "อธิบายอนาปานสติแบบสั้นๆ ใน 2-3 ประโยค"}
    ],
    max_tokens=150
)

answer = response.choices[0].message.content
tokens = response.usage.total_tokens

print("="*60)
print("คำตอบจาก GPT-4o-mini:")
print("="*60)
print(answer)
print("="*60)
print(f"\nTokens ใช้: {tokens}")
print("ราคา: ~$0.0001 (ถูกมาก)")
print("\n✅ OpenAI API ทำงานได้ปกติ!")
