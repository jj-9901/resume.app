import sys
import json
import re
from collections import defaultdict

class AchievementsExtractor:
    def __init__(self):
        self.achievement_headings = {
            'awards', 'achievements', 'award and achievements',
            'honors', 'recognition', 'accomplishments',
            'awards/achievements'  # Added this pattern
        }
        self.ignore_phrases = {
            'skills', 'education', 'projects', 'experience',
            'certifications', 'references'
        }
        self.bullet_or_numbered_pattern = re.compile(r'^(\d+\.\s+|[-•*]\s+)')
        self.achievement_pattern = re.compile(
            r'(1st|2nd|3rd|\d+th)\s+prize|finalist|award|honor|achievement',
            re.IGNORECASE
        )

    def is_achievement_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading in text_lower for heading in self.achievement_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase in text_lower for phrase in self.ignore_phrases)

    def is_achievement_text(self, text):
        return bool(self.achievement_pattern.search(text))

    def extract_achievement_blocks(self, block_texts):
        achievements = []
        current = []
        in_achievements_section = False
        max_lines = 10  # Prevent capturing too much unrelated text
        
        for line in block_texts:
            line = line.strip()
            if not line:
                continue

            # Check if this line starts the achievements section
            if not in_achievements_section and self.is_achievement_heading(line):
                in_achievements_section = True
                continue
            
            # Skip if we're not in achievements section yet
            if not in_achievements_section:
                continue
                
            # Check if we've hit another section
            if self.is_ignore_heading(line):
                break
                
            # If it's a bullet/numbered item or looks like an achievement
            if (self.bullet_or_numbered_pattern.match(line) or 
                self.is_achievement_text(line)):
                if current:  # Save previous achievement if exists
                    achievements.append({"description": " ".join(current)})
                    current = []
            
            current.append(line)
            
            # Prevent collecting too much unrelated text
            if len(current) >= max_lines:
                if current:
                    achievements.append({"description": " ".join(current)})
                    current = []
                break

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

        # If no explicit heading found, look for block with achievement-like text
        if self.achievement_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    if self.is_achievement_text(text):
                        self.achievement_block_id = block_id
                        break
                if self.achievement_block_id is not None:
                    break

        if self.achievement_block_id is not None:
            extracted = self.extract_achievement_blocks(blocks[self.achievement_block_id])
            # Filter out very short or non-achievement items
            filtered = [
                item for item in extracted 
                if (len(item['description'].split()) >= 3 and 
                    self.is_achievement_text(item['description']))
            ]
            formatted = {}
            for i, item in enumerate(filtered, 1):
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
            "used_block": extractor.achievement_block_id
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"Error processing achievements: {str(e)}", file=sys.stderr)
        sys.exit(1)