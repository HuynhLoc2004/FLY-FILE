"""Word to PDF conversion with embedded Unicode fonts and wide-table support."""

import io
import os
import threading
from pathlib import Path

import mammoth
from bs4 import BeautifulSoup
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
from xhtml2pdf import default as pisa_default


_FONT_LOCK = threading.Lock()


def _unicode_font_path() -> Path | None:
    """Find a font that contains Vietnamese glyphs on local and Linux hosts."""
    configured = os.getenv("PDF_FONT_PATH")
    candidates = [
        Path(configured) if configured else None,
        Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf",
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def _maximum_table_columns(body_html: str) -> int:
    soup = BeautifulSoup(body_html, "html.parser")
    maximum = 0
    for row in soup.select("table tr"):
        columns = 0
        for cell in row.find_all(["td", "th"], recursive=False):
            try:
                columns += max(1, int(cell.get("colspan", 1)))
            except (TypeError, ValueError):
                columns += 1
        maximum = max(maximum, columns)
    return maximum


def _register_unicode_font() -> bool:
    """Register the TTF directly, avoiding xhtml2pdf's lossy base-14 fallback."""
    font = _unicode_font_path()
    if font is None:
        return False
    with _FONT_LOCK:
        if "FlyUnicode" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("FlyUnicode", str(font)))
            pdfmetrics.registerFontFamily(
                "FlyUnicode",
                normal="FlyUnicode",
                bold="FlyUnicode",
                italic="FlyUnicode",
                boldItalic="FlyUnicode",
            )
        # pisaContext copies this mapping for every conversion.
        pisa_default.DEFAULT_FONT["flyunicode"] = "FlyUnicode"
    return True


def _html_document(body_html: str) -> str:
    max_columns = _maximum_table_columns(body_html)
    is_wide = max_columns >= 8
    is_extra_wide = max_columns >= 12
    page_size = "A3 landscape" if is_extra_wide else "A4 landscape" if is_wide else "A4 portrait"
    page_margin = "8mm" if is_extra_wide else "10mm" if is_wide else "20mm 18mm 18mm 22mm"
    table_font_size = "6.5pt" if is_extra_wide else "7pt" if is_wide else "10pt"
    cell_padding = "1.5pt" if is_extra_wide else "2pt" if is_wide else "4pt 5pt"

    family = '"DejaVu Sans", "Liberation Sans", Arial, sans-serif'
    if _unicode_font_path():
        family = '"FlyUnicode", "DejaVu Sans", "Liberation Sans", Arial, sans-serif'

    css = (
        f'@page{{size:{page_size};margin:{page_margin};}}'
        + f'html,body{{font-family:{family};font-size:11pt;line-height:1.35;color:#000;}}'
        + 'body{margin:0;padding:0;}p{margin:0 0 7pt 0;}'
        + f'h1,h2,h3,h4,h5,h6{{font-family:{family};page-break-after:avoid;margin:12pt 0 6pt;}}'
        + f'table{{width:100%;border-collapse:collapse;margin:0 0 8pt;font-size:{table_font_size};}}'
        + f'td,th{{border:1px solid #000;padding:{cell_padding};vertical-align:top;'
          'overflow-wrap:anywhere;word-break:break-word;hyphens:auto;}'
        + 'tr{page-break-inside:avoid;}img{max-width:100%;height:auto;}'
        + 'ul,ol{margin:0 0 7pt 18pt;padding:0;}li{margin-bottom:2pt;}'
    )
    return (
        '<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">'
        f'<style>{css}</style></head><body>{body_html}</body></html>'
    )


def convert_word_bytes_to_pdf_bytes(word_bytes: bytes) -> bytes:
    if not word_bytes:
        raise ValueError("File Word trống.")
    if not _register_unicode_font():
        raise RuntimeError(
            "Máy chủ chưa có font Unicode. Hãy cài DejaVu Sans hoặc cấu hình PDF_FONT_PATH."
        )
    result = mammoth.convert_to_html(io.BytesIO(word_bytes))
    document_html = _html_document(result.value)
    output = io.BytesIO()
    status = pisa.CreatePDF(
        io.StringIO(document_html),
        dest=output,
        encoding="utf-8",
    )
    if status.err:
        raise RuntimeError(f"Không thể tạo PDF (mã lỗi {status.err}).")
    return output.getvalue()
