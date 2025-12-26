#!/usr/bin/env python3
"""
AI Thumbnail Generator
Generate YouTube thumbnails using OpenAI DALL-E + Pillow for text overlay

Requires:
- OpenAI API key in .env or production_config.json
- Pillow (PIL) for image manipulation
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv


class ThumbnailGeneratorAI:
    """Generate thumbnails with AI + text overlay"""
    
    def __init__(self, production_dir: Path):
        self.production_dir = Path(production_dir)
        
        # Load config
        load_dotenv()
        self.api_key = self._get_api_key()
        
        # Load production data
        self.metadata = self._load_json("metadata.json")
        self.thumbnail_concepts = self._load_json("thumbnail_concepts.json")
        
        # Font path (adjust as needed)
        self.font_path = self._find_thai_font()
        
    def _get_api_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        # Try from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return api_key
        
        # Try from production_config.json
        config_file = Path("production_config.json")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('openai', {}).get('api_key')
        
        return None
    
    def _load_json(self, filename: str) -> dict:
        """Load JSON file"""
        filepath = self.production_dir / filename
        if not filepath.exists():
            print(f"⚠️  {filename} not found")
            return {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _find_thai_font(self) -> str:
        """Find Thai font (Sarabun, Prompt, Noto Sans Thai)"""
        # Common Thai font locations
        font_paths = [
            "C:/Windows/Fonts/Sarabun-Bold.ttf",
            "C:/Windows/Fonts/Sarabun.ttf",
            "C:/Windows/Fonts/THSarabunNew-Bold.ttf",
            "C:/Windows/Fonts/THSarabunNew.ttf",
            "C:/Windows/Fonts/NotoSansThai-Bold.ttf",
            "fonts/Sarabun-Bold.ttf",  # Local fonts folder
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        
        # Fallback to Arial (not ideal for Thai)
        return "C:/Windows/Fonts/Arial.ttf"
    
    def generate_base_image(self, concept: Dict) -> Optional[str]:
        """Generate base image using DALL-E"""
        if not self.api_key:
            print("⚠️  No OpenAI API key found - using placeholder image")
            return None
        
        try:
            # Build prompt from concept
            prompt = self._build_dalle_prompt(concept)
            
            print(f"🎨 Generating base image with DALL-E...")
            print(f"📝 Prompt: {prompt[:100]}...")
            
            # Call DALL-E API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "size": "1792x1024",  # Landscape for YouTube
                "quality": "standard",
                "n": 1
            }
            
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']
                
                # Download image
                image_response = requests.get(image_url, timeout=30)
                temp_file = self.production_dir / "thumbnail_base.png"
                
                with open(temp_file, 'wb') as f:
                    f.write(image_response.content)
                
                print(f"✅ Base image generated: {temp_file}")
                return str(temp_file)
            else:
                print(f"❌ DALL-E API error: {response.status_code}")
                print(response.text)
                return None
            
        except Exception as e:
            print(f"❌ Error generating base image: {e}")
            return None
    
    def _build_dalle_prompt(self, concept: Dict) -> str:
        """Build DALL-E prompt from thumbnail concept"""
        title = self.metadata.get('title', 'Dhamma Video')
        
        # Base prompt
        prompt = f"Create a YouTube thumbnail for a Thai Buddhist Dhamma channel. "
        prompt += f"Topic: {title}. "
        
        # Add concept details
        if 'visual_elements' in concept:
            prompt += f"Visual style: {', '.join(concept['visual_elements'])}. "
        
        if 'color_scheme' in concept:
            colors = concept['color_scheme']
            prompt += f"Color palette: {colors.get('primary', 'warm')}, {colors.get('secondary', 'calm')}. "
        
        # Style guidelines
        prompt += "Style: Clean, modern, professional, minimalist. "
        prompt += "Mood: Peaceful, serene, inspiring. "
        prompt += "No text in the image (text will be added separately). "
        prompt += "16:9 aspect ratio, suitable for YouTube thumbnail."
        
        return prompt
    
    def create_placeholder_image(self) -> str:
        """Create simple gradient placeholder if no API"""
        # Create 1280x720 image
        width, height = 1280, 720
        img = Image.new('RGB', (width, height))
        pixels = img.load()
        
        # Gradient from warm pink to orange
        for y in range(height):
            for x in range(width):
                r = int(255 * (1 - y/height) + 255 * (y/height))
                g = int(182 * (1 - y/height) + 212 * (y/height))
                b = int(193 * (1 - y/height) + 163 * (y/height))
                pixels[x, y] = (r, g, b)
        
        # Save
        temp_file = self.production_dir / "thumbnail_base.png"
        img.save(temp_file)
        
        print(f"✅ Created placeholder image: {temp_file}")
        return str(temp_file)
    
    def add_text_overlay(self, base_image: str, concept: Dict, output_path: Path) -> bool:
        """Add text overlay to base image"""
        try:
            # Open image
            img = Image.open(base_image)
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            
            # Create drawing context
            draw = ImageDraw.Draw(img)
            
            # Get title
            title = self.metadata.get('title', 'Dhamma Video')
            
            # Split title if too long
            if len(title) > 30:
                # Find good breaking point
                words = title.split()
                mid = len(words) // 2
                line1 = ' '.join(words[:mid])
                line2 = ' '.join(words[mid:])
            else:
                line1 = title
                line2 = None
            
            # Load fonts
            try:
                font_large = ImageFont.truetype(self.font_path, 100)
                font_small = ImageFont.truetype(self.font_path, 60)
                font_badge = ImageFont.truetype(self.font_path, 40)
            except:
                # Fallback
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_badge = ImageFont.load_default()
            
            # Add shadow for better readability
            shadow_offset = 4
            
            # Draw line 1 (main title)
            x1, y1 = 100, 250
            # Shadow
            draw.text((x1+shadow_offset, y1+shadow_offset), line1, fill=(0,0,0,180), font=font_large)
            # Text
            draw.text((x1, y1), line1, fill=(255,255,255), font=font_large)
            
            # Draw line 2 (if exists)
            if line2:
                y2 = y1 + 120
                draw.text((x1+shadow_offset, y2+shadow_offset), line2, fill=(0,0,0,180), font=font_large)
                draw.text((x1, y2), line2, fill=(255,255,255), font=font_large)
            
            # Add badge (optional)
            if concept.get('badge_text'):
                badge_text = concept['badge_text']
                badge_x, badge_y = 100, 550
                
                # Badge background
                badge_bbox = draw.textbbox((badge_x, badge_y), badge_text, font=font_badge)
                padding = 20
                draw.rounded_rectangle(
                    [badge_bbox[0]-padding, badge_bbox[1]-padding, 
                     badge_bbox[2]+padding, badge_bbox[3]+padding],
                    radius=10,
                    fill=(255, 183, 77, 230)
                )
                
                # Badge text
                draw.text((badge_x, badge_y), badge_text, fill=(255,255,255), font=font_badge)
            
            # Save
            img.save(output_path, quality=95)
            
            print(f"✅ Text overlay added")
            print(f"📄 Thumbnail saved: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding text overlay: {e}")
            return False
    
    def generate(self, output_path: Path, concept_index: int = 0) -> bool:
        """Generate complete thumbnail"""
        print("\n" + "="*70)
        print("🎨 AI Thumbnail Generator")
        print("="*70 + "\n")
        
        # Get concept
        concepts = self.thumbnail_concepts.get('concepts', [])
        if not concepts:
            print("⚠️  No thumbnail concepts found")
            concept = {"name": "Default"}
        else:
            concept = concepts[min(concept_index, len(concepts)-1)]
        
        print(f"🎯 Using concept: {concept.get('name', 'Unknown')}")
        
        # Step 1: Generate or create base image
        print("\n📸 Step 1/2: Generating base image...")
        base_image = self.generate_base_image(concept)
        
        if not base_image:
            base_image = self.create_placeholder_image()
        
        # Step 2: Add text overlay
        print("\n✍️  Step 2/2: Adding text overlay...")
        success = self.add_text_overlay(base_image, concept, output_path)
        
        if success:
            print("\n" + "="*70)
            print("✅ THUMBNAIL GENERATED!")
            print("="*70)
            print(f"\n📄 File: {output_path}")
            print(f"📏 Size: 1280x720 (YouTube standard)")
        
        return success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Thumbnail Generator")
    parser.add_argument("--production-dir", required=True, help="Production directory")
    parser.add_argument("--output", required=True, help="Output thumbnail file (PNG/JPG)")
    parser.add_argument("--concept", type=int, default=0, help="Concept index (0-2)")
    
    args = parser.parse_args()
    
    production_dir = Path(args.production_dir)
    output_path = Path(args.output)
    
    # Validate
    if not production_dir.exists():
        print(f"❌ Production directory not found: {production_dir}")
        return 1
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate
    generator = ThumbnailGeneratorAI(production_dir)
    success = generator.generate(output_path, args.concept)
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
