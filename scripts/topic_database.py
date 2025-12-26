#!/usr/bin/env python3
"""
Topic Database Manager - จัดการ Mock Topics และ Production History

ใช้สำหรับ:
1. เลือกหัวข้อถัดไป (ที่ยังไม่เคยทำ)
2. บันทึก production history
3. สถิติและ reporting
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class TopicDatabase:
    """จัดการ mock topics database"""
    
    def __init__(self, topics_file: Path, history_file: Path):
        self.topics_file = topics_file
        self.history_file = history_file
        self.topics_data = None
        self.history_data = None
    
    def load(self):
        """โหลดข้อมูล"""
        # Load topics
        if self.topics_file.exists():
            with open(self.topics_file, 'r', encoding='utf-8') as f:
                self.topics_data = json.load(f)
        else:
            raise FileNotFoundError(f"Topics file not found: {self.topics_file}")
        
        # Load history
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.history_data = json.load(f)
        else:
            # สร้างใหม่
            self.history_data = {
                "created_at": datetime.now().isoformat(),
                "completed": [],
                "in_progress": [],
                "failed": [],
                "skipped": [],
                "total_produced": 0,
                "total_topics": len(self.topics_data['topics']) if self.topics_data else 0
            }
            self._save_history()
    
    def _save_history(self):
        """บันทึก history"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history_data, f, ensure_ascii=False, indent=2)
    
    def get_completed_topic_ids(self) -> set:
        """ดึง topic IDs ที่ทำเสร็จแล้ว"""
        completed_ids = set()
        for record in self.history_data['completed']:
            completed_ids.add(record['topic_id'])
        return completed_ids
    
    def get_next_topic(self, skip_completed: bool = True, min_priority: int = 3) -> Optional[Dict]:
        """เลือกหัวข้อถัดไป (ตามลำดับ priority) - เฉพาะ priority >= min_priority"""
        
        if not self.topics_data:
            return None
        
        completed_ids = self.get_completed_topic_ids() if skip_completed else set()
        
        # เรียงตาม priority (สูง -> ต่ำ)
        sorted_topics = sorted(
            self.topics_data['topics'],
            key=lambda x: x['priority'],
            reverse=True
        )
        
        # หาหัวข้อแรกที่ยังไม่ทำและมี priority >= min_priority
        for topic in sorted_topics:
            if topic['id'] not in completed_ids and topic.get('priority', 0) >= min_priority:
                return topic
        
        return None  # ทำครบแล้วหรือไม่มีหัวข้อที่ priority >= min_priority
    
    def get_topic_by_id(self, topic_id: str) -> Optional[Dict]:
        """ดึงหัวข้อตาม ID"""
        for topic in self.topics_data['topics']:
            if topic['id'] == topic_id:
                return topic
        return None
    
    def mark_completed(self, topic_id: str, run_id: str, output_dir: str):
        """บันทึกว่าทำเสร็จแล้ว"""
        
        topic = self.get_topic_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic not found: {topic_id}")
        
        record = {
            "topic_id": topic_id,
            "title": topic['title'],
            "category": topic['category'],
            "produced_at": datetime.now().isoformat(),
            "run_id": run_id,
            "output_dir": output_dir,
            "status": "completed"
        }
        
        self.history_data['completed'].append(record)
        self.history_data['total_produced'] = len(self.history_data['completed'])
        self._save_history()
    
    def mark_in_progress(self, topic_id: str, run_id: str):
        """บันทึกว่ากำลังทำ"""
        
        topic = self.get_topic_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic not found: {topic_id}")
        
        record = {
            "topic_id": topic_id,
            "title": topic['title'],
            "started_at": datetime.now().isoformat(),
            "run_id": run_id
        }
        
        self.history_data['in_progress'].append(record)
        self._save_history()
    
    def mark_failed(self, topic_id: str, run_id: str, error_message: str):
        """บันทึกว่าล้มเหลว"""
        
        topic = self.get_topic_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic not found: {topic_id}")
        
        record = {
            "topic_id": topic_id,
            "title": topic['title'],
            "failed_at": datetime.now().isoformat(),
            "run_id": run_id,
            "error": error_message
        }
        
        self.history_data['failed'].append(record)
        
        # ลบออกจาก in_progress
        self.history_data['in_progress'] = [
            r for r in self.history_data['in_progress']
            if r['topic_id'] != topic_id
        ]
        
        self._save_history()
    
    def complete_in_progress(self, topic_id: str, run_id: str, output_dir: str):
        """ย้ายจาก in_progress → completed"""
        
        # ลบออกจาก in_progress
        self.history_data['in_progress'] = [
            r for r in self.history_data['in_progress']
            if r['topic_id'] != topic_id
        ]
        
        # เพิ่มเข้า completed
        self.mark_completed(topic_id, run_id, output_dir)
    
    def get_statistics(self) -> Dict:
        """สถิติโดยรวม"""
        
        total = len(self.topics_data['topics']) if self.topics_data else 0
        completed = len(self.history_data['completed'])
        in_progress = len(self.history_data['in_progress'])
        failed = len(self.history_data['failed'])
        remaining = total - completed
        
        # Progress percentage
        progress_pct = (completed / total * 100) if total > 0 else 0
        
        # By category
        completed_by_category = {}
        for record in self.history_data['completed']:
            cat = record.get('category', 'Unknown')
            completed_by_category[cat] = completed_by_category.get(cat, 0) + 1
        
        return {
            "total_topics": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "remaining": remaining,
            "progress_percentage": round(progress_pct, 1),
            "completed_by_category": completed_by_category
        }
    
    def get_upcoming_topics(self, count: int = 5, min_priority: int = 3) -> List[Dict]:
        """ดึงหัวข้อถัดไปที่จะทำ (top N) - เฉพาะ priority >= min_priority"""
        
        completed_ids = self.get_completed_topic_ids()
        
        sorted_topics = sorted(
            self.topics_data['topics'],
            key=lambda x: x['priority'],
            reverse=True
        )
        
        upcoming = []
        for topic in sorted_topics:
            if topic['id'] not in completed_ids and topic.get('priority', 0) >= min_priority:
                upcoming.append(topic)
                if len(upcoming) >= count:
                    break
        
        return upcoming


