import io
import fitz  # PyMuPDF

ULTRA_TARGET_BYTES = 2 * 1024 * 1024
ULTRA_TOLERANCE_BYTES = int(2.6 * 1024 * 1024)


def _save_pdf_optimized(doc: fitz.Document) -> bytes:
    out_io = io.BytesIO()
    try:
        doc.subset_fonts()
    except Exception:
        pass
    doc.save(
        out_io,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        use_objstms=1,
        compression_effort=100,
    )
    return out_io.getvalue()


def _compress_native_pdf(
    file_bytes: bytes,
    *,
    dpi_threshold: int,
    dpi_target: int,
    quality: int,
    lossy: bool = True,
    lossless: bool = True,
) -> bytes:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        doc.rewrite_images(
            dpi_threshold=dpi_threshold,
            dpi_target=dpi_target,
            quality=quality,
            lossy=lossy,
            lossless=lossless,
            bitonal=False,
            color=True,
            gray=True,
            set_to_gray=False,
        )
        return _save_pdf_optimized(doc)
    finally:
        doc.close()


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF while preserving native text/vector content whenever possible.
    Levels:
      - 'medium': Mild native optimization, prioritizes clarity.
      - 'extreme': Strong native image compression, keeps text sharper than full-page rasterization.
      - 'ultra': Adaptive native compression targeting about 2-2.6 MB when possible.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        base_optimized = _save_pdf_optimized(doc)

        if level == "ultra":
            if len(base_optimized) <= ULTRA_TOLERANCE_BYTES:
                return base_optimized

            candidates = [
                (300, 170, 72),
                (260, 155, 68),
                (240, 145, 64),
                (220, 135, 60),
                (200, 125, 56),
                (180, 118, 52),
            ]

            best_bytes = base_optimized
            best_distance = abs(len(base_optimized) - ULTRA_TARGET_BYTES)
            for dpi_threshold, dpi_target, quality in candidates:
                compressed = _compress_native_pdf(
                    file_bytes,
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=quality,
                )
                compressed_size = len(compressed)
                if compressed_size <= ULTRA_TOLERANCE_BYTES:
                    return compressed

                distance = abs(compressed_size - ULTRA_TARGET_BYTES)
                if best_bytes is None or distance < best_distance:
                    best_bytes = compressed
                    best_distance = distance

            return best_bytes

        if level == "extreme":
            compressed = _compress_native_pdf(
                file_bytes,
                dpi_threshold=240,
                dpi_target=145,
                quality=62,
            )
            return compressed if len(compressed) < len(base_optimized) else base_optimized

        compressed = _compress_native_pdf(
            file_bytes,
            dpi_threshold=300,
            dpi_target=190,
            quality=80,
            lossy=False,
            lossless=True,
        )
        return compressed if len(compressed) < len(base_optimized) else base_optimized
    finally:
        doc.close()
