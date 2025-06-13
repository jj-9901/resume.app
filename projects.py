import sys
import json
import re
from collections import defaultdict

class ProjectsExtractor:
    def __init__(self):
        self.project_headings = {
            'projects', 'personal projects', 'academic projects',
            'project experience', 'selected projects', 'project portfolio',
            'research projects', 'technical projects', 'project', 'project details', 'professional projects'
        }
        self.ignore_phrases = {
            'experience', 'education', 'hobbies', 'work',
            'certifications', 'references', 'skills'
        }
        self.project_markers = {
            '•', '●', '○', '■', '□', '♦', '➢', '➔', '⦿', '◘', '◦', '‣'
        }
        self.date_pattern = re.compile(
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?(?:\s*[-–—]\s*(?:present|now|current|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
            r'(?:\s+\d{1,2})?|\d{4}))?\s*\d{4}\b|\b\d{4}\s*[-–—]\s*\d{4}\b',
            re.IGNORECASE
        )
        self.project_name_pattern = re.compile(
            r'^(.*?\b(?:project|research|thesis|dissertation|initiative|'
            r'application|system|platform|tool|software|website|app|bot|visualizer|algorithm)\b.*?)$',
            re.IGNORECASE
        )

    def is_project_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(heading == text_lower for heading in self.project_headings)

    def is_ignore_heading(self, text):
        text_lower = text.lower().strip(".:- ")
        return any(phrase == text_lower for phrase in self.ignore_phrases)

    def is_project_marker(self, text):
        return text.strip() in self.project_markers

    def is_project_name(self, text):
        return bool(self.project_name_pattern.match(text.strip()))

    def extract_project_blocks(self, block_texts):
        projects = []
        current_project = {}
        in_projects_section = False
        
        for line in block_texts:
            line = line.strip()
            if not line:
                continue
                
            # Check if we've entered the projects section
            if not in_projects_section and self.is_project_heading(line):
                in_projects_section = True
                continue
                
            if not in_projects_section:
                continue
                
            # Check if we should start a new project
            if (self.is_project_marker(line) or 
                (self.is_project_name(line) and not current_project) or
                (len(line.split()) <= 6 and self.is_project_name(line))):
                
                if current_project:  # Save previous project if exists
                    projects.append(current_project)
                    current_project = {}
                
                if not self.is_project_marker(line):
                    current_project['name'] = line
            else:
                # Add details to current project
                if 'details' not in current_project:
                    current_project['details'] = []
                
                if line not in current_project.get('name', ''):
                    current_project['details'].append(line)
        
        if current_project:  # Add the last project
            projects.append(current_project)
            
        return projects

    def process_data(self, data):
        blocks = defaultdict(list)
        self.project_block_id = None
        
        # First pass: find all blocks and identify the project block
        for item in data:
            block_id = item.get('block', 0)
            blocks[block_id].append(item['text'])
            if self.is_project_heading(item['text']):
                self.project_block_id = block_id

        # Second pass: if no exact match, look for partial matches
        if self.project_block_id is None:
            for block_id, texts in blocks.items():
                for text in texts:
                    text_lower = text.lower()
                    if ('project' in text_lower or 'research' in text_lower) and \
                       not any(ignore in text_lower for ignore in self.ignore_phrases):
                        self.project_block_id = block_id
                        break
                if self.project_block_id is not None:
                    break

        # If we found a project block, extract its contents
        if self.project_block_id is not None:
            projects = self.extract_project_blocks(blocks[self.project_block_id])
            
            # Format the projects with sequential numbers
            formatted_projects = {}
            for i, proj in enumerate(projects, 1):
                # Clean up the details by removing markers and empty lines
                if 'details' in proj:
                    proj['details'] = [d for d in proj['details'] 
                                     if not self.is_project_marker(d) and d.strip()]
                formatted_projects[f"project_{i}"] = proj
            
            return formatted_projects
        return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python projects.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        data = input_data['data'] if isinstance(input_data, dict) and 'data' in input_data else input_data

        extractor = ProjectsExtractor()
        projects = extractor.process_data(data)

        # Output a valid JSON object of projects
        result = {
        "projects": projects,
        "used_block": extractor.project_block_id  # This is an integer or None
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"Error processing projects: {str(e)}", file=sys.stderr)
        sys.exit(1)