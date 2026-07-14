import unittest

from main import (
    DownloadEditedRequest,
    _html_to_pdf_bytes,
    api_translate_pdf_download_pdf,
)


class TranslationPdfTests(unittest.TestCase):
    def test_html_renderer_returns_a_pdf(self):
        pdf = _html_to_pdf_bytes(
            "<html><body><h1>Translated document</h1>"
            "<p>Full name: NGUYEN VAN AN</p></body></html>"
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


class TranslationPdfEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_renders_gemini_style_tables(self):
        translated_html = """
        <div style="width:100%;color:#1a202c">
          <table style="width:100%;border-collapse:collapse;table-layout:fixed">
            <tr>
              <td style="border:none;word-wrap:break-word">MINISTRY OF PUBLIC SECURITY</td>
              <td style="border:none;text-align:center">SOCIALIST REPUBLIC OF VIETNAM</td>
            </tr>
          </table>
          <p style="text-align:center;font-weight:bold">CRIMINAL RECORD CERTIFICATE NO. 2</p>
          <ol><li>Full name: BUI BAO LONG</li><li>Gender: Male</li></ol>
        </div>
        """
        request = DownloadEditedRequest(result={
            "original_filename": "criminal-record.pdf",
            "pages": [{"page_num": 1, "translated_html": translated_html}],
        })

        response = await api_translate_pdf_download_pdf(request)
        pdf = b"".join([chunk async for chunk in response.body_iterator])

        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
