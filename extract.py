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




# import sys
# import json
# import fitz  # PyMuPDF
# from collections import defaultdict

# HEADING_KEYWORDS = {
#     "profile", "skills", "education", "experience", "employment history",
#     "projects", "certifications", "languages", "details", "hobbies", 
#     "extra-curricular activities", "summary", "work experience",
#     "technical skills", "professional experience", "academic background"
# }

# def calculate_heading_score(line, size_levels):
#     """Calculate a score for how likely this line is to be a heading"""
#     text = line["text"].strip().lower()
#     score = 0
    
#     # Font size is the most important factor
#     if line["font_size"] >= size_levels[0] - 1:
#         score += 4  # Very likely to be name/title
#     elif line["font_size"] >= size_levels[1] - 1:
#         score += 3  # Likely section heading
#     elif line["font_size"] >= size_levels[2] - 1:
#         score += 1  # Possibly subheading
    
#     # Keyword matching
#     clean_text = text.strip(":.- ").lower()
#     if clean_text in HEADING_KEYWORDS:
#         score += 2
    
#     # Text characteristics (all caps, ends with colon)
#     if text.isupper():
#         score += 1
#     if text.endswith(":") or text.endswith("-"):
#         score += 1
    
#     # Position on page (headings are often at the top or left)
#     if line["y0"] < 150:  # Near top of page
#         score += 1
    
#     return score

# def extract_pdf_layout(pdf_path):
#     doc = fitz.open(pdf_path)
#     extracted_data = []
#     page_heights = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         page_height = page.rect.height
#         page_heights.append(page_height)

#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if block["type"] != 0:
#                 continue

#             for line in block["lines"]:
#                 line_text = ""
#                 x0s, y0s, x1s, y1s = [], [], [], []
#                 font_sizes = []
#                 fonts = set()

#                 for span in line["spans"]:
#                     line_text += span["text"]
#                     bbox = span["bbox"]
#                     x0s.append(bbox[0])
#                     y0s.append(bbox[1])
#                     x1s.append(bbox[2])
#                     y1s.append(bbox[3])
#                     font_sizes.append(span["size"])
#                     fonts.add(span["font"])

#                 if not line_text.strip():
#                     continue

#                 x0, y0, x1, y1 = min(x0s), min(y0s), max(x1s), max(y1s)
#                 font_size = max(font_sizes)
#                 fonts = list(fonts)

#                 extracted_data.append({
#                     "text": line_text.strip(),
#                     "x0": x0,
#                     "y0": y0,
#                     "x1": x1,
#                     "y1": y1,
#                     "font_size": font_size,
#                     "fonts": fonts,
#                     "page": page_num,
#                     "block": 0,
#                     "column": 0
#                 })

#     actual_page_height = page_heights[0] if page_heights else 1000

#     # === DETERMINE FONT SIZE HIERARCHY ===
#     font_sizes = [item["font_size"] for item in extracted_data]
#     if not font_sizes:
#         return extracted_data, actual_page_height
        
#     unique_sizes = sorted(list(set(font_sizes)), reverse=True)
    
#     # We want exactly 3 size levels: title, headings, normal text
#     if len(unique_sizes) >= 3:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[-1]]
#     elif len(unique_sizes) == 2:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[1]-2]
#     else:
#         size_levels = [unique_sizes[0], unique_sizes[0]-2, unique_sizes[0]-4]
    
#     # === ASSIGN HEADING SCORES ===
#     for item in extracted_data:
#         item["heading_score"] = calculate_heading_score(item, size_levels)
    
#     # === DYNAMICALLY DETERMINE HEADING SCORE THRESHOLD ===
#     # Try different thresholds to get between 3-10 blocks
#     possible_thresholds = [5, 4, 3, 2]
#     best_threshold = 3  # default
#     best_blocks = []
    
#     for threshold in possible_thresholds:
#         # Identify potential headings with current threshold
#         potential_headings = [item for item in extracted_data if item["heading_score"] >= threshold]
        
#         # Sort by position (top to bottom, left to right)
#         extracted_data.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
#         potential_headings.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
        
#         # Assign blocks temporarily
#         temp_blocks = defaultdict(list)
#         current_block = 0
#         current_heading = None
        
