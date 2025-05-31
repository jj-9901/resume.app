# name.py
import sys
import json
import re

def is_name_candidate(text):
    # Accept 1-3 words, capitalized or all-caps
    words = text.strip().split()
    if not (1 <= len(words) <= 3):
        return False
    for w in words:
        if not re.match(r'^([A-Z][a-z]+|[A-Z]+)$', w):
            return False
    return True

def is_probable_email(text):
    return re.match(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+", text) is not None

def find_name(data, page_height):
    top_threshold = 0.6 * page_height
    upper_quarter = 0.75 * page_height

    # Step 1: Check for "Name" label in top quarter
    label_candidates = [item for item in data if 'name' in item['text'].lower() and item['y0'] >= upper_quarter]

    for label in label_candidates:
        label_x = label['x0']
        label_y = label['y0']

        # Look for item to the right (same line or close)
        for item in data:
            if (
                item['x0'] > label['x1'] and
                abs(item['y0'] - label_y) < 20 and  # within same row
                len(item['text'].strip()) > 0
            ):
                # Allow lowercase names here
                possible_name = item['text'].strip()
                if len(possible_name.split()) <= 3:
                    return ' '.join(word.capitalize() for word in possible_name.split())

    # Step 2: Use email-position anchoring — find email label/value pair, take nearby label
    for item in data:
        if 'email' in item['text'].lower():
            item_x = item['x0']
            item_y = item['y0']
            # Find matching value to the right
            for val in data:
                if (
                    val['x0'] > item['x1'] and
                    abs(val['y0'] - item_y) < 20 and
                    is_probable_email(val['text'])
                ):
                    # Now look left of email label for possible name
                    for left_item in data:
                        if (
                            left_item['x1'] < item['x0'] and
                            abs(left_item['y0'] - item_y) < 20 and
                            0 < len(left_item['text'].strip()) <= 50
                        ):
                            maybe_name = left_item['text'].strip()
                            return ' '.join(word.capitalize() for word in maybe_name.split())

    # Step 3: Original candidate logic from top of first page
    candidates = [item for item in data if item.get('y0', 0) >= top_threshold and is_name_candidate(item['text'])]

    if not candidates:
        return "no name detected"

    # Score system (without y)
    def score_no_y(item):
        font_size = item.get('font_size', 0)
        fonts = item.get('fonts', [])
        score = font_size * 5
        bold_indicators = ['Bold', 'Black', 'Heavy']
        if any(any(bi.lower() in f.lower() for bi in bold_indicators) for f in fonts):
            score += 20
        if item['text'].isupper():
            score += 10
        return score

    def score_with_y(item):
        return score_no_y(item) + item.get('y0', 0)

    max_score = max(score_no_y(item) for item in candidates)
    top_items = [item for item in candidates if score_no_y(item) == max_score]

    # Try grouping vertically close entries
    top_items_sorted = sorted(top_items, key=lambda x: x.get('y0', 0), reverse=True)
    grouped = []
    for i, item in enumerate(top_items_sorted):
        group = [item]
        for j in range(i + 1, len(top_items_sorted)):
            if abs(top_items_sorted[j]['y0'] - item['y0']) < 40:
                group.append(top_items_sorted[j])
        if len(group) > len(grouped):
            grouped = group

    if len(grouped) > 1:
        grouped.sort(key=lambda x: x['y0'], reverse=True)
        name = ' '.join(item['text'] for item in grouped).strip()
        if 1 <= len(name.split()) <= 3:
            return ' '.join(word.capitalize() for word in name.split())
        else:
            # fallback to single best
            best = max(candidates, key=score_with_y)
            return ' '.join(word.capitalize() for word in best['text'].split())
    else:
        best = max(candidates, key=score_with_y)
        if best.get('y0', 0) >= top_threshold:
            return ' '.join(word.capitalize() for word in best['text'].split())
        else:
            return "no name detected"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python name.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    json_str = sys.argv[1]
    try:
        obj = json.loads(json_str)
        data = obj.get('data', [])
        page_height = obj.get('page_height', 1000)
    except Exception as e:
        print("Failed to parse JSON:", e, file=sys.stderr)
        sys.exit(1)

    name = find_name(data, page_height)
    print(name)
