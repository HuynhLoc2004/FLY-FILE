"""
HTML translator: sends PDF pages directly to Gemini, returns translated HTML.
"""
import re
import logging
import os
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_provider_rate_lock = threading.Lock()
_last_provider_request_at = 0.0

DEFAULT_GEMINI_MODELS = (
    "gemini-2.5-flash",
)


class TranslationConfigurationError(RuntimeError):
    """The translation provider has not been configured."""


class TranslationProviderError(RuntimeError):
    """Every configured translation model failed."""


def get_gemini_api_key(api_key: str | None = None) -> str:
    """Read the key at call time so .env/runtime changes are respected."""
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise TranslationConfigurationError(
            "Chưa cấu hình GEMINI_API_KEY cho backend. "
            "Hãy thêm key vào backend/.env rồi khởi động lại backend."
        )
    return key


def get_gemini_models() -> tuple[str, ...]:
    configured = os.environ.get("GEMINI_MODELS", "")
    models = tuple(model.strip() for model in configured.split(",") if model.strip())
    models = models or DEFAULT_GEMINI_MODELS
    # Flash is substantially faster and more reliable for deterministic
    # translation. Keep it first even if an older deployment configured Pro.
    return tuple(sorted(models, key=lambda model: model != "gemini-2.5-flash"))

VISION_PROMPT = """\
You are a Vietnamese-to-English legal document translator for consular purposes.

Read this Vietnamese PDF and output an HTML fragment that:
1. Translates ALL Vietnamese text to English — nothing left in Vietnamese
2. Reproduces the EXACT same visual layout and structure as the original document
3. Uses inline CSS for all styling

Formatting fidelity rules (mandatory):
- Preserve the original font family, font size, font weight, font style, text decoration,
  alignment, line spacing, and capitalization of every text run
- Bold text stays bold, italic text stays italic, and regular text stays regular
- NEVER make a label, value, heading, or sentence bold/italic unless it is visibly so in the source
- Put the detected dominant font-family on the outermost element and preserve any local font changes
- Do not add text-shadow, box-shadow, filters, outlines, strokes, glow, opacity effects,
  duplicated text, overlaid copies, or decorative effects to any text
- Render every source text item exactly once; do not invent, repeat, or visually layer text

Layout rules:
- Keep the same number of columns, same table structure, same field arrangement as the original
- Borderless layout tables (headers, 2-col fields, signatures): use <table style="width:100%;border-collapse:collapse;table-layout:fixed"> with <td style="border:none;word-wrap:break-word">
- Data tables with visible lines (grade tables, tax detail tables): use <table style="width:100%;border-collapse:collapse;table-layout:fixed"> with <td style="border:1px solid #666;padding:2px 4px;word-wrap:break-word">
- Keep titles in their original structural position; do not move text into or out of table cells
- Do not impose a default font size or style: copy it from the source

Translation rules:
- Use natural, grammatically correct, professional legal English suitable for consular submission
- Preserve the complete meaning, tone, tense, negation, numbers, identifiers, and legal relationships
- Translate by meaning and context, not word-for-word; do not add or omit facts
- Personal names → UPPERCASE Latin no diacritics (NGUYEN VAN AN)
- "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" → "SOCIALIST REPUBLIC OF VIETNAM"
- "Độc lập - Tự do - Hạnh phúc" → "Independence - Freedom - Happiness"
- Dates: write as "August 12th, 2010" or "March 7th, 1968" (month name + ordinal day + year)
- Standard terms: Giấy khai sinh→Birth Certificate, Giấy đăng ký kết hôn→Marriage Certificate,
  Học bạ→School Report, Giấy nộp tiền vào ngân sách nhà nước→State Budget Payment Slip,
  Người nộp thuế→Taxpayer, Thuế GTGT→VAT, Tổng cộng→Total, Họ và tên→Full name,
  Ngày tháng năm sinh→Date of birth, Nơi sinh→Place of birth, Dân tộc→Ethnic group,
  Quốc tịch→Nationality, Chủ tịch→Chairman

Ignore circular stamps/seals — do not include their text.

Before returning, silently proofread the entire translation for English grammar, terminology,
consistency, missing content, duplicated content, and formatting fidelity. Correct every issue found.

Return ONLY the HTML fragment. No markdown, no explanation.
"""


_FORBIDDEN_TEXT_EFFECTS = {
    "text-shadow",
    "text-stroke",
    "text-stroke-color",
    "text-stroke-width",
    "-webkit-text-stroke",
    "-webkit-text-stroke-color",
    "-webkit-text-stroke-width",
    "filter",
}