#         for i, item in enumerate(extracted_data):
#             # Check if this is a new heading
#             if item in potential_headings:
#                 if item["heading_score"] >= threshold + 1 or (current_heading is None) or (item["font_size"] >= current_heading["font_size"] - 1):
#                     current_block += 1
#                     current_heading = item
#                     item["block"] = current_block
#                     temp_blocks[current_block].append(item)
#                     continue
            
#             # Assign to current block
#             if current_block > 0:
#                 prev_item = extracted_data[i-1] if i > 0 else None
#                 if prev_item and prev_item["block"] == current_block:
#                     vertical_gap = item["y0"] - prev_item["y1"]
#                     if vertical_gap < 20:  # Standard gap threshold
#                         item["block"] = current_block
#                         temp_blocks[current_block].append(item)
        
#         # Count actual blocks (non-empty)
#         num_blocks = len(temp_blocks)
        
#         # Check if this threshold gives us the desired number of blocks
#         if 3 <= num_blocks <= 10:
#             best_threshold = threshold
#             best_blocks = temp_blocks
#             break
#         elif num_blocks > 10 and threshold == possible_thresholds[-1]:
#             # If we still have too many blocks, use the highest threshold
#             best_threshold = possible_thresholds[0]
#             best_blocks = temp_blocks
#         elif num_blocks < 3 and threshold == possible_thresholds[-1]:
#             # If we still have too few blocks, use the lowest threshold
#             best_threshold = possible_thresholds[-1]
#             best_blocks = temp_blocks
    
#     # === FINAL BLOCK ASSIGNMENT WITH BEST THRESHOLD ===
#     # Reset blocks
#     for item in extracted_data:
#         item["block"] = 0
    
#     # Identify potential headings with best threshold
#     potential_headings = [item for item in extracted_data if item["heading_score"] >= best_threshold]
#     potential_headings.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
    
#     # Assign blocks
#     current_block = 0
#     current_heading = None
    
#     for i, item in enumerate(extracted_data):
#         # Check if this is a new heading
#         if item in potential_headings:
#             if item["heading_score"] >= best_threshold + 1 or (current_heading is None) or (item["font_size"] >= current_heading["font_size"] - 1):
#                 current_block += 1
#                 current_heading = item
#                 item["block"] = current_block
#                 continue
        
#         # Assign to current block
#         if current_block > 0:
#             prev_item = extracted_data[i-1] if i > 0 else None
#             if prev_item and prev_item["block"] == current_block:
#                 vertical_gap = item["y0"] - prev_item["y1"]
#                 if vertical_gap < 20:  # Standard gap threshold
#                     item["block"] = current_block
    
#     # Assign orphan lines to nearest block
#     blocks = defaultdict(list)
#     for item in extracted_data:
#         if item["block"] != 0:
#             blocks[item["block"]].append(item)
    
#     # Find all unassigned lines
#     unassigned = [item for item in extracted_data if item["block"] == 0]
    
#     for item in unassigned:
#         min_dist = float('inf')
#         closest_block = 0
        
#         for block_id, block_items in blocks.items():
#             # Use the heading position for distance calculation
#             heading = block_items[0]
#             dist = ((item["x0"] - heading["x0"])**2 + (item["y0"] - heading["y0"])**2)**0.5
#             if dist < min_dist:
#                 min_dist = dist
#                 closest_block = block_id
        
#         if closest_block != 0:
#             item["block"] = closest_block
#             blocks[closest_block].append(item)
    
#     # === CLUB SMALL BLOCKS TOGETHER ===
#     # Identify small blocks (less than 4 words in total)
#     small_blocks = []
#     for block_id in list(blocks.keys()):
#         total_words = sum(len(item["text"].split()) for item in blocks[block_id])
#         if total_words < 4:
#             small_blocks.append(block_id)
    
#     # Club small blocks with adjacent blocks
#     sorted_block_ids = sorted(blocks.keys())
#     for i, block_id in enumerate(sorted_block_ids):
#         if block_id in small_blocks:
#             # Find the nearest non-small block (before or after)
#             merge_target = None
#             # First try previous block
#             if i > 0 and sorted_block_ids[i-1] not in small_blocks:
#                 merge_target = sorted_block_ids[i-1]
#             # Then try next block
#             elif i < len(sorted_block_ids)-1 and sorted_block_ids[i+1] not in small_blocks:
#                 merge_target = sorted_block_ids[i+1]
            
