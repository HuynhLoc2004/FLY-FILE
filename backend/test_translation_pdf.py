import unittest

from main import _html_to_pdf_bytes


class TranslationPdfTests(unittest.TestCase):
    def test_html_renderer_returns_a_pdf(self):
        pdf = _html_to_pdf_bytes(
            "<html><body><h1>Translated document</h1>"
            "<p>Full name: NGUYEN VAN AN</p></body></html>"
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