def sanitize_translated_html(html: str) -> str:
    """Remove generated text effects without changing font or emphasis styles."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for element in soup.find_all(style=True):
        safe_declarations = []
        for declaration in element.get("style", "").split(";"):
            declaration = declaration.strip()
            if not declaration:
                continue
            property_name, separator, _ = declaration.partition(":")
            if separator and property_name.strip().lower() in _FORBIDDEN_TEXT_EFFECTS:
                continue
            safe_declarations.append(declaration)
        if safe_declarations:
            element["style"] = ";".join(safe_declarations)
        else:
            element.attrs.pop("style", None)
    return "".join(str(node) for node in soup.contents)


def _wait_for_provider_slot() -> None:
    """Throttle document calls so large PDFs do not burst through RPM quota."""
    global _last_provider_request_at
    try:
        interval = float(os.environ.get("GEMINI_MIN_REQUEST_INTERVAL_SECONDS", "2.5"))
    except ValueError:
        interval = 2.5
    interval = max(0.0, min(interval, 30.0))
    with _provider_rate_lock:
        remaining = interval - (time.monotonic() - _last_provider_request_at)
        if remaining > 0:
            time.sleep(remaining)
        _last_provider_request_at = time.monotonic()


def _provider_retry_delay(error: Exception, attempt: int) -> float:
    message = str(error)
    match = re.search(r"retry(?:Delay| delay)?[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)s", message, re.I)
    provider_delay = float(match.group(1)) if match else 0.0
    base_delay = min(30.0, 2.0 ** attempt)
    if "429" in message or "RESOURCE_EXHAUSTED" in message:
        base_delay = max(base_delay, 5.0)
    return min(60.0, max(base_delay, provider_delay))


def _call_gemini(model: str, api_key: str, prompt_text: str, retries: int = 5,
                 file_b64: str | None = None, mime_type: str = "application/pdf") -> str:
    import time
    import base64
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=90_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    if file_b64:
        contents = [
            types.Part.from_bytes(data=base64.b64decode(file_b64), mime_type=mime_type),
            types.Part.from_text(text=prompt_text),
        ]
    else:
        contents = [types.Part.from_text(text=prompt_text)]

    config = types.GenerateContentConfig(
        temperature=0.05,
        max_output_tokens=16384,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    last_err = None
    for attempt in range(retries):
        try:
            _wait_for_provider_slot()
            response = client.models.generate_content(model=model, contents=contents, config=config)
            return response.text.strip()
        except Exception as e:
            last_err = e
            if any(c in str(e) for c in ("400", "404", "INVALID_ARGUMENT")):
                raise
            if attempt < retries - 1:
                time.sleep(_provider_retry_delay(e, attempt))
    raise last_err


def translate_pdf_page_to_html(pdf_b64: str, api_key: str | None = None) -> str:
    """Send one PDF page to Gemini, return translated HTML fragment."""
    key = get_gemini_api_key(api_key)
    last_error: Exception | None = None
    for model in get_gemini_models():
        try:
            raw = _call_gemini(model, key, VISION_PROMPT, file_b64=pdf_b64, mime_type="application/pdf")
            result = re.sub(r"^```[a-z]*\s*", "", raw)
            result = re.sub(r"\s*```$", "", result).strip()
            if result and len(result) > 30:
                result = sanitize_translated_html(result)
                logger.info(f"PDF translation succeeded: {model}")
                return result
            last_error = RuntimeError("Gemini returned an empty or incomplete response")
            logger.warning("PDF translate model %s returned no usable HTML", model)
        except Exception as e:
            last_error = e
            logger.warning("PDF translate model %s failed: %s", model, e)

    raise TranslationProviderError(
        "Gemini không thể dịch tài liệu bằng các model đã cấu hình. "
        "Vui lòng kiểm tra API key, quota và GEMINI_MODELS."
    ) from last_error


# Compatibility aliases — kept so existing imports don't break
def translate_scanned_to_html(raw_text: str, api_key: str | None = None) -> str:
    return ""

def translate_scanned_image_to_html(image_b64: str, api_key: str | None = None) -> str:
    return translate_pdf_page_to_html(image_b64, api_key)

def _prepare_html_page(html: str):
    from bs4 import BeautifulSoup, NavigableString

    soup = BeautifulSoup(html, "html.parser")

    # PDF generators frequently split a single word across multiple spans.
    # Translate logical paragraphs/cells, never raw text nodes, otherwise words
    # such as "CERTIFIES" can become separate "CERTIFI" + "ES" translations.
    targets = list(soup.select(".pdf-flow-block p, .pdf-flow-block td, .pdf-flow-block th"))
    if not targets:
        targets = list(soup.find_all(["p", "td", "th"]))
    targets = [target for target in targets if not target.find(["p", "td", "th"])]
    source_segments = [
        re.sub(r"\s+", " ", target.get_text("", strip=False).replace("\xa0", " ")).strip()
        for target in targets
    ]
    non_empty = [(target, segment) for target, segment in zip(targets, source_segments) if segment]
    targets = [item[0] for item in non_empty]
    source_segments = [item[1] for item in non_empty]
    return soup, targets, source_segments


def _translate_segment_batch(source_segments: list[str], key: str) -> list[str]:
    if not source_segments:
        return []

    prompt = f"""You are a professional Vietnamese-to-English legal translator.