#             if merge_target:
#                 # Merge the small block into the target block
#                 blocks[merge_target].extend(blocks[block_id])
#                 blocks[merge_target].sort(key=lambda x: (x["y0"], x["x0"]))
#                 del blocks[block_id]
    
#     # Final cleanup - ensure each block has a heading at the top
#     final_blocks = defaultdict(list)
#     for block_id, items in blocks.items():
#         items.sort(key=lambda x: (x["y0"], x["x0"]))
        
#         # Find the best heading in this block (highest score, earliest position)
#         best_heading = None
#         for item in items:
#             if item["heading_score"] >= best_threshold:
#                 if best_heading is None or item["heading_score"] > best_heading["heading_score"]:
#                     best_heading = item
        
#         if best_heading is None:
#             # No heading found, use the first line with largest font
#             best_heading = max(items, key=lambda x: x["font_size"])
        
#         # Reorder so heading comes first
#         final_items = [best_heading]
#         final_items.extend([item for item in items if item != best_heading])
#         final_blocks[block_id] = final_items
    
#     # Reconstruct the extracted data with proper ordering
#     final_data = []
#     for block_id in sorted(final_blocks.keys()):
#         final_data.extend(final_blocks[block_id])
    
#     return final_data, actual_page_height


# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python extract.py <pdf_path>", file=sys.stderr)
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     data, page_height = extract_pdf_layout(pdf_path)
#     print(json.dumps({
#         "page_height": page_height,
#         "data": data
#     }, ensure_ascii=False, indent=2))


























# import sys
# import json
# import fitz  # PyMuPDF
# from collections import defaultdict
# import numpy as np

# HEADING_KEYWORDS = {
#     "profile", "skills", "education", "experience", "employment history",
#     "projects", "certifications", "languages", "details", "hobbies", 
#     "extra-curricular activities", "summary", "work experience",
#     "technical skills", "professional experience", "academic background"
# }

# def calculate_heading_score(line, size_levels):
#     """Calculate a score for how likely this line is to be a heading"""
#     text = line["text"].strip().lower()
#     score = 0
    
#     # Font size is the most important factor
#     if line["font_size"] >= size_levels[0] - 1:
#         score += 4  # Very likely to be name/title
#     elif line["font_size"] >= size_levels[1] - 1:
#         score += 3  # Likely section heading
#     elif line["font_size"] >= size_levels[2] - 1:
#         score += 1  # Possibly subheading
    
#     # Keyword matching
#     clean_text = text.strip(":.- ").lower()
#     if clean_text in HEADING_KEYWORDS:
#         score += 2
    
#     # Text characteristics (all caps, ends with colon)
#     if text.isupper():
#         score += 1
#     if text.endswith(":") or text.endswith("-"):
#         score += 1
    
#     # Position on page (headings are often at the top or left)
#     if line["y0"] < 150:  # Near top of page
#         score += 1
    
#     return score

# def detect_columns(extracted_data, page_width):
#     """Detect if the page has multiple columns by analyzing x-coordinate gaps"""
#     if not extracted_data:
#         return None
    
#     # Collect all x0 and x1 coordinates
#     x_coords = []
#     for item in extracted_data:
#         x_coords.extend([item["x0"], item["x1"]])
    
#     # Sort and get unique x coordinates
#     x_coords = sorted(list(set(x_coords)))
    
#     # Calculate gaps between consecutive x coordinates
#     gaps = []
#     for i in range(1, len(x_coords)):
#         gaps.append(x_coords[i] - x_coords[i-1])
    
#     if not gaps:
#         return None
    
#     # Find significant gaps (potential column separators)
#     avg_gap = np.mean(gaps)
#     std_gap = np.std(gaps)
#     significant_gaps = [g for g in gaps if g > avg_gap + 2*std_gap]
    
#     if not significant_gaps:
#         return None
    
#     # Find the most common significant gap (column separator width)
#     column_separator = max(set(significant_gaps), key=significant_gaps.count)
    
