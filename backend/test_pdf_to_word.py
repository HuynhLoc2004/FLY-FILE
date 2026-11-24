import io
import unittest
from unittest.mock import patch

import fitz
from docx import Document
from docx.oxml.ns import qn

from services.pdf_to_word import (
    _clean_text,
    _span_text_with_spacing,
    build_docx_from_blocks,
    parse_pdf_to_blocks,
)


def _make_pdf(draw_page):
    document = fitz.open()
    page = document.new_page()
    draw_page(page)
    result = document.tobytes()
    document.close()
    return result


def _block_text(parsed):
    values = []
    for page in parsed["pages"]:
        for block in page["blocks"]:
            if block["type"] == "paragraph":
                for line in block["lines"]:
                    values.append("".join(run["text"] for run in line["runs"]))
            elif block["type"] == "table":
                values.extend(value for row in block["cells"] for value in row)
    return "\n".join(values)


class PdfToWordContentTests(unittest.TestCase):
    def test_normalizes_vietnamese_combining_marks_and_removes_invalid_xml(self):
        self.assertEqual(_clean_text("Vie\u0302\u0323t Nam\x00"), "Việt Nam")

    def test_restores_visual_space_between_separate_spans(self):
        spans = [
            {"text": "Nguyễn", "bbox": (10, 10, 45, 22), "size": 11, "flags": 0, "color": 0},
            {"text": "Văn", "bbox": (49, 10, 68, 22), "size": 11, "flags": 16, "color": 0},
        ]
        runs = _span_text_with_spacing(spans)
        self.assertEqual("".join(run["text"] for run in runs), "Nguyễn Văn")
        self.assertTrue(runs[1]["bold"])

    def test_short_native_text_on_a_drawn_form_is_not_replaced_by_ocr(self):
        def draw(page):
            page.draw_rect(fitz.Rect(40, 40, 300, 100))
            page.insert_text((55, 72), "VALID TEXT")

        pdf = _make_pdf(draw)
        with patch("services.pdf_to_word._try_tesseract_ocr") as tesseract, patch(
            "services.pdf_to_word._try_rapid_ocr"
        ) as rapid:
            parsed = parse_pdf_to_blocks(pdf)

        self.assertIn("VALID TEXT", _block_text(parsed))
        tesseract.assert_not_called()
        rapid.assert_not_called()

    def test_builder_keeps_all_paragraphs_separate_and_content_editable(self):
        blocks = {
            "pages": [{
                "page_num": 1,
                "blocks": [
                    {"type": "paragraph", "bbox": [50, 20, 200, 35], "align": "center",
                     "font_size": 12, "lines": [{"runs": [{"text": "Dòng thứ nhất", "size": 12}]}]},
                    {"type": "paragraph", "bbox": [50, 38, 200, 53], "align": "center",
                     "font_size": 12, "lines": [{"runs": [{"text": "Dòng thứ hai", "size": 12}]}]},
                ],
            }],
        }
        output = build_docx_from_blocks(blocks)
        document = Document(io.BytesIO(output))
        text_paragraphs = [p.text for p in document.paragraphs if p.text]
        self.assertEqual(text_paragraphs, ["Dòng thứ nhất", "Dòng thứ hai"])

    def test_two_column_academic_paper_preserves_full_width_header_and_two_column_body(self):
        from services.pdf_to_word import _sort_blocks_reading_order
        pw = 612.0
        ph = 792.0
        blocks = [
            # Title 1 (centered, wide)
            {"type": "paragraph", "bbox": [58.0, 53.0, 554.0, 70.0], "lines": [{"runs": [{"text": "Title Line 1"}]}]},
            # Title 2 (centered, width ~ 360)
            {"type": "paragraph", "bbox": [126.0, 73.0, 486.0, 91.0], "lines": [{"runs": [{"text": "Title Line 2"}]}]},
            # Authors (centered, width ~ 358)
            {"type": "paragraph", "bbox": [127.0, 101.0, 485.0, 138.0], "lines": [{"runs": [{"text": "Authors & Affiliation"}]}]},
            # Left column: Abstract (x: 47 to 301, y: 150)
            {"type": "paragraph", "bbox": [47.0, 150.0, 301.0, 400.0], "lines": [{"runs": [{"text": "Abstract paragraph"}]}]},
            # Right column: text (x: 313 to 567, y: 150)
            {"type": "paragraph", "bbox": [313.0, 150.0, 567.0, 400.0], "lines": [{"runs": [{"text": "Right column paragraph"}]}]},
            # Right column: Figure 1 image (x: 317 to 560, y: 540)
            {"type": "image", "bbox": [317.0, 540.0, 560.0, 667.0], "ext": "png", "image": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"},
        ]
        sorted_blocks = _sort_blocks_reading_order(blocks, pw, ph)
        
        # Header blocks must be full-width
        self.assertEqual(sorted_blocks[0]["column"], "full")
        self.assertEqual(sorted_blocks[0]["lines"][0]["runs"][0]["text"], "Title Line 1")
        self.assertEqual(sorted_blocks[1]["column"], "full")
        self.assertEqual(sorted_blocks[1]["lines"][0]["runs"][0]["text"], "Title Line 2")
        self.assertEqual(sorted_blocks[2]["column"], "full")
        self.assertEqual(sorted_blocks[2]["lines"][0]["runs"][0]["text"], "Authors & Affiliation")

        # Column 0 must be Abstract
        self.assertEqual(sorted_blocks[3]["column"], 0)
        self.assertEqual(sorted_blocks[3]["lines"][0]["runs"][0]["text"], "Abstract paragraph")

        # Column 1 must be Right column text and Figure 1
        self.assertEqual(sorted_blocks[4]["column"], 1)
        self.assertEqual(sorted_blocks[4]["lines"][0]["runs"][0]["text"], "Right column paragraph")
        self.assertEqual(sorted_blocks[5]["column"], 1)
        self.assertEqual(sorted_blocks[5]["type"], "image")

        # Test DOCX build produces 2 sections: 1-col header and 2-col body
        docx_data = build_docx_from_blocks({"pages": [{"page_num": 1, "blocks": sorted_blocks}]})
        doc = Document(io.BytesIO(docx_data))
        self.assertEqual(len(doc.sections), 2)
        cols_el = doc.sections[1]._sectPr.find(qn("w:cols"))
        self.assertIsNotNone(cols_el)
        self.assertEqual(cols_el.get(qn("w:num")), "2")


if __name__ == "__main__":
    unittest.main()
