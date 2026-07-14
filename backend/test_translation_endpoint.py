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


if __name__ == "__main__":
    unittest.main()
