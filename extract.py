import sys
import json
import fitz  # PyMuPDF
from collections import defaultdict

HEADING_KEYWORDS = {
    "profile", "skills", "education", "experience", "employment history",
    "projects", "certifications", "languages", "details", "hobbies", 
    "extra-curricular activities", "summary", "work experience",
    "technical skills", "professional experience", "academic background"
}

def calculate_heading_score(line, size_levels):
    """Calculate a score for how likely this line is to be a heading"""
    text = line["text"].strip().lower()
    score = 0
    
    # Font size is the most important factor
    if line["font_size"] >= size_levels[0] - 1:
        score += 4  # Very likely to be name/title
    elif line["font_size"] >= size_levels[1] - 1:
        score += 3  # Likely section heading
    elif line["font_size"] >= size_levels[2] - 1:
        score += 1  # Possibly subheading
    
    # Keyword matching
    clean_text = text.strip(":.- ").lower()
    if clean_text in HEADING_KEYWORDS:
        score += 2
    
    # Text characteristics (all caps, ends with colon)
    if text.isupper():
        score += 1
    if text.endswith(":") or text.endswith("-"):
        score += 1
    
    # Position on page (headings are often at the top or left)
    if line["y0"] < 150:  # Near top of page
        score += 1
    
    return score

def extract_pdf_layout(pdf_path):
    doc = fitz.open(pdf_path)
    extracted_data = []
    page_heights = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_height = page.rect.height
        page_heights.append(page_height)

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
                    "column": 0
                })

    actual_page_height = page_heights[0] if page_heights else 1000

    # === DETERMINE FONT SIZE HIERARCHY ===
    font_sizes = [item["font_size"] for item in extracted_data]
    if not font_sizes:
        return extracted_data, actual_page_height
        
    unique_sizes = sorted(list(set(font_sizes)), reverse=True)
    
    # We want exactly 3 size levels: title, headings, normal text
    if len(unique_sizes) >= 3:
        size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[-1]]
    elif len(unique_sizes) == 2:
        size_levels = [unique_sizes[0], unique_sizes[1], unique_sizes[1]-2]
    else:
        size_levels = [unique_sizes[0], unique_sizes[0]-2, unique_sizes[0]-4]
    
    # === ASSIGN HEADING SCORES ===
    for item in extracted_data:
        item["heading_score"] = calculate_heading_score(item, size_levels)
    
    # === DYNAMICALLY DETERMINE HEADING SCORE THRESHOLD ===
    # Try different thresholds to get between 3-10 blocks
    possible_thresholds = [5, 4, 3, 2]
    best_threshold = 3  # default
    best_blocks = []
    
    for threshold in possible_thresholds:
        # Identify potential headings with current threshold
        potential_headings = [item for item in extracted_data if item["heading_score"] >= threshold]
        
        # Sort by position (top to bottom, left to right)
        extracted_data.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
        potential_headings.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
        
        # Assign blocks temporarily
        temp_blocks = defaultdict(list)
        current_block = 0
        current_heading = None
        
        for i, item in enumerate(extracted_data):
            # Check if this is a new heading
            if item in potential_headings:
                if item["heading_score"] >= threshold + 1 or (current_heading is None) or (item["font_size"] >= current_heading["font_size"] - 1):
                    current_block += 1
                    current_heading = item
                    item["block"] = current_block
                    temp_blocks[current_block].append(item)
                    continue
            
            # Assign to current block
            if current_block > 0:
                prev_item = extracted_data[i-1] if i > 0 else None
                if prev_item and prev_item["block"] == current_block:
                    vertical_gap = item["y0"] - prev_item["y1"]
                    if vertical_gap < 20:  # Standard gap threshold
                        item["block"] = current_block
                        temp_blocks[current_block].append(item)
        
        # Count actual blocks (non-empty)
        num_blocks = len(temp_blocks)
        
        # Check if this threshold gives us the desired number of blocks
        if 3 <= num_blocks <= 10:
            best_threshold = threshold
            best_blocks = temp_blocks
            break
        elif num_blocks > 10 and threshold == possible_thresholds[-1]:
            # If we still have too many blocks, use the highest threshold
            best_threshold = possible_thresholds[0]
            best_blocks = temp_blocks
        elif num_blocks < 3 and threshold == possible_thresholds[-1]:
            # If we still have too few blocks, use the lowest threshold
            best_threshold = possible_thresholds[-1]
            best_blocks = temp_blocks
    
    # === FINAL BLOCK ASSIGNMENT WITH BEST THRESHOLD ===
    # Reset blocks
    for item in extracted_data:
        item["block"] = 0
    
    # Identify potential headings with best threshold
    potential_headings = [item for item in extracted_data if item["heading_score"] >= best_threshold]
    potential_headings.sort(key=lambda x: (x["page"], x["y0"], x["x0"]))
    
    # Assign blocks
    current_block = 0
    current_heading = None
    
    for i, item in enumerate(extracted_data):
        # Check if this is a new heading
        if item in potential_headings:
            if item["heading_score"] >= best_threshold + 1 or (current_heading is None) or (item["font_size"] >= current_heading["font_size"] - 1):
                current_block += 1
                current_heading = item
                item["block"] = current_block
                continue
        
        # Assign to current block
        if current_block > 0:
            prev_item = extracted_data[i-1] if i > 0 else None
            if prev_item and prev_item["block"] == current_block:
                vertical_gap = item["y0"] - prev_item["y1"]
                if vertical_gap < 20:  # Standard gap threshold
                    item["block"] = current_block
    
    # Assign orphan lines to nearest block
    blocks = defaultdict(list)
    for item in extracted_data:
        if item["block"] != 0:
            blocks[item["block"]].append(item)
    
    # Find all unassigned lines
    unassigned = [item for item in extracted_data if item["block"] == 0]
    
    for item in unassigned:
        min_dist = float('inf')
        closest_block = 0
        
        for block_id, block_items in blocks.items():
            # Use the heading position for distance calculation
            heading = block_items[0]
            dist = ((item["x0"] - heading["x0"])**2 + (item["y0"] - heading["y0"])**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_block = block_id
        
        if closest_block != 0:
            item["block"] = closest_block
            blocks[closest_block].append(item)
    
    # === CLUB SMALL BLOCKS TOGETHER ===
    # Identify small blocks (less than 4 words in total)
    small_blocks = []
    for block_id in list(blocks.keys()):
        total_words = sum(len(item["text"].split()) for item in blocks[block_id])
        if total_words < 4:
            small_blocks.append(block_id)
    
    # Club small blocks with adjacent blocks
    sorted_block_ids = sorted(blocks.keys())
    for i, block_id in enumerate(sorted_block_ids):
        if block_id in small_blocks:
            # Find the nearest non-small block (before or after)
            merge_target = None
            # First try previous block
            if i > 0 and sorted_block_ids[i-1] not in small_blocks:
                merge_target = sorted_block_ids[i-1]
            # Then try next block
            elif i < len(sorted_block_ids)-1 and sorted_block_ids[i+1] not in small_blocks:
                merge_target = sorted_block_ids[i+1]
            
            if merge_target:
                # Merge the small block into the target block
                blocks[merge_target].extend(blocks[block_id])
                blocks[merge_target].sort(key=lambda x: (x["y0"], x["x0"]))
                del blocks[block_id]
    
    # Final cleanup - ensure each block has a heading at the top
    final_blocks = defaultdict(list)
    for block_id, items in blocks.items():
        items.sort(key=lambda x: (x["y0"], x["x0"]))
        
        # Find the best heading in this block (highest score, earliest position)
        best_heading = None
        for item in items:
            if item["heading_score"] >= best_threshold:
                if best_heading is None or item["heading_score"] > best_heading["heading_score"]:
                    best_heading = item
        
        if best_heading is None:
            # No heading found, use the first line with largest font
            best_heading = max(items, key=lambda x: x["font_size"])
        
        # Reorder so heading comes first
        final_items = [best_heading]
        final_items.extend([item for item in items if item != best_heading])
        final_blocks[block_id] = final_items
    
    # Reconstruct the extracted data with proper ordering
    final_data = []
    for block_id in sorted(final_blocks.keys()):
        final_data.extend(final_blocks[block_id])
    
    return final_data, actual_page_height


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