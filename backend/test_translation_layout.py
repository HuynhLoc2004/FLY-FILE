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

        self.assertIn('class="pdf-layout-page"', html)
        self.assertIn('class="pdf-layout-block"', html)
        self.assertIn("position:absolute", html)
        self.assertIn("BO CONG AN", html)
        self.assertIn("MAU SO 07/2026", html)
        self.assertIn("CONG HOA XA HOI CHU NGHIA VIET NAM", html)
        # The right-side blocks must retain a left position near 60%+, rather
        # than being reflowed below the left header.
        self.assertRegex(html, r"left:6[0-9]\.\d+%")


if __name__ == "__main__":
    unittest.main()
