import sys
import json
from collections import defaultdict

COMMON_HEADINGS = {
    'skills', 'education', 'experience', 'projects',
    'achievements', 'awards', 'certifications', 'languages',
    'hobbies', 'summary', 'profile', 'details', 'contact',
    'references', 'about', 'personal information'
}

ALREADY_USED = set()  # Will be filled from CLI

def normalize(text):
    return text.strip().lower().strip(":.- ")

def get_other_info(data):
    blocks = defaultdict(list)
    headings = {}

    for item in data:
        block_id = item.get("block", 0)
        blocks[block_id].append(item["text"])
        score = item.get("heading_score", 0)
        if score >= 2:
            headings[block_id] = normalize(item["text"])

    other_info = {}

    for block_id, lines in blocks.items():
        heading = headings.get(block_id, "")
        if heading in COMMON_HEADINGS or heading in ALREADY_USED:
            continue

        if not heading and block_id in headings:
            heading = headings[block_id]

        # Give default heading if not available
        heading = heading or f"section_{block_id}"
        heading_key = heading.replace(" ", "_")

        # Skip completely empty or already extracted content
        clean_lines = [line.strip() for line in lines if line.strip()]
        if not clean_lines:
            continue

        other_info[heading_key] = clean_lines

    return {"other_info": other_info} if other_info else {}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extra.py '<json_string>' '<used_keys_json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        used_keys = json.loads(sys.argv[2])

        ALREADY_USED.update(k.lower() for k in used_keys)

        data = input_data["data"] if isinstance(input_data, dict) and "data" in input_data else input_data
        result = get_other_info(data)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error in extra.py: {str(e)}", file=sys.stderr)
        sys.exit(1)
