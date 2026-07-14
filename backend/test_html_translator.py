import os
import unittest
from unittest.mock import patch

from services.translation.html_translator import (
    DEFAULT_GEMINI_MODELS,
    TranslationConfigurationError,
    TranslationProviderError,
    get_gemini_api_key,
    get_gemini_models,
    sanitize_translated_html,
    translate_pdf_page_to_html,
)


class HtmlTranslatorConfigurationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
