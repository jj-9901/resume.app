import sys
import json
import fitz  # PyMuPDF
from collections import defaultdict
import re

HEADING_KEYWORDS = {
    "profile", "skills", "education", "experience", "employment history",
    "projects", "certifications", "languages", "details", "hobbies", 
    "extra-curricular activities", "summary", "work experience",
    "technical skills", "professional experience", "academic background", 
    "awards", "achievements", "contact", "references", "publications", "award and achievementser","employment","jobs"
}

DATE_PATTERNS = [
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',
    r'\b\d{4}\b',
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4} – (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',
    r'\b\d{4} – \d{4}\b',
    r'\bPresent\b'
]

def contains_date(text):
    text = text.replace('-', '–')
    for pattern in DATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def calculate_heading_score(line, size_levels):
    text = line["text"].strip().lower()
    score = 0
    
    if line["font_size"] >= size_levels[0] - 1:
        score += 3
    elif line["font_size"] >= size_levels[1] - 1:
        score += 2
    elif line["font_size"] >= size_levels[2] - 1:
        score += 1

    clean_text = text.strip(":.- ").lower()
    if clean_text in HEADING_KEYWORDS:
        score += 2

    if text.isupper():
        score += 1
    if text.endswith(":") or text.endswith("-"):
        score += 1

    if line["y0"] < 150:
        score += 1

    if len(text.split()) <= 5:
        score += 1

    if len(text.split()) <= 1 and line["font_size"] > size_levels[0] - 1:
        score -= 1  # new: penalize short large-font lines

    return score

def detect_columns(lines, page_width):
    if not lines:
        return [0, page_width]

    x_coords = []
    for line in lines:
        x_coords.append(line["x0"])
        x_coords.append(line["x1"])
    x_coords = sorted(x_coords)

    gaps = []
    for i in range(1, len(x_coords)):
        gaps.append(x_coords[i] - x_coords[i-1])

    if not gaps:
        return [0, page_width]

    avg_gap = sum(gaps) / len(gaps)
    std_gap = (sum((g - avg_gap)**2 for g in gaps) / len(gaps))**0.5
    significant_gaps = [g for g in gaps if g > avg_gap + std_gap]

    if not significant_gaps:
        return [0, page_width]

    gap_counts = defaultdict(int)
    for gap in gaps:
        if gap in significant_gaps:
            gap_counts[round(gap, 1)] += 1

    if not gap_counts:
        return [0, page_width]

    column_gap = max(gap_counts.items(), key=lambda x: x[1])[0]

    split_positions = [0]
    for i in range(1, len(x_coords)):
        if round(x_coords[i] - x_coords[i-1], 1) == column_gap:
            split_pos = (x_coords[i-1] + x_coords[i]) / 2
            split_positions.append(split_pos)
    split_positions.append(page_width)

    min_column_width = page_width * 0.2
    final_positions = [split_positions[0]]
    for pos in split_positions[1:-1]:
        if pos - final_positions[-1] >= min_column_width:
            final_positions.append(pos)
    final_positions.append(split_positions[-1])

    if len(final_positions) < 2:
        final_positions = [0, page_width]  # new: force single-column fallback

    return final_positions