def main():
    parser = argparse.ArgumentParser(description="Manage topic database")
    parser.add_argument('--topics', type=Path, default=Path('data/mock_topics.json'),
                       help='Path to topics JSON file')
    parser.add_argument('--history', type=Path, default=Path('data/production_history.json'),
                       help='Path to history JSON file')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # next: ดูหัวข้อถัดไป
    parser_next = subparsers.add_parser('next', help='Get next topic to produce')
    parser_next.add_argument('--title-only', action='store_true', help='Print only the title (for batch scripts)')
    parser_next.add_argument('--id-only', action='store_true', help='Print only the ID (for batch scripts)')
    
    # stats: ดูสถิติ
    parser_stats = subparsers.add_parser('stats', help='Show statistics')
    
    # upcoming: ดูหัวข้อที่จะทำต่อไป
    parser_upcoming = subparsers.add_parser('upcoming', help='Show upcoming topics')
    parser_upcoming.add_argument('--count', type=int, default=5, help='Number of topics')
    
    # mark: บันทึกสถานะ
    parser_mark = subparsers.add_parser('mark', help='Mark topic status')
    parser_mark.add_argument('--topic-id', required=True, help='Topic ID')
    parser_mark.add_argument('--status', choices=['completed', 'in_progress', 'failed'], required=True)
    parser_mark.add_argument('--run-id', help='Run ID')
    parser_mark.add_argument('--output-dir', help='Output directory')
    parser_mark.add_argument('--error', help='Error message (for failed)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Load database
    db = TopicDatabase(args.topics, args.history)
    
    try:
        db.load()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Tip: Run 'python scripts/mock_topic_generator.py' first to generate topics")
        return 1
    
    # Execute command
    if args.command == 'next':
        topic = db.get_next_topic()
        if topic:
            if args.title_only:
                # For batch scripts - print only title
                print(topic['title'])
            elif args.id_only:
                # For batch scripts - print only ID
                print(topic['id'])
            else:
                # Full formatted output
                print(f"📌 Next topic to produce:\n")
                print(f"ID: {topic['id']}")
                print(f"Title: {topic['title']}")
                print(f"Category: {topic['category']}")
                print(f"Priority: {topic['priority']}/10")
                print(f"Difficulty: {topic['difficulty']}")
                print(f"Duration: {topic['estimated_duration']}")
                print(f"Audience: {topic['target_audience']}")
                print(f"\nWhy now: {topic['why_now']}")
        else:
            print("🎉 All topics completed!")
    
    elif args.command == 'stats':
        stats = db.get_statistics()
        print("📊 Production Statistics:\n")
        print(f"Total topics: {stats['total_topics']}")
        print(f"Completed: {stats['completed']}")
        print(f"In progress: {stats['in_progress']}")
        print(f"Failed: {stats['failed']}")
        print(f"Remaining: {stats['remaining']}")
        print(f"Progress: {stats['progress_percentage']}%")
        
        if stats['completed_by_category']:
            print("\nCompleted by category:")
            for cat, count in stats['completed_by_category'].items():
                print(f"  • {cat}: {count}")
    
    elif args.command == 'upcoming':
        topics = db.get_upcoming_topics(args.count)
        print(f"📋 Next {len(topics)} topics to produce:\n")
        for i, topic in enumerate(topics, 1):
            print(f"{i}. {topic['title']}")
            print(f"   ID: {topic['id']} | Priority: {topic['priority']}/10 | {topic['category']}")
            print()
    
    elif args.command == 'mark':
        if args.status == 'completed':
            if not args.run_id or not args.output_dir:
                print("❌ Error: --run-id and --output-dir required for completed status")
                return 1
            db.mark_completed(args.topic_id, args.run_id, args.output_dir)
            print(f"✅ Marked {args.topic_id} as completed")
        
        elif args.status == 'in_progress':
            if not args.run_id:
                print("❌ Error: --run-id required for in_progress status")
                return 1
            db.mark_in_progress(args.topic_id, args.run_id)
            print(f"🔄 Marked {args.topic_id} as in progress")
        
        elif args.status == 'failed':
            if not args.run_id or not args.error:
                print("❌ Error: --run-id and --error required for failed status")
                return 1
            db.mark_failed(args.topic_id, args.run_id, args.error)
            print(f"❌ Marked {args.topic_id} as failed")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
