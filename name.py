#name.py
import sys
import json
import re

def is_name_candidate(text):
    # Candidate: 1 to 3 words, all starting with uppercase or all caps
    words = text.strip().split()
    if not (1 <= len(words) <= 3):
        return False
    for w in words:
        # Accept all caps or capitalized words with letters only
        if not re.match(r'^([A-Z][a-z]+|[A-Z]+)$', w):
            return False
    return True

def find_name(data, page_height):
    top_threshold = 0.6 * page_height
    candidates = [item for item in data if item.get('y0', 0) >= top_threshold and is_name_candidate(item['text'])]

    if not candidates:
        return "no name detected"

    # Score with and without position
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

    # Get top score (without y)
    max_score = max(score_no_y(item) for item in candidates)
    top_items = [item for item in candidates if score_no_y(item) == max_score]

    # Try to find lines close in vertical space (e.g., < 50 units apart)
    top_items_sorted = sorted(top_items, key=lambda x: x.get('y0', 0), reverse=True)
    grouped = []
    for i, item in enumerate(top_items_sorted):
        group = [item]
        for j in range(i + 1, len(top_items_sorted)):
            if abs(top_items_sorted[j]['y0'] - item['y0']) < 50:  # adjust threshold as needed
                group.append(top_items_sorted[j])
        if len(group) > len(grouped):
            grouped = group

    if len(grouped) > 1:
        # Join group
        grouped.sort(key=lambda x: x['y0'], reverse=True)
        name = ' '.join(item['text'] for item in grouped)
        return ' '.join(word.capitalize() for word in name.split())
    else:
        # Fallback to best item with y-influenced score
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
