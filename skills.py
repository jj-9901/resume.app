import sys
import json
import re
from collections import defaultdict

class SkillsExtractor:
    def __init__(self):
        # More specific heading patterns that must match exactly
        self.skill_headings = {
            'skills', 'technical skills', 'technical expertise', 
            'key skills', 'core competencies', 'technologies',
            'tools', 'programming languages', 'technical proficiencies'
        }
        self.delimiters = r'[,;:/•\-–—|]|\s+and\s+|\s+or\s+|\s+'
        self.date_pattern = re.compile(r'\b(?:\d{1,2}\s)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{4}\b', re.IGNORECASE)
        self.ignore_phrases = {
            'employment history', 'education', 'hobbies', 
            'extra-curricular activities', 'experience'
        }

    def clean_skill(self, skill):
        skill = re.sub(r'^[\s•\-*:]+|[\s•\-*:]+$', '', skill.strip())
        return ' '.join(
            word.capitalize() if not word.isupper() else word
            for word in skill.split()
        )

    def is_skill_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading == text_lower for heading in self.skill_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase == text_lower for phrase in self.ignore_phrases)

    def is_date(self, text):
        return bool(self.date_pattern.match(text.strip()))

    def extract_skills_from_block(self, block_texts):
        cleaned_skills = []
        for line in block_texts:
            if self.is_skill_heading(line) or self.is_date(line) or self.is_ignore_heading(line):
                continue
            pieces = re.split(self.delimiters, line)
            for piece in pieces:
                piece = piece.strip()
                if piece and not self.is_date(piece) and len(piece) > 2:
                    cleaned = self.clean_skill(piece)
                    if cleaned and len(cleaned.split()) < 4:  # Skip long phrases
                        cleaned_skills.append(cleaned)
        return cleaned_skills

    def process_data(self, data):
        """Find the block with a skill heading and extract its contents"""
        blocks = defaultdict(list)
        skill_block_id = None
        
        # First pass: find all blocks and identify the skill block
        for item in data:
            block_id = item.get('block', 0)
            blocks[block_id].append(item['text'])
            # Check if this line is a skill heading
            if self.is_skill_heading(item['text']):
                skill_block_id = block_id

        # Second pass: if no exact match, look for partial matches
        if skill_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    if 'skill' in text.lower() and not any(ignore in text.lower() for ignore in self.ignore_phrases):
                        skill_block_id = block_id
                        break
                if skill_block_id is not None:
                    break

        # If we found a skill block, extract its skills
        if skill_block_id is not None:
            skills = self.extract_skills_from_block(blocks[skill_block_id])
            # Filter out any remaining section headers that might have slipped through
            return [s for s in skills if not self.is_ignore_heading(s)]
        return []

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skills.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        data = input_data['data'] if isinstance(input_data, dict) and 'data' in input_data else input_data

        extractor = SkillsExtractor()
        skills = extractor.process_data(data)

        # Output a valid JSON list of skills
        print(json.dumps(skills))
    except Exception as e:
        print(f"Error processing skills: {str(e)}", file=sys.stderr)
        sys.exit(1)