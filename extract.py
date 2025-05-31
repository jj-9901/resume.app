import sys
import json
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTPage

def extract_pdf_layout(pdf_path):
    extracted_data = []
    page_heights = []

    for page_num, page_layout in enumerate(extract_pages(pdf_path)):
        if isinstance(page_layout, LTPage):
            page_height = page_layout.height
            page_heights.append(page_height)

        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    if hasattr(text_line, 'get_text'):
                        line_text = text_line.get_text().strip()
                        if not line_text:
                            continue
                        font_sizes = []
                        fonts = set()
                        for char in text_line:
                            if isinstance(char, LTChar):
                                font_sizes.append(char.size)
                                fonts.add(char.fontname)
                        font_size = max(font_sizes) if font_sizes else 0
                        fonts = list(fonts)

                        x0, y0, x1, y1 = text_line.bbox

                        extracted_data.append({
                            'text': line_text,
                            'x0': x0,
                            'y0': y0,
                            'x1': x1,
                            'y1': y1,
                            'font_size': font_size,
                            'fonts': fonts,
                            'page': page_num  # 👈 Add this line
                        })

    actual_page_height = page_heights[0] if page_heights else 1000

    return extracted_data, actual_page_height

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <pdf_path>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    data, page_height = extract_pdf_layout(pdf_path)
    print(json.dumps({
        'page_height': page_height,
        'data': data
    }))
