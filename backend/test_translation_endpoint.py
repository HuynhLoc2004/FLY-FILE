import io
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from main import api_translate_pdf_html


class TranslationEndpointTests(unittest.IsolatedAsyncioTestCase):
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
        batch_translate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
