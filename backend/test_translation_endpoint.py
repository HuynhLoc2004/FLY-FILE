import io
import os
import unittest
from unittest.mock import patch
import fitz

from fastapi import HTTPException, UploadFile

from main import api_translate_pdf_html
from services.translation.html_translator import TranslationProviderError


class TranslationEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_failed_vision_page_does_not_discard_translated_pages(self):
        document = fitz.open()
        document.new_page()
        document.new_page()
        pdf_bytes = document.tobytes()
        document.close()
        pages = [
            {
                "page_num": 1, "width": 595, "height": 842,
                "html": '<div class="pdf-flow-block"><p>Trang một</p></div>',
                "is_scanned": False, "preserved_assets": [],
            },
            {
                "page_num": 2, "width": 595, "height": 842,
                "html": '<div class="pdf-flow-page"></div>',
                "is_scanned": True, "preserved_assets": [],
            },
        ]
        upload = UploadFile(filename="mixed.pdf", file=io.BytesIO(pdf_bytes))

        with (
            patch("services.translation.html_translator.get_gemini_api_key", return_value="test-key"),
            patch("main.pdf_to_html_pages", return_value=pages),
            patch("services.translation.html_translator.translate_html_pages", return_value=["<p>Page one</p>"]),
            patch(
                "services.translation.html_translator.translate_pdf_page_to_html",
                side_effect=TranslationProviderError("quota"),
            ),
        ):
            result = await api_translate_pdf_html(upload)

        self.assertEqual(result["total_pages"], 2)
        self.assertEqual(result["failed_pages"], [2])
        self.assertIn("Page one", result["pages"][0]["translated_html"])
        self.assertIn("Không thể dịch trang 2", result["pages"][1]["translated_html"])

    async def test_missing_key_returns_service_unavailable_before_pdf_processing(self):
        upload = UploadFile(filename="sample.pdf", file=io.BytesIO(b"not-a-pdf"))

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                await api_translate_pdf_html(upload)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("GEMINI_API_KEY", raised.exception.detail)

    async def test_ninety_one_pages_are_batched_without_blank_results(self):
        pages = [
            {
                "page_num": number,
                "width": 595,
                "height": 842,
                "html": f'<div class="pdf-flow-page"><div class="pdf-flow-block"><p>Trang {number}</p></div></div>',
                "is_scanned": False,
                "preserved_assets": [],
            }
            for number in range(1, 92)
        ]
        upload = UploadFile(filename="large.pdf", file=io.BytesIO(b"mock-pdf"))

        with (
            patch("services.translation.html_translator.get_gemini_api_key", return_value="test-key"),
            patch("main.pdf_to_html_pages", return_value=pages),
            patch(
                "services.translation.html_translator.translate_html_pages",
                side_effect=lambda html_pages: [f"<p>English page {i}</p>" for i in range(1, len(html_pages) + 1)],
            ) as batch_translate,
        ):
            result = await api_translate_pdf_html(upload)

        self.assertEqual(result["total_pages"], 91)
        self.assertEqual(len(result["pages"]), 91)
        self.assertTrue(all(page["translated_html"].strip() for page in result["pages"]))
        self.assertEqual(batch_translate.call_count, 12)


if __name__ == "__main__":
    unittest.main()
