import sys
import json
from collections import defaultdict

COMMON_HEADINGS = {
    'skills', 'education', 'experience', 'projects',
    'achievements', 'awards', 'certifications', 'languages',
    'hobbies', 'summary', 'profile', 'details', 'contact',
    'references', 'about', 'personal information'
}

USED_BLOCKS = set()

def get_other_info(data):
    blocks = defaultdict(list)
    for item in data:
        block_id = item.get("block", 0)
        blocks[block_id].append(item)

    other_info = {}
    for block_id, items in blocks.items():
        if block_id in USED_BLOCKS:
            continue

        clean_raw = []

        for item in items:
            text = item.get('text', '').strip()
            if not text:
                continue

            clean_raw.append(text)

        if clean_raw:
            # Just assign the list directly to the block key, no extra keys like 'raw'
            other_info[f"section_{block_id}"] = clean_raw

    return {"other_info": other_info} if other_info else {}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extra.py '<extracted_data_json>' '<used_blocks_json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        used_blocks = json.loads(sys.argv[2])
        USED_BLOCKS.update(used_blocks)

        data = input_data["data"] if isinstance(input_data, dict) and "data" in input_data else input_data
        result = get_other_info(data)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error in extra.py: {str(e)}", file=sys.stderr)
        sys.exit(1)