#     # Find all positions where this gap occurs
#     column_boundaries = [0]
#     for i in range(1, len(x_coords)):
#         if x_coords[i] - x_coords[i-1] >= column_separator * 0.8:  # 80% of separator width
#             column_boundaries.append((x_coords[i-1] + x_coords[i]) / 2)  # Midpoint as boundary
    
#     column_boundaries.append(page_width)
#     column_boundaries = sorted(list(set(column_boundaries)))
    
#     # We need at least 2 columns to proceed
#     if len(column_boundaries) < 2:
#         return None
    
#     return column_boundaries

# def assign_columns(extracted_data, column_boundaries):
#     """Assign each text item to a column based on its x-position"""
#     if not column_boundaries:
#         for item in extracted_data:
#             item["column"] = 0
#         return
    
#     for item in extracted_data:
#         x_center = (item["x0"] + item["x1"]) / 2
#         assigned = False
#         for col_idx in range(len(column_boundaries)-1):
#             if column_boundaries[col_idx] <= x_center < column_boundaries[col_idx+1]:
#                 item["column"] = col_idx + 1  # 1-based indexing
#                 assigned = True
#                 break
#         if not assigned:
#             item["column"] = 0

# def extract_pdf_layout(pdf_path):
#     doc = fitz.open(pdf_path)
#     extracted_data = []
#     page_heights = []
#     page_widths = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         page_height = page.rect.height
#         page_width = page.rect.width
#         page_heights.append(page_height)
#         page_widths.append(page_width)

#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if block["type"] != 0:
#                 continue

#             for line in block["lines"]:
#                 line_text = ""
#                 x0s, y0s, x1s, y1s = [], [], [], []
#                 font_sizes = []
#                 fonts = set()

#                 for span in line["spans"]:
#                     line_text += span["text"]
#                     bbox = span["bbox"]
#                     x0s.append(bbox[0])
#                     y0s.append(bbox[1])
#                     x1s.append(bbox[2])
#                     y1s.append(bbox[3])
#                     font_sizes.append(span["size"])
#                     fonts.add(span["font"])

#                 if not line_text.strip():
#                     continue

#                 x0, y0, x1, y1 = min(x0s), min(y0s), max(x1s), max(y1s)
#                 font_size = max(font_sizes)
#                 fonts = list(fonts)

#                 extracted_data.append({
#                     "text": line_text.strip(),
#                     "x0": x0,
#                     "y0": y0,
#                     "x1": x1,
#                     "y1": y1,
#                     "font_size": font_size,
#                     "fonts": fonts,
#                     "page": page_num,
#                     "block": 0,
#                     "column": 0
#                 })

#     actual_page_height = page_heights[0] if page_heights else 1000
#     actual_page_width = page_widths[0] if page_widths else 600

#     # === COLUMN DETECTION ===
#     column_boundaries = detect_columns(extracted_data, actual_page_width)
#     assign_columns(extracted_data, column_boundaries)

#     # === DETERMINE FONT SIZE HIERARCHY ===
#     font_sizes = [item["font_size"] for item in extracted_data]
#     if not font_sizes:
#         return extracted_data, actual_page_height
        
#     unique_sizes = sorted(list(set(font_sizes)), reverse=True)
    
#     # We want exactly 3 size levels: title, headings, normal text
#     if len(unique_sizes) >= 3:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[-1]]
#     elif len(unique_sizes) == 2:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[1]-2]
#     else:
#         size_levels = [unique_sizes[0], unique_sizes[0]-2, unique_sizes[0]-4]
    
#     # === ASSIGN HEADING SCORES ===
#     for item in extracted_data:
#         item["heading_score"] = calculate_heading_score(item, size_levels)
    
#     # === PROCESS EACH COLUMN SEPARATELY ===
#     # First, separate data by columns
#     columns_data = defaultdict(list)
#     for item in extracted_data:
#         columns_data[item["column"]].append(item)
    
#     # Process each column to find its own headings and blocks
#     all_blocks = defaultdict(list)
#     block_counter = 1
    
#     for column, column_items in columns_data.items():
#         # Sort items in this column by position
#         column_items.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
        
