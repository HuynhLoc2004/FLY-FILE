import io
import unittest
from unittest.mock import patch

import fitz
from docx import Document

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


if __name__ == "__main__":
    unittest.main()
