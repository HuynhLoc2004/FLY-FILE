import unittest

import fitz

from services.translation.html_extractor import pdf_page_to_html


class TranslationLayoutTests(unittest.TestCase):
    def test_two_column_header_keeps_source_coordinates(self):
        doc = fitz.open()
        page = doc.new_page(width=600, height=800)
        page.insert_text((50, 60), "BO CONG AN", fontsize=10)
        page.insert_text((390, 40), "MAU SO 07/2026", fontsize=8)
        page.insert_text((360, 60), "CONG HOA XA HOI CHU NGHIA VIET NAM", fontsize=10)

        html, _ = pdf_page_to_html(page, [])

        self.assertIn('class="pdf-flow-page"', html)
        self.assertIn('class="pdf-flow-row"', html)
        self.assertIn('class="pdf-flow-block"', html)
        self.assertNotIn("position:absolute", html)
        self.assertIn("BO CONG AN", html)
        self.assertIn("MAU SO 07/2026", html)
        self.assertIn("CONG HOA XA HOI CHU NGHIA VIET NAM", html)
        # Two source columns receive equal flexible space. A standalone line
        # gets the full row so English cannot be squeezed by its source bbox.
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", html)
        self.assertIn("width:100%;min-width:0", html)

    def test_each_native_pdf_line_becomes_one_translation_paragraph(self):
        doc = fitz.open()
        page = doc.new_page(width=600, height=800)
        page.insert_textbox(
            fitz.Rect(50, 100, 550, 180),
            "Dong thu nhat\nDong thu hai\nDong thu ba",
            fontsize=10,
        )

        html, _ = pdf_page_to_html(page, [])

        self.assertEqual(html.count("<p style="), 3)
        self.assertNotIn("<br/>", html)


if __name__ == "__main__":
    unittest.main()
