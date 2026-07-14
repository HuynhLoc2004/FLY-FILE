import unittest

import cv2
import fitz

from services.translation.html_extractor import (
    _extract_colored_mark_assets,
    _extract_preserved_assets,
    _extract_qr_assets,
)


class TranslationAssetTests(unittest.TestCase):
    def test_qr_pixels_are_extracted_as_embeddable_image(self):
        qr = cv2.QRCodeEncoder_create().encode("https://example.test/verify/123")
        qr = cv2.resize(qr, (300, 300), interpolation=cv2.INTER_NEAREST)
        qr = cv2.copyMakeBorder(qr, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
        ok, png = cv2.imencode(".png", qr)
        self.assertTrue(ok)

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(50, 650, 150, 750), stream=png.tobytes())

        assets = _extract_qr_assets(page)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["kind"], "qr")
        self.assertTrue(assets[0]["data_uri"].startswith("data:image/png;base64,"))
        x0, y0, x1, y1 = assets[0]["bbox"]
        self.assertLess(x0, x1)
        self.assertLess(y0, y1)

    def test_blue_signature_is_preserved_as_transparent_image(self):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        shape = page.new_shape()
        shape.draw_bezier((150, 700), (180, 650), (210, 745), (250, 685))
        shape.draw_line((155, 710), (270, 690))
        shape.finish(color=(0.05, 0.25, 0.85), width=3)
        shape.commit()

        assets = _extract_colored_mark_assets(page)

        self.assertGreaterEqual(len(assets), 1)
        self.assertTrue(all(asset["kind"] == "original_mark" for asset in assets))
        self.assertTrue(all(asset["data_uri"].startswith("data:image/png;base64,") for asset in assets))

    def test_small_embedded_black_signature_image_is_preserved(self):
        signature = 255 * __import__("numpy").ones((80, 240), dtype="uint8")
        cv2.line(signature, (10, 60), (220, 20), 0, 3)
        cv2.line(signature, (20, 30), (180, 65), 0, 2)
        ok, png = cv2.imencode(".png", signature)
        self.assertTrue(ok)

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(300, 680, 450, 730), stream=png.tobytes())

        assets = _extract_preserved_assets(page)

        embedded = [asset for asset in assets if asset["kind"] == "original_image"]
        self.assertEqual(len(embedded), 1)
        self.assertTrue(embedded[0]["data_uri"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
