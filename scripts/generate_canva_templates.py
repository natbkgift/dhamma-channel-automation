#!/usr/bin/env python3
"""
Canva Thumbnail Template Generator - Path A

สร้างไฟล์ JSON specs และ markdown guide สำหรับสร้าง thumbnail ใน Canva
"""

import json
import argparse
from pathlib import Path


def load_thumbnail_concepts(concepts_path: Path) -> dict:
    """โหลด thumbnail concepts"""
    with open(concepts_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_canva_specs(concepts: dict, output_dir: Path):
    """สร้าง JSON specs สำหรับแต่ละ concept"""
    
    concepts_list = concepts.get('concepts', [])
    dimensions = concepts.get('dimensions', '1280x720 px (16:9)')
    
    for concept in concepts_list:
        concept_id = concept.get('concept_id', 1)
        title = concept.get('title', 'Concept')
        
        # สร้าง detailed specs
        spec = {
            'concept_id': concept_id,
            'title': title,
            'canvas_size': dimensions,
            'file_format': concepts.get('file_format', 'JPG or PNG'),
            'file_size_limit': concepts.get('file_size_limit', '2MB'),
            
            # Text layers
            'text_layers': [],
            
            # Visual elements
            'visual_elements': concept.get('visual_elements', []),
            
            # Colors
            'color_scheme': concept.get('color_scheme', 'default'),
            
            # Composition
            'composition': concept.get('composition', 'center-aligned'),
            
            # Canva instructions
            'canva_steps': []
        }
        
        # แยก text overlays
        text_overlay = concept.get('text_overlay', {})
        if text_overlay:
            if 'main' in text_overlay:
                spec['text_layers'].append({
                    'type': 'main',
                    'text': text_overlay['main'],
                    'font': text_overlay.get('font', 'Kanit Bold'),
                    'font_size': text_overlay.get('font_size', {}).get('main', '72pt'),
                    'color': text_overlay.get('color', 'White'),
                    'effects': text_overlay.get('stroke', 'None')
                })
            
            if 'sub' in text_overlay:
                spec['text_layers'].append({
                    'type': 'sub',
                    'text': text_overlay['sub'],
                    'font': text_overlay.get('font', 'Kanit Bold'),
                    'font_size': text_overlay.get('font_size', {}).get('sub', '36pt'),
                    'color': text_overlay.get('color', 'White')
                })
            
            if 'badge' in text_overlay:
                spec['text_layers'].append({
                    'type': 'badge',
                    'text': text_overlay['badge'],
                    'font': text_overlay.get('font', 'Prompt Bold'),
                    'font_size': '24pt'
                })
        
        # Canva step-by-step
        spec['canva_steps'] = [
            f"1. Go to Canva.com and create custom size: {dimensions}",
            f"2. Background: {concept.get('color_scheme', 'Choose warm colors')}",
            "3. Add background image/gradient according to visual_elements",
            f"4. Add main text: \"{text_overlay.get('main', 'Your Text')}\"",
            f"   - Font: {text_overlay.get('font', 'Kanit Bold')}",
            f"   - Size: {text_overlay.get('font_size', {}).get('main', '72pt')}",
            f"   - Color: {text_overlay.get('color', 'White')}",
        ]
        
        if 'sub' in text_overlay:
            spec['canva_steps'].append(
                f"5. Add subtitle: \"{text_overlay.get('sub', '')}\" (smaller font)"
            )
        
        spec['canva_steps'].extend([
            "6. Add visual elements (person, icons, etc.)",
            "7. Adjust composition and spacing",
            "8. Download as JPG (Quality: 100, Size: <2MB)"
        ])
        
        # Save individual spec
        spec_file = output_dir / f'canva_concept_{concept_id}.json'
        with open(spec_file, 'w', encoding='utf-8') as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created: {spec_file.name}")


def generate_markdown_guide(concepts: dict, output_dir: Path):
    """สร้าง markdown guide สำหรับ Canva"""
    
    concepts_list = concepts.get('concepts', [])
    video_title = concepts.get('video_title', 'Video Title')
    
    guide_file = output_dir / 'CANVA_GUIDE.md'
    
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write("# 🎨 Canva Thumbnail Creation Guide\n\n")
        f.write(f"**Video Title:** {video_title}\n\n")
        f.write("---\n\n")
        
        f.write("## 🎯 Quick Start\n\n")
        f.write("1. Go to https://www.canva.com/\n")
        f.write("2. Sign up/login (free account OK)\n")
        f.write("3. Choose one of the 3 concepts below\n")
        f.write("4. Follow step-by-step instructions\n")
        f.write("5. Download as JPG (<2MB)\n\n")
        
        f.write("---\n\n")
        
        # แต่ละ concept
        for concept in concepts_list:
            concept_id = concept.get('concept_id', 1)
            title = concept.get('title', 'Concept')
            emotion = concept.get('emotion', '')
            text_overlay = concept.get('text_overlay', {})
            visual_elements = concept.get('visual_elements', [])
            color_scheme = concept.get('color_scheme', '')
            composition = concept.get('composition', '')
            
            f.write(f"## Concept {concept_id}: {title}\n\n")
            f.write(f"**Emotion:** {emotion}  \n")
            f.write(f"**Color Scheme:** {color_scheme}  \n")
            f.write(f"**Composition:** {composition}\n\n")
            
            f.write("### 📝 Text Content\n\n")
            if 'main' in text_overlay:
                f.write(f"**Main Text:** {text_overlay['main']}  \n")
                f.write(f"- Font: {text_overlay.get('font', 'Kanit Bold')}  \n")
                f.write(f"- Size: {text_overlay.get('font_size', {}).get('main', '72pt')}  \n")
                f.write(f"- Color: {text_overlay.get('color', 'White')}\n\n")
            
            if 'sub' in text_overlay:
                f.write(f"**Subtitle:** {text_overlay['sub']}  \n")
                f.write(f"- Size: {text_overlay.get('font_size', {}).get('sub', '36pt')}\n\n")
            
            f.write("### 🎨 Visual Elements\n\n")
            for elem in visual_elements:
                f.write(f"- {elem}\n")
            f.write("\n")
            
            f.write("### 🛠️ Step-by-Step in Canva\n\n")
            
            steps = [
                "**Step 1: Create Canvas**",
                "- Click 'Create a design'",
                "- Choose 'Custom size'",
                f"- Enter: 1280 x 720 px",
                "",
                "**Step 2: Background**",
                f"- Go to 'Elements' → Search '{color_scheme.split('(')[0].strip()}'",
                "- Select gradient or solid color background",
                "- Apply to canvas",
                "",
                "**Step 3: Add Images**"
            ]
            
            if "person" in str(visual_elements).lower() or "face" in str(visual_elements).lower():
                steps.extend([
                    "- Go to 'Elements' → Search 'meditation person' or 'peaceful face'",
                    "- Select free photo (marked with free icon)",
                    "- Place according to composition"
                ])
            
            steps.extend([
                "",
                "**Step 4: Add Main Text**",
                f"- Click 'Text' → 'Add a heading'",
                f"- Type: \"{text_overlay.get('main', 'Your Text')}\"",
                f"- Font: {text_overlay.get('font', 'Kanit Bold')} (search in font dropdown)",
                f"- Size: {text_overlay.get('font_size', {}).get('main', '72')} (adjust as needed)",
                f"- Color: {text_overlay.get('color', 'White')}",
                "- Effects: Add shadow (under 'Effects' button)"
            ])
            
            if 'sub' in text_overlay:
                steps.extend([
                    "",
                    "**Step 5: Add Subtitle**",
                    f"- Add another text: \"{text_overlay.get('sub', '')}\"",
                    f"- Smaller font: {text_overlay.get('font_size', {}).get('sub', '36')}",
                    "- Place below main text"
                ])
            
            steps.extend([
                "",
                "**Step 6: Final Touches**",
                "- Adjust positioning and spacing",
                "- Make sure text is readable on mobile",
                "- Check contrast (text vs background)",
                "",
                "**Step 7: Download**",
                "- Click 'Share' → 'Download'",
                "- Format: JPG",
                "- Quality: Maximum",
                "- Check file size (<2MB)",
                ""
            ])
            
            for step in steps:
                f.write(f"{step}\n")
            
            f.write("\n---\n\n")
        
        # Tips
        f.write("## 💡 Pro Tips\n\n")
        
        tips = concepts.get('best_practices', [])
        if tips:
            for tip in tips:
                f.write(f"- ✅ {tip}\n")
            f.write("\n")
        
        avoid = concepts.get('avoid', [])
        if avoid:
            f.write("### ❌ Avoid\n\n")
            for item in avoid:
                f.write(f"- {item}\n")
            f.write("\n")
        
        f.write("---\n\n")
        f.write("## 🔍 A/B Testing\n\n")
        f.write("**Recommendation:** Create 2-3 different thumbnails and test which gets higher CTR\n\n")
        f.write("1. Upload all thumbnails to YouTube Studio\n")
        f.write("2. Use different thumbnails for first 7-14 days\n")
        f.write("3. Check Analytics → Reach → CTR\n")
        f.write("4. Keep the one with highest CTR\n")
    
    print(f"✅ Created: {guide_file.name}")


def generate_template_links(output_dir: Path):
    """สร้างไฟล์ลิงก์ไปยัง Canva templates (ถ้ามี)"""
    
    links_file = output_dir / 'canva_templates.md'
    
    with open(links_file, 'w', encoding='utf-8') as f:
        f.write("# 📎 Canva Template Links\n\n")
        f.write("## Free YouTube Thumbnail Templates\n\n")
        
        f.write("คุณสามารถใช้ templates ฟรีเหล่านี้เป็น starting point:\n\n")
        
        templates = [
            ("Canva YouTube Thumbnail", "https://www.canva.com/templates/?query=youtube+thumbnail"),
            ("Meditation Thumbnail", "https://www.canva.com/templates/?query=meditation+thumbnail"),
            ("Minimal Thumbnail", "https://www.canva.com/templates/?query=minimal+youtube+thumbnail"),
        ]
        
        for name, url in templates:
            f.write(f"- [{name}]({url})\n")
        
        f.write("\n---\n\n")
        f.write("## How to Use Templates\n\n")
        f.write("1. Click any link above\n")
        f.write("2. Find a template you like (look for FREE ones)\n")
        f.write("3. Click 'Customize this template'\n")
        f.write("4. Edit text and images according to CANVA_GUIDE.md\n")
        f.write("5. Download as JPG\n")
    
    print(f"✅ Created: {links_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate Canva thumbnail templates and guides")
    parser.add_argument('--input-dir', type=Path, required=True,
                       help='Input directory with thumbnail_concepts.json')
    parser.add_argument('--output-dir', type=Path, default=None,
                       help='Output directory for templates (default: templates/canva/)')
    
    args = parser.parse_args()
    
    # Paths
    input_dir = args.input_dir
    output_dir = args.output_dir or (Path('templates') / 'canva')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    concepts_file = input_dir / 'thumbnail_concepts.json'
    
    # ตรวจสอบไฟล์
    if not concepts_file.exists():
        print(f"❌ Error: {concepts_file} not found!")
        return
    
    print("🎨 Canva Thumbnail Template Generator")
    print(f"📂 Input: {input_dir}")
    print(f"📂 Output: {output_dir}\n")
    
    # โหลด concepts
    concepts = load_thumbnail_concepts(concepts_file)
    concepts_list = concepts.get('concepts', [])
    
    if not concepts_list:
        print("❌ No concepts found!")
        return
    
    print(f"✅ Found {len(concepts_list)} thumbnail concepts\n")
    
    # สร้างไฟล์ต่างๆ
    print("📄 Generating files...\n")
    
    # 1. Individual concept specs
    generate_canva_specs(concepts, output_dir)
    
    # 2. Markdown guide
    generate_markdown_guide(concepts, output_dir)
    
    # 3. Template links
    generate_template_links(output_dir)
    
    print("\n✅ All Canva templates generated!")
    print("\n🎯 NEXT STEPS:")
    print("   1. Open https://www.canva.com/")
    print("   2. Read CANVA_GUIDE.md")
    print("   3. Choose one concept (1, 2, or 3)")
    print("   4. Follow step-by-step instructions")
    print("   5. Download thumbnail as JPG (<2MB)")
    print("\n💡 TIP: Create all 3 concepts for A/B testing!")


if __name__ == '__main__':
    main()
