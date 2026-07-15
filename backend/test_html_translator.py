import os
import unittest
from unittest.mock import patch

from services.translation.html_translator import (
    DEFAULT_GEMINI_MODELS,
    TranslationConfigurationError,
    TranslationProviderError,
    _build_translation_batches,
    get_gemini_api_key,
    get_gemini_models,
    sanitize_translated_html,
    translate_html_page,
    translate_html_pages,
    translate_pdf_page_to_html,
)


class HtmlTranslatorConfigurationTests(unittest.TestCase):
    def test_large_documents_are_batched_by_character_count(self):
        segments = [(0, index, "x" * 600) for index in range(5)]

        batches = _build_translation_batches(segments, max_segments=80, max_chars=1_000)

        self.assertEqual([len(batch) for batch in batches], [1, 1, 1, 1, 1])

    def test_missing_api_key_has_actionable_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(TranslationConfigurationError, "GEMINI_API_KEY"):
                get_gemini_api_key()

    def test_models_can_be_configured(self):
        with patch.dict(os.environ, {"GEMINI_MODELS": "model-a, model-b"}, clear=True):
            self.assertEqual(get_gemini_models(), ("model-a", "model-b"))

    def test_current_models_are_the_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_gemini_models(), DEFAULT_GEMINI_MODELS)

    def test_sanitizer_removes_text_effects_but_preserves_font_formatting(self):
        html = (
            '<p style="font-family:Arial;font-size:11pt;font-weight:bold;'
            'font-style:italic;text-shadow:1px 1px #000;filter:blur(1px);'
            '-webkit-text-stroke:1px black">Translated text</p>'
        )

        cleaned = sanitize_translated_html(html)

        self.assertIn("font-family:Arial", cleaned)
        self.assertIn("font-size:11pt", cleaned)
        self.assertIn("font-weight:bold", cleaned)
        self.assertIn("font-style:italic", cleaned)
        self.assertNotIn("text-shadow", cleaned)
        self.assertNotIn("filter:", cleaned)
        self.assertNotIn("text-stroke", cleaned)

    @patch("services.translation.html_translator._call_gemini", return_value="")
    def test_empty_responses_raise_instead_of_rendering_failed_pages(self, call_gemini):
        with self.assertRaises(TranslationProviderError):
            translate_pdf_page_to_html("cGRm", api_key="test-key")
        self.assertEqual(call_gemini.call_count, len(DEFAULT_GEMINI_MODELS))

    @patch(
        "services.translation.html_translator._call_gemini",
        return_value='["SOCIALIST REPUBLIC OF VIETNAM", "Independence - Freedom - Happiness"]',
    )
    def test_html_translation_replaces_text_only_and_preserves_exact_styles(self, _call):
        source = (
            '<p style="font-family:Arial;font-size:12pt;font-weight:bold;text-align:center">'
            'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</p>'
            '<p style="font-family:Times New Roman;font-size:9pt;font-style:italic">'
            'Độc lập - Tự do - Hạnh phúc</p>'
        )

        translated = translate_html_page(source, api_key="test-key")

        self.assertIn("font-family:Arial", translated)
        self.assertIn("font-size:12pt", translated)
        self.assertIn("font-weight:bold", translated)
        self.assertIn("font-family:Times New Roman", translated)
        self.assertIn("font-style:italic", translated)
        self.assertIn("SOCIALIST REPUBLIC OF VIETNAM", translated)
        self.assertNotIn("CỘNG HÒA", translated)

    @patch(
        "services.translation.html_translator._call_gemini",
        return_value='["CERTIFIES:"]',
    )
    def test_pdf_split_spans_are_joined_before_translation(self, call_gemini):
        source = (
            '<div class="pdf-flow-block"><p style="text-align:center">'
            '<span style="font-family:Arial;font-weight:bold">XÁC NH</span>'
            '<span style="font-family:Arial;font-weight:bold">ẬN:</span>'
            '</p></div>'
        )

        translated = translate_html_page(source, api_key="test-key")

        prompt = call_gemini.call_args.args[2]
        self.assertIn("XÁC NHẬN:", prompt)
        self.assertIn("CERTIFIES:", translated)
        self.assertNotIn("CERTIFI</span>", translated)

    @patch("services.translation.html_translator._call_gemini")
    def test_multi_page_batches_map_every_segment_back_to_its_page(self, call_gemini):
        call_gemini.side_effect = [
            '["EN page 1 line 1", "EN page 1 line 2"]',
            '["EN page 2 line 1", "EN page 2 line 2"]',
            '["EN page 3 line 1"]',
        ]
        pages = [
            '<div class="pdf-flow-block"><p>VI p1 l1</p><p>VI p1 l2</p></div>',
            '<div class="pdf-flow-block"><p>VI p2 l1</p><p>VI p2 l2</p></div>',
            '<div class="pdf-flow-block"><p>VI p3 l1</p></div>',
        ]

        translated = translate_html_pages(
            pages, api_key="test-key", max_segments_per_batch=2, max_workers=1
        )

        self.assertEqual(call_gemini.call_count, 3)
        self.assertIn("EN page 1 line 1", translated[0])
        self.assertIn("EN page 1 line 2", translated[0])
        self.assertNotIn("EN page 2", translated[0])
        self.assertIn("EN page 2 line 1", translated[1])
        self.assertIn("EN page 2 line 2", translated[1])
        self.assertIn("EN page 3 line 1", translated[2])

    @patch("services.translation.html_translator._call_gemini")
    def test_failed_large_batch_is_split_without_losing_segments(self, call_gemini):
        first_half = [f"EN {index}" for index in range(20)]
        second_half = [f"EN {index}" for index in range(20, 40)]
        call_gemini.side_effect = [
            RuntimeError("truncated provider response"),
            __import__("json").dumps(first_half),
            __import__("json").dumps(second_half),
        ]
        html = '<div class="pdf-flow-block">' + "".join(
            f"<p>VI {index}</p>" for index in range(40)
        ) + "</div>"

        translated = translate_html_pages(
            [html], api_key="test-key", max_segments_per_batch=40, max_workers=1
        )[0]

        self.assertEqual(call_gemini.call_count, 3)
        for index in range(40):
            self.assertIn(f"EN {index}", translated)


if __name__ == "__main__":
    unittest.main()
