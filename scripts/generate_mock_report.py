#!/usr/bin/env python3
"""
Mock Topics Report Generator - สร้าง HTML report สำหรับ Mock Topics Database

แสดง:
- ภาพรวมหัวข้อทั้งหมด
- สถิติ progress
- Upcoming topics
- ตารางหัวข้อ (sortable, filterable)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def load_data(topics_file: Path, history_file: Path) -> tuple:
    """โหลดข้อมูล"""
    
    # Load topics
    if not topics_file.exists():
        raise FileNotFoundError(f"Topics file not found: {topics_file}")
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics_data = json.load(f)
    
    # Load history
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    else:
        history_data = {
            "completed": [],
            "in_progress": [],
            "failed": [],
            "total_produced": 0
        }
    
    return topics_data, history_data


def calculate_statistics(topics_data: dict, history_data: dict) -> Dict:
    """คำนวณสถิติ"""
    
    total = len(topics_data['topics'])
    completed = len(history_data['completed'])
    in_progress = len(history_data['in_progress'])
    failed = len(history_data['failed'])
    remaining = total - completed
    progress_pct = (completed / total * 100) if total > 0 else 0
    
    # Completed IDs
    completed_ids = {r['topic_id'] for r in history_data['completed']}
    
    # Upcoming topics
    upcoming = []
    for topic in sorted(topics_data['topics'], key=lambda x: x['priority'], reverse=True):
        if topic['id'] not in completed_ids:
            upcoming.append(topic)
            if len(upcoming) >= 5:
                break
    
    # By category (from topics)
    by_category = topics_data['statistics'].get('by_category', {})
    
    # By difficulty
    by_difficulty = topics_data['statistics'].get('by_difficulty', {})
    
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "remaining": remaining,
        "progress_pct": round(progress_pct, 1),
        "upcoming": upcoming,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "completed_ids": completed_ids
    }


def generate_html(topics_data: dict, history_data: dict, stats: Dict, output_file: Path) -> str:
    """สร้าง HTML"""
    
    topics = topics_data['topics']
    
    # Absolute paths
    abs_topics_file = Path('data/mock_topics.json').resolve()
    abs_history_file = Path('data/production_history.json').resolve()
    
    # Current timestamp
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    footer_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock Topics Database - Dhamma Channel</title>
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
            max-width: 1400px;
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
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.95em;
            opacity: 0.9;
        }}
        
        .progress-bar-container {{
            background: #f0f0f0;
            height: 40px;
            border-radius: 20px;
            overflow: hidden;
            margin: 30px 0;
            position: relative;
        }}
        
        .progress-bar {{
            background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
            height: 100%;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
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
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: bold;
            cursor: pointer;
            user-select: none;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        @media screen and (max-width: 768px) {{
            table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .charts {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media screen and (max-width: 480px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        
        .badge-priority {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }}
        
        .badge-category {{
            background: #667eea;
            color: white;
        }}
        
        .badge-difficulty-easy {{
            background: #43e97b;
            color: white;
        }}
        
        .badge-difficulty-medium {{
            background: #ffa726;
            color: white;
        }}
        
        .badge-difficulty-hard {{
            background: #f5576c;
            color: white;
        }}
        
        .badge-completed {{
            background: #43e97b;
            color: white;
        }}
        
        .badge-pending {{
            background: #ffa726;
            color: white;
        }}
        
        .upcoming-card {{
            background: #f8f9fa;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #667eea;
            border-radius: 8px;
            transition: all 0.3s;
        }}
        
        .upcoming-card:hover {{
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .upcoming-title {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .upcoming-meta {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .filter-bar {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .filter-bar input,
        .filter-bar select {{
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
        }}
        
        .filter-bar input:focus,
        .filter-bar select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .chart-card {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
        }}
        
        .chart-card h3 {{
            color: #667eea;
            margin-bottom: 20px;
        }}
        
        .chart-bar {{
            margin: 10px 0;
        }}
        
        .chart-bar-label {{
            font-size: 0.9em;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
        }}
        
        .chart-bar-fill {{
            height: 30px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            transition: width 0.5s;
            display: flex;
            align-items: center;
            padding: 0 15px;
            color: white;
            font-weight: bold;
            font-size: 0.85em;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Mock Topics Database</h1>
            <div class="subtitle">Dhamma Channel Content Library</div>
            <div style="margin-top: 15px; opacity: 0.8;">
                สร้างเมื่อ: {current_time}
            </div>
        </div>
        
        <div class="content">
            <!-- Statistics Overview -->
            <div class="section">
                <h2>📊 สถิติภาพรวม</h2>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">หัวข้อทั้งหมด</div>
                        <div class="stat-number">{stats['total']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">ทำเสร็จแล้ว</div>
                        <div class="stat-number">{stats['completed']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">กำลังทำ</div>
                        <div class="stat-number">{stats['in_progress']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">เหลืออีก</div>
                        <div class="stat-number">{stats['remaining']}</div>
                    </div>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {stats['progress_pct']}%">
                        {stats['progress_pct']}% Complete
                    </div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="charts">
                <div class="chart-card">
                    <h3>📂 หัวข้อตาม Category</h3>
"""
    
    # Category chart
    if stats['by_category']:
        max_count = max(stats['by_category'].values())
        for cat, count in stats['by_category'].items():
            width_pct = (count / max_count * 100) if max_count > 0 else 0
            html += f"""                    <div class="chart-bar">
                        <div class="chart-bar-label">
                            <span>{cat}</span>
                            <span>{count}</span>
                        </div>
                        <div class="chart-bar-fill" style="width: {width_pct}%">
                            {count}
                        </div>
                    </div>
"""
    
    html += """                </div>
                
                <div class="chart-card">
                    <h3>📊 ระดับความยาก</h3>
"""
    
    # Difficulty chart
    if stats['by_difficulty']:
        max_count = max(stats['by_difficulty'].values())
        for diff, count in stats['by_difficulty'].items():
            width_pct = (count / max_count * 100) if max_count > 0 else 0
            html += f"""                    <div class="chart-bar">
                        <div class="chart-bar-label">
                            <span>{diff}</span>
                            <span>{count}</span>
                        </div>
                        <div class="chart-bar-fill" style="width: {width_pct}%">
                            {count}
                        </div>
                    </div>
"""
    
    html += """                </div>
            </div>
            
            <!-- Upcoming Topics -->
            <div class="section">
                <h2>⏭️ หัวข้อถัดไปที่จะทำ (Top 5)</h2>
"""
    
    if stats['upcoming']:
        for i, topic in enumerate(stats['upcoming'], 1):
            html += f"""                <div class="upcoming-card">
                    <div class="upcoming-title">{i}. {topic['title']}</div>
                    <div class="upcoming-meta">
                        <span class="badge badge-priority">Priority: {topic['priority']}/10</span>
                        <span class="badge badge-category">{topic['category']}</span>
                        <span class="badge badge-difficulty-{'easy' if topic['difficulty'] == 'ง่าย' else 'medium' if topic['difficulty'] == 'กลาง' else 'hard'}">{topic['difficulty']}</span>
                        <span>🎯 {topic['target_audience']}</span>
                        <span>⏱️ {topic['estimated_duration']}</span>
                    </div>
                    <div style="margin-top: 10px; color: #666; font-size: 0.95em;">
                        💡 {topic['why_now']}
                    </div>
                </div>
"""
    else:
        html += """                <p>🎉 ไม่มีหัวข้อที่เหลือ - ทำครบทุกหัวข้อแล้ว!</p>
"""
    
    html += """            </div>
            
            <!-- All Topics Table -->
            <div class="section">
                <h2>📋 หัวข้อทั้งหมด</h2>
                
                <div class="filter-bar">
                    <input type="text" id="searchBox" placeholder="🔍 ค้นหาหัวข้อ..." style="flex: 1; min-width: 200px;">
                    <select id="categoryFilter">
                        <option value="">ทุก Category</option>
"""
    
    # Category filter options
    for cat in sorted(stats['by_category'].keys()):
        html += f'                        <option value="{cat}">{cat}</option>\n'
    
    html += """                    </select>
                    <select id="statusFilter">
                        <option value="">ทุกสถานะ</option>
                        <option value="completed">เสร็จแล้ว</option>
                        <option value="pending">ยังไม่ทำ</option>
                    </select>
                    <select id="difficultyFilter">
                        <option value="">ทุกระดับ</option>
"""
    
    # Difficulty filter options
    for diff in sorted(stats['by_difficulty'].keys()):
        html += f'                        <option value="{diff}">{diff}</option>\n'
    
    html += """                    </select>
                </div>
                
                <table id="topicsTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)">#</th>
                            <th onclick="sortTable(1)">หัวข้อ</th>
                            <th onclick="sortTable(2)">Category</th>
                            <th onclick="sortTable(3)">Priority</th>
                            <th onclick="sortTable(4)">ความยาก</th>
                            <th onclick="sortTable(5)">ระยะเวลา</th>
                            <th onclick="sortTable(6)">สถานะ</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Table rows
    for i, topic in enumerate(topics, 1):
        is_completed = topic['id'] in stats['completed_ids']
        status_badge = '<span class="badge badge-completed">เสร็จแล้ว</span>' if is_completed else '<span class="badge badge-pending">ยังไม่ทำ</span>'
        diff_class = 'easy' if topic['difficulty'] == 'ง่าย' else 'medium' if topic['difficulty'] == 'กลาง' else 'hard'
        
        html += f"""                        <tr data-category="{topic['category']}" data-status="{'completed' if is_completed else 'pending'}" data-difficulty="{topic['difficulty']}">
                            <td>{i}</td>
                            <td>{topic['title']}</td>
                            <td><span class="badge badge-category">{topic['category']}</span></td>
                            <td><span class="badge badge-priority">{topic['priority']}/10</span></td>
                            <td><span class="badge badge-difficulty-{diff_class}">{topic['difficulty']}</span></td>
                            <td>{topic['estimated_duration']}</td>
                            <td>{status_badge}</td>
                        </tr>
