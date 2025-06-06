import sys
import json
import re
from collections import defaultdict

class EducationExtractor:
    def __init__(self):
        self.education_headings = {
            'education', 'academic background', 'academics', 'educational background',
            'education & training', 'qualifications'
        }
        self.ignore_phrases = {
            'skills', 'experience', 'hobbies', 'projects',
            'certifications', 'references'
        }
        self.date_pattern = re.compile(
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?(?:\s*[-–—]\s*(?:present|now|current|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?|\d{4}))?\s*\d{4}\b|\b\d{4}\s*[-–—]\s*\d{4}\b',
            re.IGNORECASE
        )
        self.degree_pattern = re.compile(
            r'\b(?:b\.?tech|m\.?tech|ph\.?d|mba|bsc|msc|ba|ma|b\.?e|m\.?e|bca|mca|diploma|degree|graduate)\b',
            re.IGNORECASE
        )

    def is_education_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading == text_lower for heading in self.education_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase == text_lower for phrase in self.ignore_phrases)

    def is_date(self, text):
        return bool(self.date_pattern.search(text.strip()))

    def extract_education_blocks(self, block_texts):
        education_entries = []
        current_entry = {}
        keywords = ['grade', 'completion', 'graduation', 'cgpa', 'percentage', 'class', 'marks']

        for line in block_texts:
            line = line.strip()
            if not line or self.is_education_heading(line):
                continue  # Skip empty lines and section headings like "Education"

            is_start = (
                self.degree_pattern.search(line) or
                any(k in line.lower() for k in keywords) or
                self.is_date(line)
            )

            if is_start and current_entry:
                education_entries.append(current_entry)
                current_entry = {}

            if 'details' not in current_entry:
                current_entry['details'] = []
            current_entry['details'].append(line)

        if current_entry:
            education_entries.append(current_entry)

        return education_entries


    def process_data(self, data):
        blocks = defaultdict(list)
        education_block_id = None

        for item in data:
            block_id = item.get('block', 0)
            blocks[block_id].append(item['text'])
            if self.is_education_heading(item['text']):
                education_block_id = block_id

        if education_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    text_lower = text.lower()
                    if 'education' in text_lower and not any(ignore in text_lower for ignore in self.ignore_phrases):
                        education_block_id = block_id
                        break
                if education_block_id is not None:
                    break

        if education_block_id is not None:
            educations = self.extract_education_blocks(blocks[education_block_id])
            
            formatted_educations = {}
            for i, edu in enumerate(educations, 1):
                formatted_educations[f"education_{i}"] = edu

            return formatted_educations
        return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python education.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        data = input_data['data'] if isinstance(input_data, dict) and 'data' in input_data else input_data

        extractor = EducationExtractor()
        educations = extractor.process_data(data)

        print(json.dumps(educations))
    except Exception as e:
        print(f"Error processing education: {str(e)}", file=sys.stderr)
        sys.exit(1)
