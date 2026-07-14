import io

import fitz  # PyMuPDF


LOSSLESS_LEVELS = {
    "medium": {
        "garbage": 4,
        "deflate": True,
        "clean": True,
        "use_objstms": 1,
    },
    "extreme": {
        "garbage": 4,
        "deflate": True,
        "clean": True,
        "use_objstms": 1,
    },
    "ultra": {
        "garbage": 4,
        "deflate": True,
        "clean": True,
        "use_objstms": 1,
    },
}

RASTER_LEVELS = {
    "extreme": {
        "zoom": 2.2,      # ~158 DPI, still readable for forms/scans
        "quality": 78,
        "grayscale": True,
    },
    "ultra": {
        "zoom": 2.0,      # ~144 DPI floor to avoid unreadable text
        "quality": 70,
        "grayscale": True,
    },
}


def _save_optimized_copy(doc: fitz.Document, level: str) -> bytes:
    out_io = io.BytesIO()
    doc.save(out_io, **LOSSLESS_LEVELS[level])
    return out_io.getvalue()


def _rasterize_pdf(doc: fitz.Document, level: str) -> bytes:
    profile = RASTER_LEVELS[level]
    new_doc = fitz.open()

    try:
        for page in doc:
            matrix = fitz.Matrix(profile["zoom"], profile["zoom"])
            colorspace = fitz.csGRAY if profile["grayscale"] else fitz.csRGB
            pix = page.get_pixmap(matrix=matrix, colorspace=colorspace, alpha=False)
            img_bytes = pix.tobytes("jpeg", jpg_quality=profile["quality"])

            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)

        out_io = io.BytesIO()
        new_doc.save(out_io, garbage=4, deflate=True)
        return out_io.getvalue()
    finally:
        new_doc.close()


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF while keeping text readable.

    Strategy:
      - medium: lossless structure optimization only, preserving original vector text/images
      - extreme/ultra: try a safe lossless pass first, then use high-DPI grayscale rasterization
        only if it actually produces a smaller file
    """
    normalized_level = (level or "medium").lower()
    if normalized_level not in LOSSLESS_LEVELS:
        normalized_level = "medium"

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        optimized_bytes = _save_optimized_copy(doc, normalized_level)

        if normalized_level == "medium":
            return optimized_bytes if len(optimized_bytes) < len(file_bytes) else file_bytes

        rasterized_bytes = _rasterize_pdf(doc, normalized_level)
        candidates = [file_bytes, optimized_bytes, rasterized_bytes]
        return min(candidates, key=len)
    finally:
        doc.close()