"""
    
    # Build Quick Actions links with proper file paths
    topics_file_url = str(abs_topics_file).replace('\\', '/')
    history_file_url = str(abs_history_file).replace('\\', '/')
    
    html += f"""                    </tbody>
                </table>
            </div>
            
            <!-- Quick Actions -->
            <div class="section">
                <h2>🔗 Quick Actions</h2>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <a href="file:///{topics_file_url}" class="btn">📄 เปิด Topics JSON</a>
                    <a href="file:///{history_file_url}" class="btn">📊 เปิด History JSON</a>
                    <button onclick="window.print()" class="btn">🖨️ Print Report</button>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>🎬 Dhamma Channel Automation</strong></p>
            <p>Mock Topics Database • Generated: {footer_time}</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                Total Topics: {stats['total']} | Completed: {stats['completed']} | Remaining: {stats['remaining']}
            </p>
        </div>
    </div>
    
    <script>
        // Search filter
        document.getElementById('searchBox').addEventListener('input', filterTable);
        document.getElementById('categoryFilter').addEventListener('change', filterTable);
        document.getElementById('statusFilter').addEventListener('change', filterTable);
        document.getElementById('difficultyFilter').addEventListener('change', filterTable);
        
        function filterTable() {{
            const search = document.getElementById('searchBox').value.toLowerCase();
            const category = document.getElementById('categoryFilter').value;
            const status = document.getElementById('statusFilter').value;
            const difficulty = document.getElementById('difficultyFilter').value;
            
            const rows = document.querySelectorAll('#topicsTable tbody tr');
            
            rows.forEach(row => {{
                const title = row.cells[1].textContent.toLowerCase();
                const rowCategory = row.dataset.category;
                const rowStatus = row.dataset.status;
                const rowDifficulty = row.dataset.difficulty;
                
                const matchSearch = title.includes(search);
                const matchCategory = !category || rowCategory === category;
                const matchStatus = !status || rowStatus === status;
                const matchDifficulty = !difficulty || rowDifficulty === difficulty;
                
                if (matchSearch && matchCategory && matchStatus && matchDifficulty) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
        
        // Table sorting
        function sortTable(columnIndex) {{
            const table = document.getElementById('topicsTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {{
                const aText = a.cells[columnIndex].textContent;
                const bText = b.cells[columnIndex].textContent;
                
                // Try numeric sort first
                const aNum = parseFloat(aText);
                const bNum = parseFloat(bText);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return aNum - bNum;
                }}
                
                return aText.localeCompare(bText, 'th');
            }});
            
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</body>
</html>
"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report for mock topics")
    parser.add_argument('--topics', type=Path, default=Path('data/mock_topics.json'),
                       help='Path to topics JSON')
    parser.add_argument('--history', type=Path, default=Path('data/production_history.json'),
                       help='Path to production history JSON')
    parser.add_argument('--output', type=Path, default=Path('reports/mock_topics_report.html'),
                       help='Output HTML file')
    
    args = parser.parse_args()
    
    print("📊 Mock Topics Report Generator")
    print(f"📂 Topics: {args.topics}")
    print(f"📂 History: {args.history}")
    print(f"📂 Output: {args.output}\n")
    
    try:
        # Load data
        print("📖 Loading data...")
        topics_data, history_data = load_data(args.topics, args.history)
        
        # Calculate statistics
        print("📊 Calculating statistics...")
        stats = calculate_statistics(topics_data, history_data)
        
        # Generate HTML
        print("🎨 Generating HTML...")
        html = generate_html(topics_data, history_data, stats, args.output)
        
        # Backup existing report
        if args.output.exists():
            print("📦 Backing up existing report...")
            backup_num = 1
            while True:
                backup_path = args.output.parent / f"{args.output.stem}_{backup_num:03d}{args.output.suffix}"
                if not backup_path.exists():
                    args.output.rename(backup_path)
                    print(f"   ✅ Backup saved: {backup_path}")
                    break
                backup_num += 1
        
        # Save
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Report generated successfully!")
        print(f"📄 File: {args.output}")
        print(f"\n📊 Summary:")
        print(f"   • Total topics: {stats['total']}")
        print(f"   • Completed: {stats['completed']}")
        print(f"   • Remaining: {stats['remaining']}")
        print(f"   • Progress: {stats['progress_pct']}%\n")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Tip: Run 'python scripts/mock_topic_generator.py' first")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
