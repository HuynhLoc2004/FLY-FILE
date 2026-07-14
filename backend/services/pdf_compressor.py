import io
import fitz  # PyMuPDF

ULTRA_TARGET_BYTES = 2 * 1024 * 1024
ULTRA_TOLERANCE_BYTES = int(2.6 * 1024 * 1024)


def _save_pdf_optimized(doc: fitz.Document) -> bytes:
    out_io = io.BytesIO()
    doc.save(out_io, garbage=4, deflate=True, use_objstms=1)
    return out_io.getvalue()


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
      - 'ultra': Adaptive compression targeting about 2-2.6 MB while preserving readability.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if level == "ultra":
            native_compressed = _save_pdf_optimized(doc)
            if len(native_compressed) <= ULTRA_TOLERANCE_BYTES:
                return native_compressed

            candidates = [
                (2.35, 84),
                (2.2, 82),
                (2.05, 80),
                (1.9, 78),
                (1.75, 76),
                (1.6, 74),
                (1.45, 72),
                (1.3, 70),
            ]

            best_bytes = native_compressed
            best_distance = abs(len(native_compressed) - ULTRA_TARGET_BYTES)
            for zoom, quality in candidates:
                compressed = _render_pdf_as_image_pdf(doc, zoom, quality)
                compressed_size = len(compressed)
                if compressed_size <= ULTRA_TOLERANCE_BYTES:
                    return compressed

                distance = abs(compressed_size - ULTRA_TARGET_BYTES)
                if best_bytes is None or distance < best_distance:
                    best_bytes = compressed
                    best_distance = distance

            return best_bytes if best_bytes is not None else _render_pdf_as_image_pdf(doc, 1.3, 70)

        if level == "extreme":
            return _render_pdf_as_image_pdf(doc, 1.45, 62)

        return _render_pdf_as_image_pdf(doc, 2.0, 82)
    finally:
        doc.close()
