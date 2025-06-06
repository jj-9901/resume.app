import sys
import json
import re
from collections import defaultdict

class ExperienceExtractor:
    def __init__(self):
        self.experience_headings = {
            'experience', 'work experience', 'professional experience',
            'employment history', 'career history', 'employment',
            'professional background'
        }
        self.ignore_phrases = {
            'skills', 'education', 'hobbies', 'projects',
            'certifications', 'references'
        }
        self.date_pattern = re.compile(
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?(?:\s*[-–—]\s*(?:present|now|current|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?|\d{4}))?\s*\d{4}\b|\b\d{4}\s*[-–—]\s*\d{4}\b',
            re.IGNORECASE
        )
        self.position_pattern = re.compile(
            r'^(.*?\b(?:engineer|developer|manager|director|specialist|'
            r'analyst|designer|consultant|associate|officer|lead|head)\b.*?)$',
            re.IGNORECASE
        )

    def is_experience_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading == text_lower for heading in self.experience_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase == text_lower for phrase in self.ignore_phrases)

    def is_date(self, text):
        return bool(self.date_pattern.search(text.strip()))

    def extract_experience_blocks(self, block_texts):
        experiences = []
        current_exp = {}
        collecting = False
        last_line_was_date = False
        
        for line in block_texts:
            line = line.strip()
            if not line:
                continue
                
            # Check if we should start a new experience block
            if (self.is_date(line) or 
                (self.position_pattern.match(line) and not current_exp) or
                (last_line_was_date and not current_exp)):
                
                if current_exp:  # Save previous experience if exists
                    experiences.append(current_exp)
                    current_exp = {}
                
                if self.is_date(line):
                    current_exp['dates'] = line
                    last_line_was_date = True
                else:
                    current_exp['position'] = line
                    last_line_was_date = False
            else:
                # Add details to current experience
                if 'details' not in current_exp:
                    current_exp['details'] = []
                
                if line not in current_exp.get('dates', '') and not self.is_ignore_heading(line):
                    current_exp['details'].append(line)
                last_line_was_date = False
        
        if current_exp:  # Add the last experience
            experiences.append(current_exp)
            
        return experiences

    def process_data(self, data):
        blocks = defaultdict(list)
        self.experience_block_id = None
        
        # First pass: find all blocks and identify the experience block
        for item in data:
            block_id = item.get('block', 0)
            blocks[block_id].append(item['text'])
            if self.is_experience_heading(item['text']):
                self.experience_block_id = block_id

        # Second pass: if no exact match, look for partial matches
        if self.experience_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    text_lower = text.lower()
                    if ('experience' in text_lower or 'employment' in text_lower) and \
                       not any(ignore in text_lower for ignore in self.ignore_phrases):
                        self.experience_block_id = block_id
                        break
                if self.experience_block_id is not None:
                    break

        # If we found an experience block, extract its contents
        if self.experience_block_id is not None:
            experiences = self.extract_experience_blocks(blocks[self.experience_block_id])
            
            # Format the experiences with sequential numbers
            formatted_experiences = {}
            for i, exp in enumerate(experiences, 1):
                formatted_experiences[f"experience_{i}"] = exp
            
            return formatted_experiences
        return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python experience.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        data = input_data['data'] if isinstance(input_data, dict) and 'data' in input_data else input_data

        extractor = ExperienceExtractor()
        experiences = extractor.process_data(data)

        # Output a valid JSON object of experiences
        result = {
        "experience": experiences,
        "used_block": extractor.experience_block_id  # This is an integer or None
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"Error processing experiences: {str(e)}", file=sys.stderr)
        sys.exit(1)