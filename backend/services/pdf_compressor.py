import io
import fitz  # PyMuPDF

EXTREME_TARGET_BYTES = 5 * 1024 * 1024
EXTREME_MIN_BYTES = int(4.4 * 1024 * 1024)
EXTREME_MAX_BYTES = int(5.6 * 1024 * 1024)
MEDIUM_TARGET_BYTES = int(8.5 * 1024 * 1024)
MEDIUM_MIN_BYTES = 7 * 1024 * 1024
MEDIUM_MAX_BYTES = 10 * 1024 * 1024
ULTRA_TARGET_BYTES = 2 * 1024 * 1024
ULTRA_MIN_BYTES = int(1.75 * 1024 * 1024)
ULTRA_MAX_BYTES = int(2.35 * 1024 * 1024)


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


def _pick_target_profile(file_bytes: bytes, target_bytes: int, min_bytes: int, max_bytes: int, candidates: list[tuple[int, int, int]], fallback_bytes: bytes) -> bytes:
    best_in_window = None
    best_above_target = None
    best_above_distance = None
    best_below_target = None
    best_below_distance = None

    for dpi_threshold, dpi_target, quality in candidates:
        compressed = _compress_native_pdf(
            file_bytes,
            dpi_threshold=dpi_threshold,
            dpi_target=dpi_target,
            quality=quality,
        )
        compressed_size = len(compressed)
        if compressed_size == 0:
            continue

        if min_bytes <= compressed_size <= max_bytes:
            best_in_window = compressed
            break

        if compressed_size > target_bytes:
            distance = compressed_size - target_bytes
            if best_above_target is None or distance < best_above_distance:
                best_above_target = compressed
                best_above_distance = distance
        else:
            distance = target_bytes - compressed_size
            if best_below_target is None or distance < best_below_distance:
                best_below_target = compressed
                best_below_distance = distance

    if best_in_window is not None:
        return best_in_window

    if best_above_target is not None:
        return best_above_target

    if best_below_target is not None and len(best_below_target) >= min_bytes:
        return best_below_target

    return fallback_bytes


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF while preserving native text/vector content whenever possible.
    Levels:
      - 'medium': Mild native compression targeting about 7-10 MB with high clarity.
      - 'extreme': Adaptive native compression targeting about 5 MB.
      - 'ultra': Adaptive native compression targeting about 2 MB.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        base_optimized = _save_pdf_optimized(doc)

        if level == "ultra":
            if ULTRA_MIN_BYTES <= len(base_optimized) <= ULTRA_MAX_BYTES:
                return base_optimized

            candidates = [
                (360, 250, 90),
                (340, 240, 89),
                (320, 230, 88),
                (300, 220, 86),
                (280, 210, 84),
                (260, 200, 82),
                (240, 190, 80),
            ]

            return _pick_target_profile(
                file_bytes,
                ULTRA_TARGET_BYTES,
                ULTRA_MIN_BYTES,
                ULTRA_MAX_BYTES,
                candidates,
                base_optimized,
            )

        if level == "extreme":
            if EXTREME_MIN_BYTES <= len(base_optimized) <= EXTREME_MAX_BYTES:
                return base_optimized

            candidates = [
                (420, 300, 92),
                (400, 285, 90),
                (380, 270, 89),
                (360, 255, 88),
                (340, 240, 86),
                (320, 225, 84),
                (300, 210, 82),
            ]
            return _pick_target_profile(
                file_bytes,
                EXTREME_TARGET_BYTES,
                EXTREME_MIN_BYTES,
                EXTREME_MAX_BYTES,
                candidates,
                base_optimized,
            )

        if MEDIUM_MIN_BYTES <= len(base_optimized) <= MEDIUM_MAX_BYTES:
            return base_optimized

        if len(base_optimized) < MEDIUM_MIN_BYTES:
            return base_optimized

        candidates = [
            (480, 360, 96),
            (460, 345, 95),
            (440, 330, 94),
            (420, 315, 93),
            (400, 300, 92),
            (380, 285, 91),
        ]
        return _pick_target_profile(
            file_bytes,
            MEDIUM_TARGET_BYTES,
            MEDIUM_MIN_BYTES,
            MEDIUM_MAX_BYTES,
            candidates,
            base_optimized,
        )
    finally:
        doc.close()