#         # Find potential headings in this column (exclude name/title if it's the first item)
#         possible_thresholds = sorted(list(set([item["heading_score"] for item in column_items])), reverse=True)
        
#         # Find the best threshold for this column (excluding the name/title if it's at the top)
#         best_threshold = None
#         if len(column_items) > 0:
#             # The first item might be the name/title - we'll handle it separately
#             first_item = column_items[0]
#             if first_item["heading_score"] >= size_levels[0] - 1:
#                 # This is likely the name/title - create a separate block for it
#                 first_item["block"] = block_counter
#                 all_blocks[block_counter].append(first_item)
#                 block_counter += 1
#                 column_items = column_items[1:]  # Process the rest of the column
        
#         # Find threshold for the remaining items
#         if column_items:
#             # Try to find a threshold that gives reasonable number of headings (3-10)
#             for threshold in possible_thresholds:
#                 num_headings = sum(1 for item in column_items if item["heading_score"] >= threshold)
#                 if 3 <= num_headings <= 10:
#                     best_threshold = threshold
#                     break
            
#             if best_threshold is None and possible_thresholds:
#                 best_threshold = possible_thresholds[0]
            
#             # Assign blocks in this column
#             current_block = None
#             for item in column_items:
#                 if item["heading_score"] >= best_threshold:
#                     # New block
#                     current_block = block_counter
#                     block_counter += 1
#                     item["block"] = current_block
#                     all_blocks[current_block].append(item)
#                 elif current_block is not None:
#                     # Add to current block if vertical gap is small
#                     prev_item = all_blocks[current_block][-1]
#                     vertical_gap = item["y0"] - prev_item["y1"]
#                     if vertical_gap < 20:
#                         item["block"] = current_block
#                         all_blocks[current_block].append(item)
    
#     # === FINAL BLOCK ASSIGNMENT AND CLEANUP ===
#     # Reconstruct the extracted data with proper ordering
#     final_data = []
    
#     # First, handle name/title blocks (they should come first)
#     name_blocks = []
#     other_blocks = []
#     for block_id, items in all_blocks.items():
#         if len(items) == 1 and items[0]["heading_score"] >= size_levels[0] - 1:
#             name_blocks.append((items[0]["page"], items[0]["column"], items[0]["y0"], block_id))
#         else:
#             other_blocks.append((items[0]["page"], items[0]["column"], items[0]["y0"], block_id))
    
#     # Sort name blocks by page, column, position
#     name_blocks.sort()
    
#     # Sort other blocks by page, column, position
#     other_blocks.sort()
    
#     # Add name blocks first
#     for _, _, _, block_id in name_blocks:
#         final_data.extend(all_blocks[block_id])
    
#     # Add other blocks
#     for _, _, _, block_id in other_blocks:
#         final_data.extend(all_blocks[block_id])
    
#     # Ensure all items are assigned to blocks
#     for item in extracted_data:
#         if item["block"] == 0:
#             # Find the nearest block in the same column
#             best_block = None
#             min_distance = float('inf')
            
#             for block_id, block_items in all_blocks.items():
#                 if block_items[0]["column"] == item["column"]:
#                     # Calculate distance to first item in block
#                     distance = abs(item["y0"] - block_items[0]["y0"])
#                     if distance < min_distance:
#                         min_distance = distance
#                         best_block = block_id
            
#             if best_block is not None:
#                 item["block"] = best_block
#                 all_blocks[best_block].append(item)
#                 all_blocks[best_block].sort(key=lambda x: (x["y0"], x["x0"]))
    
#     # Re-sort final data after all assignments
#     final_data.sort(key=lambda x: (x["page"], x["column"], x["y0"], x["x0"]))
    
#     return final_data, actual_page_height

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python extract.py <pdf_path>", file=sys.stderr)
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     data, page_height = extract_pdf_layout(pdf_path)
#     print(json.dumps({
#         "page_height": page_height,
#         "data": data
#     }, ensure_ascii=False, indent=2))


























# import sys
# import json
# import fitz  # PyMuPDF
# from collections import defaultdict

# HEADING_KEYWORDS = {
#     "profile", "skills", "education", "experience", "employment history",
#     "projects", "certifications", "languages", "details", "hobbies", 
#     "extra-curricular activities", "summary", "work experience",
#     "technical skills", "professional experience", "academic background"
# }

