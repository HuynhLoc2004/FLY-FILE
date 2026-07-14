import io
import fitz  # PyMuPDF

MB = 1024 * 1024


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


def _render_pdf_as_image_pdf(file_bytes: bytes, *, zoom: float, quality: int) -> bytes:
    src = fitz.open(stream=file_bytes, filetype="pdf")
    out = fitz.open()
    try:
        for page in src:
            pix = page.get_pixmap(
                matrix=fitz.Matrix(zoom, zoom),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            img_bytes = pix.tobytes("jpeg", jpg_quality=quality)
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)

        out_io = io.BytesIO()
        out.save(out_io, garbage=4, deflate=True, deflate_images=True, use_objstms=1)
        return out_io.getvalue()
    finally:
        out.close()
        src.close()


def _pick_target_profile(
    file_bytes: bytes,
    *,
    target_bytes: int,
    min_bytes: int,
    max_bytes: int,
    candidates: list[tuple[int, int, int]],
    fallback_bytes: bytes,
) -> bytes:
    original_size = len(file_bytes)
    best_in_window = None
    best_above_target = None
    best_above_distance = None
    best_below_target = None
    best_below_distance = None
    smallest_reduction = None

    for dpi_threshold, dpi_target, quality in candidates:
        compressed = _compress_native_pdf(
            file_bytes,
            dpi_threshold=dpi_threshold,
            dpi_target=dpi_target,
            quality=quality,
        )
        compressed_size = len(compressed)
        if compressed_size == 0 or compressed_size >= original_size:
            continue

        if smallest_reduction is None or compressed_size < len(smallest_reduction):
            smallest_reduction = compressed

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

    if smallest_reduction is not None:
        return smallest_reduction

    return fallback_bytes


def _pick_smallest_result(original_size: int, results: list[bytes], fallback_bytes: bytes) -> bytes:
    valid = [blob for blob in results if blob and len(blob) < original_size]
    if not valid:
        return fallback_bytes
    return min(valid, key=len)


def _resolve_target_window(level: str, original_size: int) -> tuple[int, int, int]:
    if level == "ultra":
        target = int(original_size * 0.003)
        return (
            min(max(target, 2 * MB), 4 * MB),
            2 * MB,
            4 * MB,
        )

    if level == "extreme":
        target = int(original_size * 0.006)
        return (
            min(max(target, 5 * MB), 7 * MB),
            5 * MB,
            7 * MB,
        )

    target = int(original_size * 0.01)
    return (
        min(max(target, 7 * MB), 10 * MB),
        7 * MB,
        10 * MB,
    )


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF while preserving native text/vector content whenever possible.
    Levels:
      - 'medium': Around 1% of original size, bounded to about 7-10 MB.
      - 'extreme': Around 0.6% of original size, bounded to about 5-7 MB.
      - 'ultra': Around 0.3% of original size, bounded to about 2-4 MB.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        base_optimized = _save_pdf_optimized(doc)
        original_size = len(file_bytes)

        if len(base_optimized) >= original_size:
            base_optimized = file_bytes

        medium_target, medium_min, medium_max = _resolve_target_window("medium", original_size)
        extreme_target, extreme_min, extreme_max = _resolve_target_window("extreme", original_size)
        ultra_target, ultra_min, ultra_max = _resolve_target_window("ultra", original_size)

        if level == "ultra":
            if ultra_min <= len(base_optimized) <= ultra_max and len(base_optimized) < original_size:
                return base_optimized

            native_candidates = [
                (360, 250, 90),
                (340, 240, 89),
                (320, 230, 88),
                (300, 220, 86),
                (280, 210, 84),
                (260, 200, 82),
                (240, 190, 80),
            ]

            native_result = _pick_target_profile(
                file_bytes,
                target_bytes=ultra_target,
                min_bytes=ultra_min,
                max_bytes=ultra_max,
                candidates=native_candidates,
                fallback_bytes=base_optimized,
            )
            if len(native_result) <= ultra_max and len(native_result) < original_size:
                return native_result

            raster_results = [
                _render_pdf_as_image_pdf(file_bytes, zoom=1.9, quality=88),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.7, quality=84),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.55, quality=80),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.4, quality=76),
            ]
            return _pick_smallest_result(original_size, raster_results, native_result)

        if level == "extreme":
            if extreme_min <= len(base_optimized) <= extreme_max and len(base_optimized) < original_size:
                return base_optimized

            native_candidates = [
                (420, 300, 92),
                (400, 285, 90),
                (380, 270, 89),
                (360, 255, 88),
                (340, 240, 86),
                (320, 225, 84),
                (300, 210, 82),
            ]
            native_result = _pick_target_profile(
                file_bytes,
                target_bytes=extreme_target,
                min_bytes=extreme_min,
                max_bytes=extreme_max,
                candidates=native_candidates,
                fallback_bytes=base_optimized,
            )
            if len(native_result) <= extreme_max and len(native_result) < original_size:
                return native_result

            raster_results = [
                _render_pdf_as_image_pdf(file_bytes, zoom=2.2, quality=92),
                _render_pdf_as_image_pdf(file_bytes, zoom=2.0, quality=88),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.8, quality=84),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.65, quality=80),
            ]
            return _pick_smallest_result(original_size, raster_results, native_result)

        if len(base_optimized) < original_size and medium_min <= len(base_optimized) <= medium_max:
            return base_optimized

        if original_size <= medium_max:
            return base_optimized

        native_candidates = [
            (480, 360, 96),
            (460, 345, 95),
            (440, 330, 94),
            (420, 315, 93),
            (400, 300, 92),
            (380, 285, 91),
        ]
        native_result = _pick_target_profile(
            file_bytes,
            target_bytes=medium_target,
            min_bytes=medium_min,
            max_bytes=medium_max,
            candidates=native_candidates,
            fallback_bytes=base_optimized,
        )
        if len(native_result) < original_size and len(native_result) <= medium_max:
            return native_result

        raster_results = [
            _render_pdf_as_image_pdf(file_bytes, zoom=2.5, quality=95),
            _render_pdf_as_image_pdf(file_bytes, zoom=2.3, quality=93),
            _render_pdf_as_image_pdf(file_bytes, zoom=2.1, quality=91),
        ]
        return _pick_smallest_result(original_size, raster_results, native_result)
    finally:
        doc.close()
