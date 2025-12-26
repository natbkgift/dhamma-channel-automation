#!/usr/bin/env python3
"""List all Thai voices from Google Cloud TTS"""
from google.cloud import texttospeech
import os

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'astral-shape-439509-h4-2cfc6b202fa3.json'

# Create client
client = texttospeech.TextToSpeechClient()

# List voices
voices = client.list_voices(language_code='th-TH')

print("🎙️ เสียงภาษาไทยทั้งหมดที่มีใน Google Cloud TTS:\n")
print(f"{'Name':<35} {'Gender':<12} {'Type':<15}")
print("=" * 70)

for voice in voices.voices:
    if 'th-TH' in voice.language_codes:
        gender = "ผู้ชาย (MALE)" if voice.ssml_gender == 1 else "ผู้หญิง (FEMALE)"
        
        # Determine voice type
        if 'Neural2' in voice.name:
            voice_type = "Neural2 (Best)"
        elif 'Wavenet' in voice.name:
            voice_type = "WaveNet"
        elif 'Standard' in voice.name:
            voice_type = "Standard (Free)"
        else:
            voice_type = "Other"
        
        print(f"{voice.name:<35} {gender:<12} {voice_type:<15}")

print("\n" + "=" * 70)
print("📝 หมายเหตุ:")
print("   • Neural2 = คุณภาพสูงสุด, เสียงธรรมชาติ ($16/1M chars)")
print("   • WaveNet = คุณภาพสูง (อาจถูก deprecated)")
print("   • Standard = คุณภาพมาตรฐาน (ฟรี)")
