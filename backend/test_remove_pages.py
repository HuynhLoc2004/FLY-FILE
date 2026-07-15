import io
import json
import unittest

import fitz
from fastapi import HTTPException, UploadFile

from main import api_extract_pages, api_remove_pages


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
            insertion_manifest="[]",
            insert_files=None,
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
            await api_remove_pages(
                upload, removed_pages="[1, 2]", page_rotations="{}",
                insertion_manifest="[]", insert_files=None,
            )
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("ít nhất một trang", raised.exception.detail)

    async def test_inserts_one_page_at_removed_position(self):
        upload = UploadFile(filename="sample.pdf", file=io.BytesIO(make_pdf(3)))
        replacement = UploadFile(filename="replacement.pdf", file=io.BytesIO(make_pdf(1)))
        response = await api_remove_pages(
            upload,
            removed_pages="[2]",
            page_rotations="{}",
            insertion_manifest='[{"position": 2, "file_index": 0}]',
            insert_files=[replacement],
        )
        body = b"".join([chunk async for chunk in response.body_iterator])
        result = fitz.open(stream=body, filetype="pdf")
        self.assertEqual(result.page_count, 3)
        self.assertIn("ORIGINAL PAGE 1", result[0].get_text())
        self.assertIn("ORIGINAL PAGE 1", result[1].get_text())
        self.assertIn("ORIGINAL PAGE 3", result[2].get_text())
        result.close()

    async def test_extracts_cut_pages_as_a_new_pdf(self):
        upload = UploadFile(filename="sample.pdf", file=io.BytesIO(make_pdf(4)))
        response = await api_extract_pages(upload, pages="[2, 4]")
        body = b"".join([chunk async for chunk in response.body_iterator])
        result = fitz.open(stream=body, filetype="pdf")
        self.assertEqual(result.page_count, 2)
        self.assertIn("ORIGINAL PAGE 2", result[0].get_text())
        self.assertIn("ORIGINAL PAGE 4", result[1].get_text())
        result.close()


if __name__ == "__main__":
    unittest.main()