Translate the JSON array below as one document, using context across all items.
Return ONLY a valid JSON array with exactly {len(source_segments)} strings in the same order.
Do not merge, split, omit, duplicate, or reorder items. Preserve numbers and identifiers exactly.
Each array item is exactly one source line or one table cell; its translation must remain in that item.
Use natural, grammatically correct legal English. Personal names must be uppercase Latin without
diacritics. Preserve punctuation belonging to each item. Do not output HTML or markdown.

SOURCE SEGMENTS:
{json.dumps(source_segments, ensure_ascii=False)}"""

    last_error: Exception | None = None
    for model in get_gemini_models():
        try:
            raw = _call_gemini(model, key, prompt)
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            translated = json.loads(cleaned)
            if not isinstance(translated, list) or len(translated) != len(source_segments):
                raise ValueError("Gemini returned a different number of text segments")
            if not all(isinstance(item, str) for item in translated):
                raise ValueError("Gemini returned non-text translation segments")
            return translated
        except Exception as exc:
            last_error = exc
            logger.warning("HTML text-node translation model %s failed: %s", model, exc)

    raise TranslationProviderError(
        "Gemini không thể dịch nội dung trong khi giữ nguyên định dạng PDF."
    ) from last_error


def _apply_html_translations(soup, targets, translated: list[str]) -> str:
    from bs4 import NavigableString

    for target, translated_text in zip(targets, translated):
        styled_run = target.find("span", style=True)
        run_style = styled_run.get("style", "") if styled_run else ""
        target.clear()
        if run_style:
            translated_run = soup.new_tag("span")
            translated_run["style"] = run_style
            translated_run.string = translated_text
            target.append(translated_run)
        else:
            target.append(NavigableString(translated_text))
    return sanitize_translated_html("".join(str(node) for node in soup.contents))


def _build_translation_batches(flattened: list[tuple[int, int, str]],
                               max_segments: int,
                               max_chars: int) -> list[list[tuple[int, int, str]]]:
    """Bound requests by item count and prompt size to avoid truncated JSON."""
    batches: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = []
    current_chars = 0
    for item in flattened:
        item_chars = len(item[2])
        if current and (len(current) >= max_segments or current_chars + item_chars > max_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += item_chars
    if current:
        batches.append(current)
    return batches


def translate_html_pages(html_pages: list[str], api_key: str | None = None,
                         max_segments_per_batch: int = 80,
                         max_chars_per_batch: int = 24_000,
                         max_workers: int | None = None) -> list[str]:
    """Translate many pages in small, bounded, fault-isolated batches."""
    key = get_gemini_api_key(api_key)
    prepared = [_prepare_html_page(html) for html in html_pages]
    flattened: list[tuple[int, int, str]] = []
    for page_index, (_soup, _targets, segments) in enumerate(prepared):
        flattened.extend((page_index, segment_index, text)
                         for segment_index, text in enumerate(segments))

    translated_by_page = [[""] * len(item[2]) for item in prepared]
    def translate_batch(batch: list[tuple[int, int, str]]) -> None:
        try:
            translated = _translate_segment_batch([item[2] for item in batch], key)
        except TranslationProviderError:
            # Large JSON arrays can occasionally be truncated. Split only that
            # batch and continue; never discard all previously translated pages.
            if len(batch) <= 20:
                raise
            middle = len(batch) // 2
            translate_batch(batch[:middle])
            translate_batch(batch[middle:])
            return
        for (page_index, segment_index, _source), translated_text in zip(batch, translated):
            translated_by_page[page_index][segment_index] = translated_text

    batches = _build_translation_batches(
        flattened,
        max(1, max_segments_per_batch),
        max(1_000, max_chars_per_batch),
    )
    if max_workers is None:
        try:
            max_workers = int(os.environ.get("GEMINI_TRANSLATION_WORKERS", "1"))
        except ValueError:
            max_workers = 1
    worker_count = min(max(1, max_workers), 4, max(1, len(batches)))

    # Sequential calls are the safe default for API keys with low RPM quota.
    # Paid deployments can explicitly raise GEMINI_TRANSLATION_WORKERS.
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        list(executor.map(translate_batch, batches))

    results = []
    for (soup, targets, _segments), translated in zip(prepared, translated_by_page):
        results.append(_apply_html_translations(soup, targets, translated))
    return results


def translate_html_page(html: str, api_key: str | None = None, is_scanned: bool = False) -> str:
    """Translate one page through the same deterministic batch pipeline."""
    return translate_html_pages([html], api_key=api_key)[0]

def translate_html_document(pages: list[dict], api_key: str | None = None) -> list[dict]:
    return pages  # no longer used
