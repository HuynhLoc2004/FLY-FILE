import io
import json
import unittest

import fitz
from fastapi import HTTPException, UploadFile

from main import api_remove_pages


def make_pdf(page_count=4):
    document = fitz.open()
    for page_number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"ORIGINAL PAGE {page_number}")
    content = document.tobytes()
    document.close()
    return content


class RemovePagesEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_removes_selected_pages_and_preserves_original_order(self):
        upload = UploadFile(filename="sample.pdf", file=io.BytesIO(make_pdf()))
        response = await api_remove_pages(
            upload,
            removed_pages=json.dumps([2]),
            page_rotations=json.dumps({"3": 90}),
        )
        body = b"".join([chunk async for chunk in response.body_iterator])
        result = fitz.open(stream=body, filetype="pdf")
        self.assertEqual(result.page_count, 3)
        self.assertIn("ORIGINAL PAGE 1", result[0].get_text())
        self.assertIn("ORIGINAL PAGE 3", result[1].get_text())
        self.assertIn("ORIGINAL PAGE 4", result[2].get_text())
        self.assertEqual(result[1].rotation, 90)
        result.close()

    async def test_rejects_removing_every_page(self):
        upload = UploadFile(filename="sample.pdf", file=io.BytesIO(make_pdf(2)))
        with self.assertRaises(HTTPException) as raised:
            await api_remove_pages(upload, removed_pages="[1, 2]", page_rotations="{}")
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("ít nhất một trang", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
