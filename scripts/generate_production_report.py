#!/usr/bin/env python3
"""
Production Report Generator - สร้าง HTML report สำหรับขั้นตอน manual production

อ่านข้อมูลจาก output/ และสร้างไฟล์ HTML พร้อมลิงก์ไปยัง:
- โฟลเดอร์ที่เกี่ยวข้อง
- เว็บไซต์/เครื่องมือที่ต้องใช้
- คำแนะนำ step-by-step
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import os


def load_json_safe(file_path: Path) -> dict:
    """โหลด JSON file อย่างปลอดภัย"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load {file_path.name}: {e}")
        return {}


def get_file_info(file_path: Path) -> dict:
    """ดึงข้อมูลไฟล์"""
    if file_path.exists():
        size = file_path.stat().st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        
        return {
            'exists': True,
            'size': size_str,
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        }
    return {'exists': False}


def generate_html_report(run_id: str, base_dir: Path) -> str:
    """สร้าง HTML report"""
    
    # Paths
    output_dir = base_dir / 'output' / run_id
    audio_dir = base_dir / 'audio' / run_id
    template_dir = base_dir / 'templates' / run_id
    canva_dir = base_dir / 'templates' / 'canva'
    broll_dir = base_dir / 'broll' / run_id
    
    # Load metadata
    metadata = load_json_safe(output_dir / 'metadata.json')
    voiceover_guide = load_json_safe(output_dir / 'voiceover_guide.json')
    visual_guide = load_json_safe(output_dir / 'visual_guide.json')
    thumbnail_concepts = load_json_safe(output_dir / 'thumbnail_concepts.json')
    topics_ranked = load_json_safe(output_dir / 'topics_ranked.json')
    
    # Video info - get title from topics_ranked (most accurate)
    if topics_ranked and 'topic_override' in topics_ranked:
        title = topics_ranked['topic_override']
    elif topics_ranked and 'ranked' in topics_ranked and len(topics_ranked['ranked']) > 0:
        title = topics_ranked['ranked'][0]['title']
    else:
        title = metadata.get('title', 'Untitled Video')
    
    description = metadata.get('description', '')
    
    # Calculate duration from voiceover_guide
    duration = "0:00 นาที"  # default
    
    # First priority: actual duration from audio file
    if metadata and 'actual_duration_seconds' in metadata:
        total_seconds = metadata['actual_duration_seconds']
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        duration = f"{minutes}:{seconds:02d} นาที"
    # Second priority: voiceover_guide
    elif voiceover_guide and 'sections' in voiceover_guide:
        # Try to get duration_seconds if available
        if any('duration_seconds' in section for section in voiceover_guide['sections']):
            total_seconds = sum(section.get('duration_seconds', 0) for section in voiceover_guide['sections'])
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            duration = f"{minutes}:{seconds:02d} นาที"
        else:
            # Parse from last section's timestamp (e.g., "08:30-10:00")
            last_section = voiceover_guide['sections'][-1]
            if 'timestamp' in last_section:
                timestamp = last_section['timestamp']
                # Extract end time (e.g., "10:00" from "08:30-10:00")
                if '-' in timestamp:
                    end_time = timestamp.split('-')[1].strip()
                    # Parse MM:SS
                    parts = end_time.split(':')
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        duration = f"{minutes}:{seconds:02d} นาที"
    
    # Fallback to metadata estimate
    if duration == "0:00 นาที" and metadata:
        duration = metadata.get('duration', '8-10 นาที')
    
    tags = metadata.get('tags', [])
    
    # File checks
    script_file = get_file_info(output_dir / 'script_validated.md')
    recording_simple = get_file_info(audio_dir / 'recording_script_SIMPLE.txt')
    recording_detailed = get_file_info(audio_dir / 'recording_script_DETAILED.txt')
    timeline_edl = get_file_info(template_dir / 'timeline.edl')
    timeline_csv = get_file_info(template_dir / 'timeline.csv')
    editing_guide = get_file_info(template_dir / 'EDITING_GUIDE.md')
    canva_guide = get_file_info(canva_dir / 'CANVA_GUIDE.md')
    
    # Count sections
    sections_dir = audio_dir / 'sections'
    section_count = len(list(sections_dir.glob('*.txt'))) if sections_dir.exists() else 0
    
    # Count scenes
    scene_count = len(visual_guide.get('scenes', []))
    
    # Count thumbnails
    thumbnail_count = len(thumbnail_concepts.get('concepts', []))
    
    # Absolute paths for file:/// links
    abs_output = output_dir.resolve()
    abs_audio = audio_dir.resolve()
    abs_template = template_dir.resolve()
    abs_canva = canva_dir.resolve()
    abs_broll = broll_dir.resolve()
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Production Guide - {run_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header .run-id {{
            font-size: 1.2em;
            opacity: 0.9;
            font-family: 'Courier New', monospace;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .video-info {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }}
        
        .video-info h2 {{
            font-size: 2em;
            margin-bottom: 15px;
        }}
        
        .video-info .meta {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 15px;
            font-size: 0.95em;
        }}
        
        .video-info .meta-item {{
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 8px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .step {{
            background: #f8f9fa;
            border-left: 5px solid #667eea;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            transition: all 0.3s ease;
        }}
        
        .step:hover {{
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .step-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .step-number {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2em;
            margin-right: 15px;
        }}
        
        .step h3 {{
            color: #333;
            font-size: 1.4em;
            margin: 0;
        }}
        
        .step-content {{
            margin-left: 55px;
        }}
        
        .file-list {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        
        .file-item {{
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .file-item.exists {{
            border-left: 4px solid #28a745;
        }}
        
        .file-item.missing {{
            border-left: 4px solid #dc3545;
            opacity: 0.6;
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            margin: 5px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-secondary {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        
        .btn-success {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }}
        
        .btn-info {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        
        .tools {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .tool-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .tool-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        .tool-card h4 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .checklist {{
            list-style: none;
            padding: 0;
        }}
        
        .checklist li {{
            padding: 10px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 5px;
            padding-left: 40px;
            position: relative;
        }}
        
        .checklist li:before {{
            content: "☐";
            position: absolute;
            left: 15px;
            font-size: 1.3em;
            color: #667eea;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
            margin-top: 40px;
        }}
        
        .tag {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            margin: 3px;
            font-size: 0.85em;
        }}
        
        .btn-ai {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }}
        
        .btn-ai:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-ai:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .progress-container {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }}
        
        .progress-container.active {{
            display: block;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }}
        
        .progress-status {{
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }}
        
        .download-link {{
            margin-top: 15px;
            display: none;
        }}
        
        .download-link.active {{
            display: block;
        }}
        
        .ai-section {{
            margin: 20px 0;
            padding: 20px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .btn {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Production Guide</h1>
            <div class="run-id">Run ID: {run_id}</div>
            <div style="margin-top: 15px; opacity: 0.8;">
                สร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </div>
        
        <div class="content">
            <!-- Video Information -->
            <div class="video-info">
                <h2>📹 {title}</h2>
                <p style="margin: 10px 0; white-space: pre-wrap;">{description}</p>
                <div class="meta">
                    <div class="meta-item">⏱️ ระยะเวลา: {duration}</div>
                    <div class="meta-item">📝 Sections: {section_count}</div>
                    <div class="meta-item">🎞️ Scenes: {scene_count}</div>
                    <div class="meta-item">🖼️ Thumbnails: {thumbnail_count}</div>
                </div>
                {f'''<div style="margin-top: 15px;">
                    {' '.join([f'<span class="tag">#{tag}</span>' for tag in tags[:10]])}
                </div>''' if tags else ''}
            </div>
            
            <!-- Statistics -->
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">AI Generated Files</div>
                    <div class="stat-number">{len(list(output_dir.glob('*.*'))) if output_dir.exists() else 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Recording Sections</div>
                    <div class="stat-number">{section_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Video Scenes</div>
                    <div class="stat-number">{scene_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Thumbnail Concepts</div>
                    <div class="stat-number">{thumbnail_count}</div>
                </div>
            </div>
            
            <!-- Quick Links -->
            <div class="section">
                <h2>🔗 Quick Links</h2>
                <div style="text-align: center; padding: 20px;">
                    <a href="file:///{abs_output}" class="btn">📂 Output Folder</a>
                    <a href="file:///{abs_audio}" class="btn">🎙️ Audio Scripts</a>
                    <a href="file:///{abs_template}" class="btn">🎬 Video Templates</a>
                    <a href="file:///{abs_canva}" class="btn">🖼️ Thumbnail Guide</a>
                </div>
            </div>
            
            <!-- Production Steps -->
            <div class="section">
                <h2>📋 Production Workflow</h2>
                
                <!-- Step 1: Voiceover Recording -->
                <div class="step">
                    <div class="step-header">
                        <div class="step-number">1</div>
                        <h3>🎙️ บันทึกเสียง (Voiceover Recording)</h3>
                    </div>
                    <div class="step-content">
                        <p><strong>เครื่องมือที่แนะนำ:</strong></p>
                        <div class="tools">
                            <div class="tool-card">
                                <h4>Audacity (Free)</h4>
                                <p>โปรแกรมบันทึก/ตัดต่อเสียงฟรี</p>
                                <a href="https://www.audacityteam.org/" target="_blank" class="btn btn-info">Download</a>
                            </div>
                            <div class="tool-card">
                                <h4>OBS Studio (Free)</h4>
                                <p>บันทึกเสียง+วิดีโอพร้อมกัน</p>
                                <a href="https://obsproject.com/" target="_blank" class="btn btn-info">Download</a>
                            </div>
                        </div>
                        
                        <p><strong>ไฟล์สำหรับบันทึก:</strong></p>
                        <div class="file-list">
                            <div class="file-item {'exists' if recording_simple['exists'] else 'missing'}">
                                <span>📄 recording_script_SIMPLE.txt</span>
                                <span>{recording_simple.get('size', 'N/A')}</span>
                            </div>
                            <div class="file-item {'exists' if recording_detailed['exists'] else 'missing'}">
                                <span>📄 recording_script_DETAILED.txt (มี timing)</span>
                                <span>{recording_detailed.get('size', 'N/A')}</span>
                            </div>
                            <div class="file-item {'exists' if sections_dir.exists() else 'missing'}">
                                <span>📁 sections/ ({section_count} ไฟล์)</span>
                                <span>บันทึกทีละ section</span>
                            </div>
                        </div>
                        
                        <a href="file:///{abs_audio}" class="btn btn-success">เปิดโฟลเดอร์ Audio</a>
                        
                        <div class="ai-section">
                            <h4 style="margin-top: 0; color: #667eea;">🤖 สร้างเสียงบรรยายด้วย AI (Text-to-Speech)</h4>
                            <p>ใช้ AI สร้างเสียงบรรยายอัตโนมัติจากสคริปต์ (ใช้ API key ที่ตั้งไว้ใน .env)</p>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600;">🔧 TTS Provider:</label>
                                    <select id="ttsProvider" onchange="updateVoiceOptions()" style="width: 100%; padding: 8px; border-radius: 5px; border: 1px solid #ddd;">
                                        <option value="google">Google Cloud TTS (แนะนำสำหรับภาษาไทย)</option>
                                        <option value="openai">OpenAI TTS</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600;">🎤 Voice:</label>
                                    <select id="ttsVoice" style="width: 100%; padding: 8px; border-radius: 5px; border: 1px solid #ddd;">
                                        <!-- Populated by updateVoiceOptions() -->
                                    </select>
                                    <script>
                                        // Immediate initialization fallback
                                        if (document.getElementById('ttsVoice').options.length === 0) {{
                                            console.warn('Voice dropdown empty, forcing update...');
                                            setTimeout(function() {{
                                                if (typeof updateVoiceOptions === 'function') {{
                                                    updateVoiceOptions();
                                                }}
                                            }}, 100);
                                        }}
                                    </script>
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; font-weight: 600;">⚡ Speed: <span id="speedValue">0.88</span>x</label>
                                <input type="range" id="ttsSpeed" min="0.5" max="2.0" step="0.01" value="0.88" 
                                       oninput="document.getElementById('speedValue').textContent = this.value + 'x'" 
                                       style="width: 100%;">
                                <small style="display: block; color: #666; margin-top: 5px;">
                                    แนะนำ: 0.85x (ช้า สงบ) | 0.88x (สมดุล ⭐) | 0.92x (ปกติ) | 1.0x (เร็ว)
                                </small>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" id="ttsUseSSML" checked style="width: 18px; height: 18px; cursor: pointer;" onchange="toggleSSMLLevel()">
                                    <span style="font-weight: 600;">🗣️ ปรับสคริปต์เป็น SSML (ธรรมชาติขึ้น)</span>
                                </label>
                                <small style="display: block; margin-left: 26px; color: #666; margin-top: 5px;">
                                    ใช้ SSML Enhancer เพื่อเพิ่มการหยุดจังหวะและการเน้นคำอัตโนมัติ (ระดับ: เลือกได้) ⭐ แนะนำ
                                </small>
                                <div id="ssmlLevelWrapper" style="margin-left: 26px; margin-top: 8px; display: block;">
                                    <label for="ttsSSMLLevel" style="font-weight:600; display:flex; align-items:center; gap:6px; margin-bottom:4px;">ระดับ SSML:
                                        <span style="cursor:help; font-size:12px; background:#eee; padding:2px 6px; border-radius:4px;" title="Low: เพิ่ม pause เล็กน้อย / เน้นคำน้อยที่สุด\nMedium: สมดุล pause + emphasis (แนะนำ)\nHigh: เพิ่ม pause ชัด / เน้นคำสำคัญมากขึ้น\nเลือกเพื่อปรับจังหวะให้อ่านเป็นธรรมชาติ">ℹ️</span>
                                    </label>
                                    <select id="ttsSSMLLevel" style="padding:6px 10px; border-radius:6px; border:1px solid #ccc;">
                                        <option value="low">Low - นุ่มนวลน้อยสุด</option>
                                        <option value="medium" selected>Medium - สมดุล (แนะนำ)</option>
                                        <option value="high">High - เน้นจังหวะมาก</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" id="ttsContentOnly" checked style="width: 18px; height: 18px; cursor: pointer;">
                                    <span style="font-weight: 600;">📝 เฉพาะเนื้อหาพากย์ (แนะนำ!)</span>
                                </label>
                                <small style="display: block; margin-left: 26px; color: #666; margin-top: 5px;">
                                    แยกเฉพาะเนื้อหาที่ต้องพากย์ ลบ metadata, [VISUAL:], คำสั่งผลิต และแยกประโยคยาว (~67% ประหยัดกว่า)
                                </small>
                            </div>
                            
                            <button class="btn-ai" onclick="generateTTS(event)">
                                <span>🎙️</span>
                                <span>สร้างเสียงด้วย AI</span>
                            </button>
                            
                            <div id="ttsProgress" class="progress-container">
                                <div class="progress-bar">
                                    <div id="progressFill" class="progress-fill" style="width: 0%">0%</div>
                                </div>
                                <div id="progressStatus" class="progress-status">กำลังเตรียมข้อมูล...</div>
                            </div>
                            
                            <div id="downloadLink" class="download-link">
                                <a href="file:///{abs_audio}" class="btn btn-success">� เปิดโฟลเดอร์ Audio</a>
                            </div>
                        </div>
                        
                        <p><strong>Checklist:</strong></p>
                        <ul class="checklist">
                            <li>อ่านสคริปต์ SIMPLE ทั้งหมดก่อน</li>
                            <li>ฝึกซ้อมการออกเสียง</li>
                            <li>ตรวจสอบไมโครโฟน (ลด noise)</li>
                            <li>บันทึกทีละ section ตาม DETAILED script</li>
                            <li>บันทึก 2-3 takes เพื่อเลือกที่ดีที่สุด</li>
                            <li>Edit ด้วย Audacity: Noise Reduction + Normalize to -3dB</li>
                            <li>Export เป็น MP3 (192 kbps) หรือ WAV (48kHz, 16-bit)</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Step 2: Video Editing -->
                <div class="step">
                    <div class="step-header">
                        <div class="step-number">2</div>
                        <h3>🎬 ตัดต่อวิดีโอ (Video Editing)</h3>
                    </div>
                    <div class="step-content">
                        <p><strong>เครื่องมือที่แนะนำ:</strong></p>
                        <div class="tools">
                            <div class="tool-card">
                                <h4>DaVinci Resolve (Free)</h4>
                                <p>Professional video editor</p>
                                <a href="https://www.blackmagicdesign.com/products/davinciresolve" target="_blank" class="btn btn-info">Download</a>
                            </div>
                            <div class="tool-card">
                                <h4>CapCut (Free)</h4>
                                <p>ตัดต่อง่าย เหมาะมือใหม่</p>
                                <a href="https://www.capcut.com/" target="_blank" class="btn btn-info">Download</a>
                            </div>
                        </div>
                        
                        <p><strong>ไฟล์เทมเพลต:</strong></p>
                        <div class="file-list">
                            <div class="file-item {'exists' if timeline_edl['exists'] else 'missing'}">
                                <span>📄 timeline.edl</span>
                                <span>{timeline_edl.get('size', 'N/A')}</span>
                            </div>
                            <div class="file-item {'exists' if timeline_csv['exists'] else 'missing'}">
                                <span>📄 timeline.csv ({scene_count} scenes)</span>
                                <span>{timeline_csv.get('size', 'N/A')}</span>
                            </div>
                            <div class="file-item {'exists' if editing_guide['exists'] else 'missing'}">
                                <span>📄 EDITING_GUIDE.md (คู่มือละเอียด)</span>
                                <span>{editing_guide.get('size', 'N/A')}</span>
                            </div>
                        </div>
                        
                        <a href="file:///{abs_template}" class="btn btn-success">เปิดโฟลเดอร์ Templates</a>
                        <a href="https://www.pexels.com/videos/" target="_blank" class="btn btn-secondary">หา B-roll (Pexels)</a>
                        <a href="https://pixabay.com/videos/" target="_blank" class="btn btn-secondary">หา B-roll (Pixabay)</a>
                        
                        <p><strong>Checklist:</strong></p>
                        <ul class="checklist">
                            <li>สร้าง Project ใหม่ใน DaVinci Resolve (1080p, 30fps)</li>
                            <li>Import เสียงบรรยาย (voiceover.mp3)</li>
                            <li>อ่าน EDITING_GUIDE.md ทั้งหมด</li>
                            <li>Download B-roll จาก Pexels/Pixabay ตาม visual_guide</li>
                            <li>วาง B-roll บน timeline ตาม timeline.csv</li>
                            <li>เพิ่ม text overlays (Fusion > Text+)</li>
                            <li>Color grading: warm tones, soft contrast</li>
                            <li>Export MP4 (H.264, 1080p, 10-15 Mbps)</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Step 3: Thumbnail Creation -->
                <div class="step">
                    <div class="step-header">
                        <div class="step-number">3</div>
                        <h3>🖼️ สร้าง Thumbnail</h3>
                    </div>
                    <div class="step-content">
                        <p><strong>เครื่องมือที่แนะนำ:</strong></p>
                        <div class="tools">
                            <div class="tool-card">
                                <h4>Canva (Free)</h4>
                                <p>ออกแบบกราฟิกออนไลน์</p>
                                <a href="https://www.canva.com/" target="_blank" class="btn btn-info">เปิด Canva</a>
                            </div>
                            <div class="tool-card">
                                <h4>Photopea (Free)</h4>
                                <p>Photoshop แบบ web-based</p>
                                <a href="https://www.photopea.com/" target="_blank" class="btn btn-info">เปิด Photopea</a>
                            </div>
                        </div>
                        
                        <p><strong>ไฟล์คู่มือ:</strong></p>
                        <div class="file-list">
                            <div class="file-item {'exists' if canva_guide['exists'] else 'missing'}">
                                <span>📄 CANVA_GUIDE.md (step-by-step)</span>
                                <span>{canva_guide.get('size', 'N/A')}</span>
                            </div>
                            <div class="file-item exists">
                                <span>📄 canva_concept_1.json</span>
                                <span>Concept 1</span>
                            </div>
                            <div class="file-item exists">
                                <span>📄 canva_concept_2.json</span>
                                <span>Concept 2</span>
                            </div>
                            <div class="file-item exists">
                                <span>📄 canva_concept_3.json</span>
                                <span>Concept 3</span>
                            </div>
                        </div>
                        
                        <a href="file:///{abs_canva}" class="btn btn-success">เปิดโฟลเดอร์ Canva</a>
                        <a href="https://www.canva.com/templates/?query=youtube%20thumbnail" target="_blank" class="btn btn-secondary">เทมเพลต Canva</a>
                        
                        <p><strong>Checklist:</strong></p>
                        <ul class="checklist">
                            <li>อ่าน CANVA_GUIDE.md</li>
                            <li>เลือก concept (แนะนำทำทั้ง 3 เพื่อ A/B testing)</li>
                            <li>ค้นหาภาพพื้นหลังจาก Unsplash/Pexels</li>
                            <li>เพิ่มข้อความหลัก (ฟอนต์ใหญ่ชัด อ่านง่าย)</li>
                            <li>ใช้สี contrast สูง (ข้อความต้องชัด)</li>
                            <li>เพิ่ม visual elements ตาม concept</li>
                            <li>ขนาด: 1280x720 pixels</li>
                            <li>Download เป็น JPG (&lt;2MB)</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Step 4: YouTube Upload -->
                <div class="step">
                    <div class="step-header">
                        <div class="step-number">4</div>
                        <h3>📤 อัปโหลดขึ้น YouTube</h3>
                    </div>
                    <div class="step-content">
                        <p><strong>ข้อมูล Metadata:</strong></p>
                        <div class="file-list">
                            <div class="file-item {'exists' if script_file['exists'] else 'missing'}">
                                <span>📄 metadata.json</span>
                                <span>Title, Description, Tags</span>
                            </div>
                            <div class="file-item exists">
                                <span>📄 subtitles_th.srt</span>
                                <span>คำบรรยายภาษาไทย</span>
                            </div>
                        </div>
                        
                        <a href="https://studio.youtube.com/" target="_blank" class="btn btn-success">เปิด YouTube Studio</a>
                        <a href="file:///{abs_output / 'metadata.json'}" class="btn btn-secondary">เปิด metadata.json</a>
                        
                        <p><strong>Checklist:</strong></p>
                        <ul class="checklist">
                            <li>เปิด YouTube Studio</li>
                            <li>Upload ไฟล์วิดีโอ (MP4)</li>
                            <li>คัดลอก Title จาก metadata.json</li>
                            <li>คัดลอก Description (เพิ่ม timestamps ถ้ามี)</li>
                            <li>เพิ่ม Tags (คัดลอกจาก metadata.json)</li>
                            <li>Upload Thumbnail</li>
                            <li>เพิ่มคำบรรยาย (Upload subtitles_th.srt)</li>
                            <li>เลือก Category: Education</li>
                            <li>ตั้งค่า Visibility (Public/Unlisted/Private)</li>
                            <li>Publish!</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Resources -->
            <div class="section">
                <h2>📚 Additional Resources</h2>
                <div class="tools">
                    <div class="tool-card">
                        <h4>Stock Videos</h4>
                        <a href="https://www.pexels.com/videos/" target="_blank" class="btn btn-info">Pexels</a>
                        <a href="https://pixabay.com/videos/" target="_blank" class="btn btn-info">Pixabay</a>
                    </div>
                    <div class="tool-card">
                        <h4>Stock Photos</h4>
                        <a href="https://unsplash.com/" target="_blank" class="btn btn-info">Unsplash</a>
                        <a href="https://www.pexels.com/" target="_blank" class="btn btn-info">Pexels</a>
                    </div>
                    <div class="tool-card">
                        <h4>Background Music</h4>
                        <a href="https://www.youtube.com/audiolibrary" target="_blank" class="btn btn-info">YouTube Audio Library</a>
                    </div>
                    <div class="tool-card">
                        <h4>Fonts (Thai)</h4>
                        <a href="https://fonts.google.com/?subset=thai" target="_blank" class="btn btn-info">Google Fonts</a>
                    </div>
                </div>
            </div>
            
        </div>
        
        <div class="footer">
            <p><strong>🎬 Dhamma Channel Automation</strong></p>
            <p>Generated by Production Orchestrator • {datetime.now().strftime('%Y')}</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                Run ID: <code>{run_id}</code>
            </p>
        </div>
    </div>
    
    <script>
        // Voice options for both providers
        const voiceOptions = {{
            google: [
                // Journey voices - ธรรมชาติที่สุด (⭐ แนะนำ!)
                {{ value: 'th-TH-Journey-D', label: 'ผู้ชาย - อบอุ่น เป็นธรรมชาติ (⭐⭐⭐ แนะนำที่สุด!)' }},
                {{ value: 'th-TH-Journey-F', label: 'ผู้หญิง - นุ่มนวล เป็นมิตร (⭐⭐ แนะนำ!)' }},
                {{ value: 'th-TH-Journey-O', label: 'ผู้ชาย - สงบ เหมาะกับธรรมะ (⭐ แนะนำ)' }},
                
                // Chirp3-HD - คุณภาพดี
                {{ value: 'th-TH-Chirp3-HD-Schedar', label: 'ผู้ชาย - Schedar (นุ่มสงบ)' }},
                {{ value: 'th-TH-Chirp3-HD-Achird', label: 'ผู้ชาย - Achird (ธรรมชาติ)' }},
                {{ value: 'th-TH-Chirp3-HD-Umbriel', label: 'ผู้ชาย - Umbriel (เสียงลึก)' }},
                {{ value: 'th-TH-Chirp3-HD-Alnilam', label: 'ผู้ชาย - Alnilam (ชัดเจน)' }},
                {{ value: 'th-TH-Chirp3-HD-Charon', label: 'ผู้ชาย - Charon (มั่นคง)' }},
                {{ value: 'th-TH-Chirp3-HD-Achernar', label: 'ผู้หญิง - Achernar (นุ่มนวล)' }},
                
                // Neural2 - คุณภาพสูง
                {{ value: 'th-TH-Neural2-C', label: 'ผู้หญิง - Neural2-C (คุณภาพสูง)' }},
                
                // Wavenet - คลาสสิก
                {{ value: 'th-TH-Wavenet-B', label: 'ผู้ชาย - Wavenet-B (เป็นกันเอง)' }},
                {{ value: 'th-TH-Wavenet-D', label: 'ผู้ชาย - Wavenet-D (มั่นใจ)' }},
                {{ value: 'th-TH-Standard-A', label: 'ผู้หญิง - Standard (ฟรี)' }}
            ],
            openai: [
                {{ value: 'alloy', label: 'Alloy - เสียงกลาง' }},
                {{ value: 'echo', label: 'Echo - เสียงผู้ชาย' }},
                {{ value: 'fable', label: 'Fable - เสียงอังกฤษ' }},
                {{ value: 'onyx', label: 'Onyx - เสียงลึก' }},
                {{ value: 'nova', label: 'Nova - เสียงหญิง' }},
                {{ value: 'shimmer', label: 'Shimmer - เสียงนุ่มนวล' }}
            ]
        }};
        
        function updateVoiceOptions() {{
            const provider = document.getElementById('ttsProvider').value;
            const voiceSelect = document.getElementById('ttsVoice');
            
            // Clear existing options
            voiceSelect.innerHTML = '';
            
            // Add new options based on provider
            const voices = voiceOptions[provider] || [];
            voices.forEach((voice, index) => {{
                const option = document.createElement('option');
                option.value = voice.value;
                option.textContent = voice.label;
                // Select Chirp3-HD-Schedar for Google or alloy for OpenAI as default
                if ((provider === 'google' && voice.value === 'th-TH-Chirp3-HD-Schedar') || 
                    (provider === 'openai' && voice.value === 'alloy')) {{
                    option.selected = true;
                }}
                voiceSelect.appendChild(option);
            }});
            
            console.log('Voice options updated:', provider, 'Total voices:', voices.length);
        }}
        
        async function generateTTS(e) {{
            const btn = (e && e.target) ? e.target.closest('button') : document.querySelector('.btn-ai');
            const progressContainer = document.getElementById('ttsProgress');
            const progressFill = document.getElementById('progressFill');
            const progressStatus = document.getElementById('progressStatus');
            const downloadLink = document.getElementById('downloadLink');
            
            // Get user selections
            const provider = document.getElementById('ttsProvider').value;
            const voice = document.getElementById('ttsVoice').value;
            const speed = document.getElementById('ttsSpeed').value;
            const contentOnly = document.getElementById('ttsContentOnly').checked;
            const useSSML = document.getElementById('ttsUseSSML').checked;
            
            // Disable button
            btn.disabled = true;
            
            // Show progress
            progressContainer.classList.add('active');
            downloadLink.classList.remove('active');
            
            try {{
                // Step 1: สร้าง batch file (10%)
                progressFill.style.width = '10%';
                progressFill.textContent = '10%';
                progressStatus.textContent = 'กำลังสร้าง batch file...';
                await new Promise(resolve => setTimeout(resolve, 300));
                
                const scriptPath = String.raw`{str(abs_audio / "recording_script_SIMPLE.txt").replace(chr(92), chr(92)*2)}`;
                const outputPath = String.raw`{str(abs_audio / "voiceover_ai.mp3").replace(chr(92), chr(92)*2)}`;
                
                // สร้างคำสั่งตาม provider (ไม่ใช้ --clean เพื่อให้ preprocessor ทำงาน)
                const contentFlag = contentOnly ? '--content-only' : '';
                const flags = contentFlag;
                
                const ssmlPath = scriptPath.replace(/\.txt$/i, '_ssml.txt');
                // Use forward slashes to avoid JS escape issues; PowerShell accepts them
                const venvPython = `"{Path.cwd().as_posix()}/venv/Scripts/python.exe"`;
                let prepCommand = '';
                let finalScript = scriptPath;
                if (useSSML) {{
                    const ssmlLevel = document.getElementById('ttsSSMLLevel').value || 'medium';
                    prepCommand = `& ${{venvPython}} scripts\ssml_enhancer.py "${{scriptPath}}" "${{ssmlPath}}" --level ${{ssmlLevel}}`;
                    finalScript = ssmlPath;
                }}

                let ttsCommand = '';
                if (provider === 'google') {{
                    ttsCommand = `& ${{venvPython}} scripts\\tts_unified.py --provider google --script "${{finalScript}}" --output "${{outputPath}}" --voice ${{voice}} --rate ${{speed}} ${{flags}}`;
                }} else {{
                    ttsCommand = `& ${{venvPython}} scripts\\tts_unified.py --provider openai --script "${{finalScript}}" --output "${{outputPath}}" --voice ${{voice}} --speed ${{speed}} ${{flags}}`;
                }}
                
                // Build combined command once (template literal for clarity)
                const combinedCmd = prepCommand ? `${{prepCommand}}\n${{ttsCommand}}` : ttsCommand;
                
                // Step 2: ดาวน์โหลด batch file (20%)
                progressFill.style.width = '20%';
                progressFill.textContent = '20%';
                progressStatus.innerHTML = 'กำลังเตรียมคำสั่ง...<br><small>Provider: ' + provider + ', Voice: ' + voice + '</small>';
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Step 3: แสดงคำสั่งและเปิด batch file (30%)
                progressFill.style.width = '30%';
                progressFill.textContent = '30%';
                
                const batchPath = String.raw`{str(abs_audio / "run_tts.bat").replace(chr(92), chr(92)*2)}`;
                // Performance logging instrumentation
                const perfLog = String.raw`{str(abs_audio / "performance_log.txt").replace(chr(92), chr(92)*2)}`;
                let batchLines = [];
                batchLines.push('@echo off');
                batchLines.push(`cd /d "{Path.cwd()}"`);
                batchLines.push('echo ===== TTS Batch Started %date% %time% =====');
                batchLines.push('echo [BEGIN] %date% %time% > "' + perfLog + '"');
                batchLines.push('set START_TIME=%time%');
                if (prepCommand) {{
                    batchLines.push('echo [SSML_BEGIN] %date% %time% >> "' + perfLog + '"');
                    batchLines.push(prepCommand);
                    batchLines.push('echo [SSML_END] %date% %time% >> "' + perfLog + '"');
                }}
                batchLines.push('echo [TTS_BEGIN] %date% %time% >> "' + perfLog + '"');
                batchLines.push(ttsCommand);
                batchLines.push('echo [TTS_END] %date% %time% >> "' + perfLog + '"');
                batchLines.push('set END_TIME=%time%');
                batchLines.push('echo SSML_USED=' + (prepCommand ? 'true' : 'false') + ' LEVEL=' + (prepCommand ? document.getElementById('ttsSSMLLevel').value : 'none') + ' >> "' + perfLog + '"');
                batchLines.push('echo START_TIME=%START_TIME% END_TIME=%END_TIME% >> "' + perfLog + '"');
                batchLines.push('if %errorlevel% equ 0 (');
                batchLines.push('    echo TTS_SUCCESS');
                batchLines.push('    echo [SUCCESS] %date% %time% >> "' + perfLog + '"');
                batchLines.push(') else (');
                batchLines.push('    echo TTS_FAILED');
                batchLines.push('    echo [FAIL] %date% %time% >> "' + perfLog + '"');
                batchLines.push(')');
                batchLines.push('echo ===== TTS Batch Finished %date% %time% =====');
                batchLines.push('pause');
                const batchContent = batchLines.join('\n');
                
                progressStatus.innerHTML = `
                    <strong>📋 คำสั่งที่จะรัน:</strong><br>
                    <code id="ttsCommandCode" style="display: block; background: #2d2d2d; color: #f8f8f2; padding: 10px; margin: 10px 0; border-radius: 5px; font-size: 11px; overflow-x: auto; user-select: all;">${{combinedCmd}}</code>
                    <button id="copyBtn" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin-top: 5px;">
                        📋 คัดลอกคำสั่ง
                    </button>
                    <button id="downloadBtn" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin-top: 5px; margin-left: 5px;">
                        🚀 ดาวน์โหลด Batch File
                    </button>
                `;
                
                // Add event listeners (safer than inline onclick)
                document.getElementById('copyBtn').addEventListener('click', function() {{
                    copyCommand(combinedCmd);
                }});
                
                document.getElementById('downloadBtn').addEventListener('click', function() {{
                    openBatchFile(batchContent);
                }});
                
                // Add Open Audio Folder button dynamically (ensures path correctness)
                const audioBtnContainer = document.getElementById('downloadLink');
                if (audioBtnContainer && !document.getElementById('openAudioBtn')) {{
                    const btn = document.createElement('a');
                    btn.id = 'openAudioBtn';
                    btn.href = 'file:///{abs_audio}'.replace(/\\/g,'/');
                    btn.className = 'btn btn-success';
                    btn.textContent = '📁 เปิดโฟลเดอร์เสียง';
                    btn.style.marginLeft = '8px';
                    audioBtnContainer.appendChild(btn);
                }}
                
                // Step 4: รอผู้ใช้รัน (50%)
                progressFill.style.width = '50%';
                progressFill.textContent = '50%';
                
                // Show folder button
                downloadLink.classList.add('active');
                
            }} catch (error) {{
                console.error('TTS Error:', error);
                progressFill.style.width = '0%';
                progressFill.textContent = 'Error';
                progressFill.style.background = '#dc3545';
                progressStatus.innerHTML = `❌ เกิดข้อผิดพลาด: ${{error.message}}<br>
                    <small>กรุณาตรวจสอบ:</small><br>
                    <small>1. ตั้งค่า API Keys ใน .env</small><br>
                    <small>2. เชื่อมต่ออินเทอร์เน็ต</small><br>
                    <small>3. ติดตั้ง libraries: pip install openai google-cloud-texttospeech</small>`;
                progressStatus.style.color = '#dc3545';
            }} finally {{
                btn.disabled = false;
            }}
        }}
        
        function copyCommand(cmd) {{
            navigator.clipboard.writeText(cmd).then(() => {{
                alert('✅ คัดลอกคำสั่งแล้ว! วางใน PowerShell/CMD แล้วกด Enter');
            }}).catch(err => {{
                console.error('Copy failed:', err);
                alert('❌ ไม่สามารถคัดลอกอัตโนมัติได้ กรุณาคัดลอกเอง');
            }});
        }}
        
        function openBatchFile(batchContent) {{
            // ดาวน์โหลด batch file
            const blob = new Blob([batchContent], {{ type: 'text/plain' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'generate_tts.bat';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            alert('✅ ดาวน์โหลด generate_tts.bat แล้ว!\\n\\nดับเบิลคลิกไฟล์เพื่อสร้างเสียง AI');
        }}
        
        // Initialize voice options on page load
        document.addEventListener('DOMContentLoaded', function() {{
            updateVoiceOptions();
            toggleSSMLLevel();
        }});
        function toggleSSMLLevel() {{
            const cb = document.getElementById('ttsUseSSML');
            const wrap = document.getElementById('ssmlLevelWrapper');
            if (!cb || !wrap) return;
            wrap.style.display = cb.checked ? 'block' : 'none';
        }}
    </script>
</body>
</html>
"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate production HTML report")
    parser.add_argument('--run-id', type=str, required=True,
                       help='Run ID (e.g., production_complete_001)')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory (default: output/<run-id>/)')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path.cwd()
    output_dir = args.output_dir or (base_dir / 'output' / args.run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get topic title for filename
    topics_ranked_file = output_dir / 'topics_ranked.json'
    topic_title = None
    if topics_ranked_file.exists():
        topics_data = load_json_safe(topics_ranked_file)
        if topics_data and 'topic_override' in topics_data:
            topic_title = topics_data['topic_override']
        elif topics_data and 'ranked' in topics_data and len(topics_data['ranked']) > 0:
            topic_title = topics_data['ranked'][0]['title']
    
    # Create safe filename from topic title
    if topic_title:
        # Remove special characters and limit length
        safe_title = "".join(c for c in topic_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # Limit length
        report_file = output_dir / f'PRODUCTION_GUIDE_{safe_title}.html'
    else:
        report_file = output_dir / f'PRODUCTION_GUIDE_{args.run_id}.html'
    
    # Also create a symlink/copy with standard name for easy access
    standard_report = output_dir / 'PRODUCTION_GUIDE.html'
    
    print("📊 กำลังสร้าง Production Report...")
    print(f"📂 Run ID: {args.run_id}")
    if topic_title:
        print(f"📌 Topic: {topic_title}")
    print(f"📂 Output: {report_file}\n")
    
    # Generate HTML
    html_content = generate_html_report(args.run_id, base_dir)
    
    # Save to file with run_id in name
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Create standard name (latest report)
    with open(standard_report, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ สร้าง HTML Report เรียบร้อย!")
    print(f"   📄 {report_file}")
    print(f"   📄 {standard_report} (latest)")
    print(f"\n💡 เปิดไฟล์นี้ใน browser เพื่อดูคู่มือ Production ทั้งหมด")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
