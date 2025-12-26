#!/usr/bin/env python3
"""
Mock Topic Generator - สร้างหัวข้อวิดีโอธรรมะ 15-20 หัวข้อ

อ่านจาก topic_templates.yaml และ generate หัวข้อที่หลากหลาย
ไม่ต้องใช้ AI API (ฟรี 100%)
"""

import yaml
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def load_templates(template_file: Path) -> dict:
    """โหลด topic templates จาก YAML"""
    with open(template_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_topic_from_template(category: dict, templates_data: dict) -> dict:
    """สร้าง 1 หัวข้อจาก template"""
    
    # สุ่มเลือก template
    template = random.choice(category['templates'])
    
    # สร้าง title จาก template
    title = template
    
    # แทนที่ placeholder ด้วยค่าจริง (ถ้าไม่มีให้ข้ามไป)
    replacements = {
        '{concept}': category.get('concepts', ['ธรรมะ']),
        '{technique}': category.get('techniques', ['ภาวนา']),
        '{audience}': category.get('audiences', ['ทุกคน']),
        '{problem}': category.get('problems', ['ปัญหา']),
        '{duration}': category.get('durations', ['5 นาที']),
        '{trend}': category.get('trends', ['ดิจิทัล']),
        '{era}': category.get('eras', ['ยุคใหม่']),
        '{challenge}': category.get('challenges', ['ความท้าทาย']),
        '{issue}': category.get('issues', ['ประเด็น']),
        '{principle}': category.get('principles', ['หลักธรรม']),
        '{situation}': category.get('situations', ['สถานการณ์']),
        '{time}': category.get('times', ['ทุกวัน']),
        '{benefit}': category.get('benefits', ['ประโยชน์']),
        '{action}': category.get('actions', ['ปฏิบัติ']),
        '{hook}': category.get('hooks', ['ควรรู้']),
        '{topic}': category.get('topics', ['ธรรมะ']),
        '{number}': category.get('numbers', ['3']),
    }
    
    # Replace all placeholders
    for placeholder, options in replacements.items():
        if placeholder in title:
            title = title.replace(placeholder, random.choice(options))
    
    # สร้างข้อมูลเพิ่มเติม
    difficulty = random.choice(templates_data['difficulty_levels'])
    target_audience = random.choice(templates_data['target_audiences'])
    video_duration = random.choice(templates_data['video_durations'])
    season = random.choice(templates_data['seasons'])
    
    # Priority (ตาม category weight + random) - ช่วง 3-10
    base_priority = int(category.get('weight', 0.5) * 10)
    priority = max(3, min(10, base_priority + random.randint(-2, 2)))
    
    # Keywords (สุ่มจาก pool)
    all_keywords = []
    for kw_group in templates_data['keywords'].values():
        all_keywords.extend(kw_group)
    keywords = random.sample(all_keywords, min(5, len(all_keywords)))
    
    # Why now (สุ่มเหตุผล)
    why_now_options = [
        f"{category['name']} content กำลังเป็นที่นิยม",
        "คนค้นหาหัวข้อนี้เพิ่มขึ้น 30%",
        "เทรนด์ mindfulness ในไทยเติบโต",
        "ตอบโจทย์ lifestyle คนยุคใหม่",
        "SEO opportunity สูง - แข่งขันน้อย",
        "Evergreen content - ใช้ได้นาน",
    ]
    why_now = random.choice(why_now_options)
    
    # Risk assessment
    risk_levels = ["ต่ำ", "ต่ำ", "ต่ำ", "กลาง", "กลาง"]
    risk = random.choice(risk_levels)
    
    return {
        "title": title,
        "category": category['name'],
        "difficulty": difficulty,
        "target_audience": target_audience,
        "estimated_duration": video_duration,
        "keywords": keywords,
        "season": season,
        "priority": priority,
        "why_now": why_now,
        "risk": risk,
        "sources": ["template-generated"],
    }


def generate_topics(templates_data: dict, count: int = 20) -> List[dict]:
    """สร้างหัวข้อทั้งหมด"""
    
    categories = templates_data['categories']
    topics = []
    topics_set = set()  # เพื่อเช็คไม่ให้ซ้ำ
    
    # คำนวณจำนวนหัวข้อต่อ category ตาม weight
    category_counts = {}
    for cat in categories:
        weight = cat.get('weight', 1.0 / len(categories))
        category_counts[cat['name']] = int(count * weight)
    
    # ปรับให้ได้จำนวนพอดี
    total = sum(category_counts.values())
    if total < count:
        # เพิ่มให้ category ที่ weight สูง
        sorted_cats = sorted(categories, key=lambda x: x.get('weight', 0), reverse=True)
        for i in range(count - total):
            cat_name = sorted_cats[i % len(sorted_cats)]['name']
            category_counts[cat_name] += 1
    
    # Generate topics
    for category in categories:
        cat_count = category_counts[category['name']]
        attempts = 0
        max_attempts = cat_count * 10
        
        while len([t for t in topics if t['category'] == category['name']]) < cat_count and attempts < max_attempts:
            topic = generate_topic_from_template(category, templates_data)
            
            # เช็คไม่ให้ title ซ้ำ
            if topic['title'] not in topics_set:
                topics_set.add(topic['title'])
                topics.append(topic)
            
            attempts += 1
    
    # เรียงตาม priority
    topics.sort(key=lambda x: x['priority'], reverse=True)
    
    # เพิ่ม ID
    for i, topic in enumerate(topics, 1):
        topic['id'] = f"topic_{i:03d}"
    
    return topics


def save_topics(topics: List[dict], output_file: Path):
    """บันทึกหัวข้อลง JSON"""
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_topics": len(topics),
        "version": "1.0",
        "topics": topics,
        "statistics": {
            "by_category": {},
            "by_difficulty": {},
            "by_season": {},
            "priority_distribution": {
                "high (8-10)": 0,
                "medium (5-7)": 0,
                "low (1-4)": 0
            }
        }
    }
    
    # คำนวณสถิติ
    for topic in topics:
        # By category
        cat = topic['category']
        data['statistics']['by_category'][cat] = data['statistics']['by_category'].get(cat, 0) + 1
        
        # By difficulty
        diff = topic['difficulty']
        data['statistics']['by_difficulty'][diff] = data['statistics']['by_difficulty'].get(diff, 0) + 1
        
        # By season
        season = topic['season']
        data['statistics']['by_season'][season] = data['statistics']['by_season'].get(season, 0) + 1
        
        # By priority
        priority = topic['priority']
        if priority >= 8:
            data['statistics']['priority_distribution']['high (8-10)'] += 1
        elif priority >= 5:
            data['statistics']['priority_distribution']['medium (5-7)'] += 1
        else:
            data['statistics']['priority_distribution']['low (1-4)'] += 1
    
    # บันทึก
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Generate mock topics for Dhamma videos")
    parser.add_argument('--templates', type=Path, default=Path('data/topic_templates.yaml'),
                       help='Path to topic templates YAML file')
    parser.add_argument('--output', type=Path, default=Path('data/mock_topics.json'),
                       help='Output JSON file')
    parser.add_argument('--count', type=int, default=20,
                       help='Number of topics to generate (default: 20)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # Set random seed
    if args.seed:
        random.seed(args.seed)
    
    print("🎯 Mock Topic Generator")
    print(f"📂 Templates: {args.templates}")
    print(f"📂 Output: {args.output}")
    print(f"🔢 Target count: {args.count}\n")
    
    # โหลด templates
    if not args.templates.exists():
        print(f"❌ Error: Template file not found: {args.templates}")
        return 1
    
    print("📖 Loading templates...")
    templates_data = load_templates(args.templates)
    
    # Generate topics
    print(f"🔧 Generating {args.count} topics...\n")
    topics = generate_topics(templates_data, args.count)
    
    # แสดงผลตัวอย่าง
    print(f"✅ Generated {len(topics)} topics:\n")
    print("=" * 80)
    for i, topic in enumerate(topics[:5], 1):
        print(f"{i}. {topic['title']}")
        print(f"   Category: {topic['category']} | Priority: {topic['priority']}/10 | Difficulty: {topic['difficulty']}")
        print(f"   Duration: {topic['estimated_duration']} | Audience: {topic['target_audience']}")
        print()
    
    if len(topics) > 5:
        print(f"... และอีก {len(topics) - 5} หัวข้อ")
    print("=" * 80)
    
    # บันทึก
    print(f"\n💾 Saving to {args.output}...")
    save_topics(topics, args.output)
    
    # สถิติ
    print("\n📊 Statistics:")
    
    # Load saved data to show stats
    with open(args.output, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = data['statistics']
    
    print("\n  By Category:")
    for cat, count in stats['by_category'].items():
        percentage = (count / len(topics)) * 100
        print(f"    • {cat}: {count} ({percentage:.1f}%)")
    
    print("\n  By Difficulty:")
    for diff, count in stats['by_difficulty'].items():
        print(f"    • {diff}: {count}")
    
    print("\n  By Priority:")
    for level, count in stats['priority_distribution'].items():
        print(f"    • {level}: {count}")
    
    print(f"\n✅ Mock topics generated successfully!")
    print(f"📄 File: {args.output}")
    print(f"📊 Total: {len(topics)} topics\n")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
