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
    translate_html_page,
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


if __name__ == "__main__":
    unittest.main()
