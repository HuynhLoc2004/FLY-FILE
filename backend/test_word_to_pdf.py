import io
import unittest

import fitz
from docx import Document

from services.word_to_pdf import (
    _html_document,
    _maximum_table_columns,
    _unicode_font_path,
    convert_word_bytes_to_pdf_bytes,
)


class WordToPdfTests(unittest.TestCase):
    def test_detects_wide_table_and_uses_landscape_css(self):
        row = "".join(f"<td>Cột {index}</td>" for index in range(10))
        html = f"<table><tr>{row}</tr></table>"
        self.assertEqual(_maximum_table_columns(html), 10)
        self.assertIn("size:A4 landscape", _html_document(html))

    def test_uses_a3_for_extra_wide_table(self):
        row = "".join(f"<td>Cột {index}</td>" for index in range(14))
        self.assertIn("size:A3 landscape", _html_document(f"<table><tr>{row}</tr></table>"))

    def test_unicode_font_is_available(self):
        self.assertIsNotNone(_unicode_font_path())

    def test_generated_pdf_keeps_vietnamese_and_wide_table(self):
        document = Document()
        document.add_paragraph("Cộng hòa Xã hội Chủ nghĩa Việt Nam")
        table = document.add_table(rows=2, cols=10)
        for index, cell in enumerate(table.rows[0].cells):
            cell.text = f"Cột {index + 1}"
        for index, cell in enumerate(table.rows[1].cells):
            cell.text = f"Nội dung tiếng Việt {index + 1}"
        word_buffer = io.BytesIO()
        document.save(word_buffer)

        pdf_bytes = convert_word_bytes_to_pdf_bytes(word_buffer.getvalue())
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in pdf)

        self.assertIn("Cộng hòa Xã hội Chủ nghĩa Việt Nam", text)
        self.assertIn("Nội dung tiếng Việt", text)
        self.assertNotIn("\ufffd", text)
        self.assertGreater(pdf[0].rect.width, pdf[0].rect.height)
        pdf.close()


if __name__ == "__main__":
    unittest.main()
