import sys
import json
import re
from collections import defaultdict

class AchievementsExtractor:
    def __init__(self):
        self.achievement_headings = {
            'awards', 'achievements', 'award and achievements',
            'honors', 'recognition', 'accomplishments'
        }
        self.ignore_phrases = {
            'skills', 'education', 'projects', 'experience',
            'certifications', 'references'
        }
        self.bullet_or_numbered_pattern = re.compile(r'^[-•\d\)]{1,3}\s+')

    def is_achievement_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading == text_lower for heading in self.achievement_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase == text_lower for phrase in self.ignore_phrases)

    def extract_achievement_blocks(self, block_texts):
        achievements = []
        current = []

        for line in block_texts:
            line = line.strip()
            if not line:
                continue

            # Start new item if it's a bullet or numbered list or we collected too much
            if self.bullet_or_numbered_pattern.match(line) or len(current) >= 2:
                if current:
                    achievements.append({"description": " ".join(current)})
                    current = []
            current.append(line)

        if current:
            achievements.append({"description": " ".join(current)})

        return achievements

    def process_data(self, data):
        blocks = defaultdict(list)
        self.achievement_block_id = None

        for item in data:
            block_id = item.get('block', 0)
            blocks[block_id].append(item['text'])
            if self.is_achievement_heading(item['text']):
                self.achievement_block_id = block_id

        if self.achievement_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    text_lower = text.lower()
                    if any(head in text_lower for head in self.achievement_headings) and \
                       not any(ignore in text_lower for ignore in self.ignore_phrases):
                        self.achievement_block_id = block_id
                        break
                if self.achievement_block_id is not None:
                    break

        if self.achievement_block_id is not None:
            extracted = self.extract_achievement_blocks(blocks[self.achievement_block_id])
            formatted = {}
            for i, item in enumerate(extracted, 1):
                formatted[f"achievement_{i}"] = item
            return formatted

        return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python achievements.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        data = input_data['data'] if isinstance(input_data, dict) and 'data' in input_data else input_data

        extractor = AchievementsExtractor()
        achievements = extractor.process_data(data)

        result = {
        "achievements": achievements,
        "used_block": extractor.achievement_block_id  # This is an integer or None
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"Error processing achievements: {str(e)}", file=sys.stderr)
        sys.exit(1)