# def calculate_heading_score(line, size_levels):
#     """Calculate a score for how likely this line is to be a heading"""
#     text = line["text"].strip().lower()
#     score = 0
    
#     # Font size is the most important factor
#     if line["font_size"] >= size_levels[0] - 1:
#         score += 4  # Very likely to be name/title
#     elif line["font_size"] >= size_levels[1] - 1:
#         score += 3  # Likely section heading
#     elif line["font_size"] >= size_levels[2] - 1:
#         score += 1  # Possibly subheading
    
#     # Keyword matching
#     clean_text = text.strip(":.- ").lower()
#     if clean_text in HEADING_KEYWORDS:
#         score += 2
    
#     # Text characteristics (all caps, ends with colon)
#     if text.isupper():
#         score += 1
#     if text.endswith(":") or text.endswith("-"):
#         score += 1
    
#     # Position on page (headings are often at the top or left)
#     if line["y0"] < 150:  # Near top of page
#         score += 1
    
#     return score

# def extract_pdf_layout(pdf_path):
#     doc = fitz.open(pdf_path)
#     extracted_data = []
#     page_heights = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         page_height = page.rect.height
#         page_heights.append(page_height)

#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if block["type"] != 0:
#                 continue

#             for line in block["lines"]:
#                 line_text = ""
#                 x0s, y0s, x1s, y1s = [], [], [], []
#                 font_sizes = []
#                 fonts = set()

#                 for span in line["spans"]:
#                     line_text += span["text"]
#                     bbox = span["bbox"]
#                     x0s.append(bbox[0])
#                     y0s.append(bbox[1])
#                     x1s.append(bbox[2])
#                     y1s.append(bbox[3])
#                     font_sizes.append(span["size"])
#                     fonts.add(span["font"])

#                 if not line_text.strip():
#                     continue

#                 x0, y0, x1, y1 = min(x0s), min(y0s), max(x1s), max(y1s)
#                 font_size = max(font_sizes)
#                 fonts = list(fonts)

#                 extracted_data.append({
#                     "text": line_text.strip(),
#                     "x0": x0,
#                     "y0": y0,
#                     "x1": x1,
#                     "y1": y1,
#                     "font_size": font_size,
#                     "fonts": fonts,
#                     "page": page_num,
#                     "block": 0,
#                     "column": 0
#                 })

#     actual_page_height = page_heights[0] if page_heights else 1000

#     # === DETERMINE FONT SIZE HIERARCHY ===
#     font_sizes = [item["font_size"] for item in extracted_data]
#     if not font_sizes:
#         return extracted_data, actual_page_height
        
#     unique_sizes = sorted(list(set(font_sizes)), reverse=True)
    
#     # We want exactly 3 size levels: title, headings, normal text
#     if len(unique_sizes) >= 3:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[-1]]
#     elif len(unique_sizes) == 2:
#         size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[1]-2]
#     else:
#         size_levels = [unique_sizes[0], unique_sizes[0]-2, unique_sizes[0]-4]
    
#     # === ASSIGN HEADING SCORES ===
#     for item in extracted_data:
#         item["heading_score"] = calculate_heading_score(item, size_levels)
    
#     # === GROUP INTO BLOCKS ===
#     # First identify all potential headings (high scoring lines)
#     potential_headings = [item for item in extracted_data if item["heading_score"] >= 3]
    
#     # Sort by position (top to bottom, left to right)
#     extracted_data.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
#     potential_headings.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
    
#     # Assign blocks
#     current_block = 0
#     current_heading = None
#     vertical_gap_threshold = 20  # Points between lines to consider a new block
    
#     for i, item in enumerate(extracted_data):
#         # Check if this is a new heading
#         if item in potential_headings:
#             # Only start new block if this is a strong heading (not subheading)
#             if item["heading_score"] >= 4 or (current_heading is None) or (item["font_size"] >= current_heading["font_size"] - 1):
#                 current_block += 1
#                 current_heading = item
#                 item["block"] = current_block
#                 continue
        
