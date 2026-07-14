import io
import fitz  # PyMuPDF

ULTRA_TARGET_BYTES = 2 * 1024 * 1024


def _render_pdf_as_image_pdf(doc: fitz.Document, zoom: float, quality: int) -> bytes:
    new_doc = fitz.open()

    for page in doc:
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        img_bytes = pix.tobytes("jpeg", jpg_quality=quality)

        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=img_bytes)

    out_io = io.BytesIO()
    new_doc.save(out_io, garbage=4, deflate=True)
    new_doc.close()
    return out_io.getvalue()


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF using PyMuPDF image re-rendering.
    Levels:
      - 'medium': Clear text/table focus, smaller size. (~144 DPI, 82% JPEG quality)
      - 'extreme': Strong compression, still readable. (~104 DPI, 62% JPEG quality)
      - 'ultra': Adaptive compression targeting ~2 MB while preserving readability.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if level == "ultra":
            candidates = [
                (1.75, 74),
                (1.6, 70),
                (1.45, 66),
                (1.35, 62),
                (1.25, 58),
                (1.15, 54),
                (1.05, 50),
                (0.95, 46),
            ]

            best_bytes = None
            for zoom, quality in candidates:
                compressed = _render_pdf_as_image_pdf(doc, zoom, quality)
                if len(compressed) <= ULTRA_TARGET_BYTES:
                    return compressed
                if best_bytes is None or len(compressed) < len(best_bytes):
                    best_bytes = compressed

            return best_bytes if best_bytes is not None else _render_pdf_as_image_pdf(doc, 0.9, 42)

        if level == "extreme":
            return _render_pdf_as_image_pdf(doc, 1.45, 62)

        return _render_pdf_as_image_pdf(doc, 2.0, 82)
    finally:
        doc.close()