def extract_pdf_layout(pdf_path):
    doc = fitz.open(pdf_path)
    extracted_data = []
    page_heights = []
    page_widths = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_height = page.rect.height
        page_width = page.rect.width
        page_heights.append(page_height)
        page_widths.append(page_width)

        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                line_text = ""
                x0s, y0s, x1s, y1s = [], [], [], []
                font_sizes = []
                fonts = set()

                for span in line["spans"]:
                    line_text += span["text"]
                    bbox = span["bbox"]
                    x0s.append(bbox[0])
                    y0s.append(bbox[1])
                    x1s.append(bbox[2])
                    y1s.append(bbox[3])
                    font_sizes.append(span["size"])
                    fonts.add(span["font"])

                if not line_text.strip():
                    continue

                x0, y0, x1, y1 = min(x0s), min(y0s), max(x1s), max(y1s)
                font_size = max(font_sizes)
                fonts = list(fonts)

                extracted_data.append({
                    "text": line_text.strip(),
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "font_size": font_size,
                    "fonts": fonts,
                    "page": page_num,
                    "block": 0,
                    "heading_score": 0,
                    "column": 0,
                    "contains_date": contains_date(line_text.strip())
                })

    actual_page_height = page_heights[0] if page_heights else 1000
    actual_page_width = page_widths[0] if page_widths else 600

    page_columns = {}
    for page_num in set([d["page"] for d in extracted_data]):
        page_lines = [d for d in extracted_data if d["page"] == page_num]
        columns = detect_columns(page_lines, actual_page_width)
        page_columns[page_num] = columns

    for item in extracted_data:
        columns = page_columns[item["page"]]
        for i in range(1, len(columns)):
            if item["x0"] < columns[i]:
                item["column"] = i - 1
                break

    font_sizes = [item["font_size"] for item in extracted_data]
    if not font_sizes:
        return extracted_data, actual_page_height

    unique_sizes = sorted(list(set(font_sizes)), reverse=True)

    if len(unique_sizes) >= 3:
        size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[-1]]
    elif len(unique_sizes) == 2:
        size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[1]-2]
    else:
        size_levels = [unique_sizes[0], unique_sizes[0]-2, unique_sizes[0]-4]

    for item in extracted_data:
        item["heading_score"] = calculate_heading_score(item, size_levels)

    extracted_data.sort(key=lambda x: (x["page"], x["column"], x["y0"], x["x0"]))

    max_score = max(item["heading_score"] for item in extracted_data) if extracted_data else 0

    def count_blocks(threshold):
        blocks = 1
        for i in range(1, len(extracted_data)):
            curr = extracted_data[i]
            prev = extracted_data[i-1]

            if prev["heading_score"] == max_score:
                continue

            if (curr["heading_score"] >= threshold and 
                (curr["y0"] - prev["y1"] > 3 or  # changed from 10 → 3
                 abs(curr["font_size"] - prev["font_size"]) > 1 or
                 curr["column"] != prev["column"])):
                blocks += 1
        return blocks

    low, high = 1.0, 5.0
    best_threshold = 3.0
    best_block_count = count_blocks(3.0)

    for _ in range(10):
        mid = (low + high) / 2
        block_count = count_blocks(mid)

        if 3 <= block_count <= 10:
            best_threshold = mid
            best_block_count = block_count
            break
        elif block_count < 3:
            high = mid - 0.1
        else:
            low = mid + 0.1

    current_block = 1
    extracted_data[0]["block"] = current_block
    block_headings = {1: extracted_data[0]["text"]}

    for i in range(1, len(extracted_data)):
        curr = extracted_data[i]
        prev = extracted_data[i-1]

        if prev["heading_score"] == max_score:
            curr["block"] = current_block
            continue

        if (curr["heading_score"] >= best_threshold and 
            (curr["y0"] - prev["y1"] > 3 or  # changed from 10 → 3
             abs(curr["font_size"] - prev["font_size"]) > 1 or
             curr["column"] != prev["column"])):
            current_block += 1
            block_headings[current_block] = curr["text"]

        curr["block"] = current_block

    while current_block > 10:
        min_size = float('inf')
        merge_pos = -1

        block_sizes = defaultdict(int)
        for item in extracted_data:
            if item["heading_score"] != max_score:
                block_sizes[item["block"]] += 1

        for block in range(1, current_block):
            combined_size = block_sizes.get(block, 0) + block_sizes.get(block+1, 0)
            if combined_size < min_size:
                min_size = combined_size
                merge_pos = block

        for item in extracted_data:
            if item["block"] > merge_pos:
                item["block"] -= 1
        current_block -= 1

    while current_block < 3 and current_block > 1:
        block_sizes = defaultdict(int)
        for item in extracted_data:
            if item["heading_score"] != max_score:
                block_sizes[item["block"]] += 1

        max_block = max(block_sizes.items(), key=lambda x: x[1])[0] if block_sizes else 1
        split_pos = -1

        for i in range(1, len(extracted_data)):
            if extracted_data[i]["block"] == max_block:
                if (extracted_data[i]["heading_score"] >= 2 and 
                    i > 0 and extracted_data[i-1]["block"] == max_block):
                    split_pos = i
                    break

        if split_pos != -1:
            for i in range(split_pos, len(extracted_data)):
                if extracted_data[i]["block"] == max_block:
                    extracted_data[i]["block"] += 1
                else:
                    break
            current_block += 1

    return extracted_data, actual_page_height

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <pdf_path>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    data, page_height = extract_pdf_layout(pdf_path)
    print(json.dumps({
        "page_height": page_height,
        "data": data
    }, ensure_ascii=False, indent=2))




