"""Get priority of a topic by title."""
import json
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Get topic priority')
    parser.add_argument('--topics', required=True, help='Path to topics JSON file')
    parser.add_argument('--title', required=True, help='Topic title')
    args = parser.parse_args()
    
    try:
        with open(args.topics, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for topic in data.get('topics', []):
            if topic['title'] == args.title:
                print(topic['priority'])
                return
        
        # Topic not found
        print(0)
    except Exception as e:
        print(0)
        sys.exit(1)

if __name__ == '__main__':
    main()