#         # Assign to current block if:
#         # 1. We have a current block
#         # 2. The vertical gap isn't too large
#         # 3. It's not another heading with similar score
#         if current_block > 0:
#             prev_item = extracted_data[i-1] if i > 0 else None
#             if prev_item and prev_item["block"] == current_block:
#                 vertical_gap = item["y0"] - prev_item["y1"]
#                 if vertical_gap < vertical_gap_threshold:
#                     item["block"] = current_block
    
#     # Assign orphan lines to nearest block
#     blocks = defaultdict(list)
#     for item in extracted_data:
#         if item["block"] != 0:
#             blocks[item["block"]].append(item)
    
#     # Find all unassigned lines
#     unassigned = [item for item in extracted_data if item["block"] == 0]
    
#     for item in unassigned:
#         min_dist = float('inf')
#         closest_block = 0
        
#         for block_id, block_items in blocks.items():
#             # Use the heading position for distance calculation
#             heading = block_items[0]
#             dist = ((item["x0"] - heading["x0"])**2 + (item["y0"] - heading["y0"])**2)**0.5
#             if dist < min_dist:
#                 min_dist = dist
#                 closest_block = block_id
        
#         if closest_block != 0:
#             item["block"] = closest_block
#             blocks[closest_block].append(item)
    
#     # === CLUB SMALL BLOCKS TOGETHER ===
#     # Identify small blocks (less than 4 words in total)
#     small_blocks = []
#     for block_id in list(blocks.keys()):
#         total_words = sum(len(item["text"].split()) for item in blocks[block_id])
#         if total_words < 4:
#             small_blocks.append(block_id)
    
#     # Club small blocks with adjacent blocks
#     sorted_block_ids = sorted(blocks.keys())
#     for i, block_id in enumerate(sorted_block_ids):
#         if block_id in small_blocks:
#             # Find the nearest non-small block (before or after)
#             merge_target = None
#             # First try previous block
#             if i > 0 and sorted_block_ids[i-1] not in small_blocks:
#                 merge_target = sorted_block_ids[i-1]
#             # Then try next block
#             elif i < len(sorted_block_ids)-1 and sorted_block_ids[i+1] not in small_blocks:
#                 merge_target = sorted_block_ids[i+1]
            
#             if merge_target:
#                 # Merge the small block into the target block
#                 blocks[merge_target].extend(blocks[block_id])
#                 blocks[merge_target].sort(key=lambda x: (x["y0"], x["x0"]))
#                 del blocks[block_id]
    
#     # Final cleanup - ensure each block has a heading at the top
#     final_blocks = defaultdict(list)
#     for block_id, items in blocks.items():
#         items.sort(key=lambda x: (x["y0"], x["x0"]))
        
#         # Find the best heading in this block (highest score, earliest position)
#         best_heading = None
#         for item in items:
#             if item["heading_score"] >= 3:
#                 if best_heading is None or item["heading_score"] > best_heading["heading_score"]:
#                     best_heading = item
        
#         if best_heading is None:
#             # No heading found, use the first line with largest font
#             best_heading = max(items, key=lambda x: x["font_size"])
        
#         # Reorder so heading comes first
#         final_items = [best_heading]
#         final_items.extend([item for item in items if item != best_heading])
#         final_blocks[block_id] = final_items
    
#     # Reconstruct the extracted data with proper ordering
#     final_data = []
#     for block_id in sorted(final_blocks.keys()):
#         final_data.extend(final_blocks[block_id])
    
#     return final_data, actual_page_height


# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python extract.py <pdf_path>", file=sys.stderr)
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     data, page_height = extract_pdf_layout(pdf_path)
#     print(json.dumps({
#         "page_height": page_height,
#         "data": data
#     }, ensure_ascii=False, indent=2))















#     import sys
# import json
# import fitz  # PyMuPDF
# from collections import defaultdict

# HEADING_KEYWORDS = {
#     "profile", "skills", "education", "experience", "employment history",
#     "projects", "certifications", "languages", "details", "hobbies", "extra-curricular activities"
# }


# def extract_pdf_layout(pdf_path):
#     doc = fitz.open(pdf_path)
#     extracted_data = []
#     page_heights = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         page_height = page.rect.height
#         page_heights.append(page_height)

#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if block["type"] != 0:
#                 continue

#             for line in block["lines"]:
#                 line_text = ""
#                 x0s, y0s, x1s, y1s = [], [], [], []
#                 font_sizes = []
#                 fonts = set()

#                 for span in line["spans"]:
#                     line_text += span["text"]
#                     bbox = span["bbox"]
#                     x0s.append(bbox[0])
#                     y0s.append(bbox[1])
#                     x1s.append(bbox[2])
#                     y1s.append(bbox[3])
#                     font_sizes.append(span["size"])
#                     fonts.add(span["font"])

#                 if not line_text.strip():
#                     continue

#                 x0, y0, x1, y1 = min(x0s), min(y0s), max(x1s), max(y1s)
#                 font_size = max(font_sizes)
#                 fonts = list(fonts)

#                 extracted_data.append({
#                     "text": line_text.strip(),
#                     "x0": x0,
#                     "y0": y0,
#                     "x1": x1,
#                     "y1": y1,
#                     "font_size": font_size,
#                     "fonts": fonts,
#                     "page": page_num,
#                     "block": 0,
#                     "column": 0
#                 })

#     actual_page_height = page_heights[0] if page_heights else 1000

#     # === BLOCK ASSIGNMENT BASED ON PROXIMITY & SCORE ===
#     pages = defaultdict(list)
#     for item in extracted_data:
#         pages[item["page"]].append(item)

#     block_counter = 0
#     vertical_gap_threshold = 15
#     x_shift_threshold = 40

#     for page_num, lines in pages.items():
#         lines.sort(key=lambda l: (l["column"], l["y0"]))
#         last_line = None

#         for line in lines:
#             start_new_block = False
#             if last_line is None:
#                 start_new_block = True
#             else:
#                 vertical_gap = line["y0"] - last_line["y1"]
#                 x_diff = abs(line["x0"] - last_line["x0"])
#                 same_score = abs(line["font_size"] - last_line["font_size"]) < 0.5

#                 if vertical_gap > vertical_gap_threshold or x_diff > x_shift_threshold:
#                     start_new_block = True
#                 elif not same_score:
#                     start_new_block = True

#             if start_new_block:
#                 block_counter += 1

#             line["block"] = block_counter
#             last_line = line

#     # === HEADING PRIORITY: OVERRIDE BASED ON FONT SIZE + KEYWORDS ===
#     for page_num, lines in pages.items():
#         max_font = max(l["font_size"] for l in lines) if lines else 0

#         for line in lines:
#             text = line["text"].strip().lower().strip(":")
#             is_heading = (
#                 line["font_size"] >= max_font - 1 or
#                 text in HEADING_KEYWORDS
#             )
#             if is_heading:
#                 block_counter += 1
#                 line["block"] = block_counter

#     # === MERGE TINY BLOCKS (less than 4 words) TO NEAREST LARGE BLOCK ===
#     block_map = defaultdict(list)
#     for item in extracted_data:
#         block_map[item["block"]].append(item)

#     updated_blocks = {}
#     for block_id, items in block_map.items():
#         total_words = sum(len(i["text"].split()) for i in items)
#         if total_words < 4:
#             min_dist = float("inf")
#             closest_block = None
#             for other_id, other_items in block_map.items():
#                 if other_id == block_id:
#                     continue
#                 other_words = sum(len(l["text"].split()) for l in other_items)
#                 if other_words >= 4:
#                     dists = [
#                         ((a["x0"] - b["x0"]) ** 2 + (a["y0"] - b["y0"]) ** 2) ** 0.5
#                         for a in items for b in other_items
#                     ]
#                     avg_dist = sum(dists) / len(dists) if dists else float("inf")
#                     if avg_dist < min_dist:
#                         min_dist = avg_dist
#                         closest_block = other_id
#             if closest_block is not None:
#                 updated_blocks[block_id] = closest_block

#     for item in extracted_data:
#         if item["block"] in updated_blocks:
#             item["block"] = updated_blocks[item["block"]]

#     return extracted_data, actual_page_height


# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python extract.py <pdf_path>", file=sys.stderr)
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     data, page_height = extract_pdf_layout(pdf_path)
#     print(json.dumps({
#         "page_height": page_height,
#         "data": data
#     }, ensure_ascii=False, indent=2))