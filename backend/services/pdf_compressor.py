import io
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Callable, TypeVar

import fitz  # PyMuPDF
from PIL import Image, ImageFilter

MB = 1024 * 1024
Candidate = TypeVar("Candidate")


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
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # A small edge boost keeps scanned text readable after JPEG encoding.
            image = image.filter(ImageFilter.UnsharpMask(radius=0.8, percent=115, threshold=3))
            image_io = io.BytesIO()
            image.save(
                image_io,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
                subsampling=1,
            )
            img_bytes = image_io.getvalue()
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)

        out_io = io.BytesIO()
        out.save(out_io, garbage=4, deflate=True, deflate_images=True, use_objstms=1)
        return out_io.getvalue()
    finally:
        out.close()
        src.close()


@lru_cache(maxsize=1)
def _find_ghostscript_command() -> str | None:
    for name in ("gswin64c", "gswin32c", "gs"):
        command = shutil.which(name)
        if command:
            return command
    return None


def _compress_with_ghostscript(file_bytes: bytes, *, image_dpi: int, jpeg_quality: int) -> bytes | None:
    command = _find_ghostscript_command()
    if not command:
        return None

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "input.pdf"
        output_path = Path(temp_dir) / "output.pdf"
        input_path.write_bytes(file_bytes)

        cmd = [
            command,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-dAutoRotatePages=/None",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            "-dColorImageDownsampleType=/Bicubic",
            f"-dColorImageResolution={image_dpi}",
            "-dGrayImageDownsampleType=/Bicubic",
            f"-dGrayImageResolution={image_dpi}",
            "-dMonoImageDownsampleType=/Subsample",
            f"-dMonoImageResolution={max(200, image_dpi)}",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            f"-dJPEGQ={jpeg_quality}",
            f"-sOutputFile={output_path}",
            str(input_path),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None

        if not output_path.exists():
            return None
        return output_path.read_bytes()


def _pick_best_result(
    original_size: int,
    target_bytes: int,
    min_bytes: int,
    max_bytes: int,
    results: list[bytes],
    fallback_bytes: bytes,
) -> bytes:
    valid = [blob for blob in results if blob and len(blob) < original_size]
    if not valid:
        return fallback_bytes

    in_window = [blob for blob in valid if min_bytes <= len(blob) <= max_bytes]
    if in_window:
        # Results are ordered from highest to lowest visual quality. Once the
        # requested size range is met, preserve quality instead of chasing an
        # exact byte count with a blurrier candidate.
        return in_window[0]

    above_target = [blob for blob in valid if len(blob) > target_bytes]
    if above_target:
        return min(above_target, key=lambda blob: len(blob) - target_bytes)

    below_target = [blob for blob in valid if len(blob) <= target_bytes]
    if below_target:
        return below_target[0]

    return min(valid, key=len)


def _search_ordered_candidates(
    candidates: list[Candidate],
    build: Callable[[Candidate], bytes | None],
    max_bytes: int,
) -> tuple[bytes | None, list[bytes]]:
    """Find the highest-quality candidate under max_bytes with few builds.

    Candidate lists must be ordered from highest quality / largest output to
    lowest quality / smallest output. The first candidate is tested directly
    because it is the common fast path; remaining candidates use binary search.
    """
    if not candidates:
        return None, []

    attempted: dict[int, bytes] = {}

    def run(index: int) -> bytes | None:
        if index in attempted:
            return attempted[index]
        result = build(candidates[index])
        if result:
            attempted[index] = result
        return result

    first = run(0)
    if first is None:
        # This also avoids retrying every Ghostscript setting when it is absent.
        return None, []
    if len(first) <= max_bytes:
        return first, [first]

    low = 1
    high = len(candidates) - 1
    best_index: int | None = None
    while low <= high:
        mid = (low + high) // 2
        result = run(mid)
        if result is None:
            break
        if len(result) <= max_bytes:
            best_index = mid
            high = mid - 1
        else:
            low = mid + 1

    ordered_results = [attempted[index] for index in sorted(attempted)]
    if best_index is not None:
        return attempted[best_index], ordered_results
    return None, ordered_results


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


def _target_size_limit(target_bytes: int, max_bytes: int, original_size: int) -> int:
    # Keep a small tolerance so a near-target, sharper result is not discarded.
    return min(int(target_bytes * 1.08), max_bytes, original_size - 1)


def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF while preserving native text/vector content whenever possible.
    Levels:
      - 'medium': Around 1% of original size, bounded to about 7-10 MB.
      - 'extreme': Around 0.6% of original size, bounded to about 5-7 MB.
      - 'ultra': Around 0.3% of original size, bounded to about 2-4 MB.
    """
    original_size = len(file_bytes)
    medium_target, medium_min, medium_max = _resolve_target_window("medium", original_size)
    extreme_target, extreme_min, extreme_max = _resolve_target_window("extreme", original_size)
    ultra_target, ultra_min, ultra_max = _resolve_target_window("ultra", original_size)
    level_max = {
        "medium": medium_max,
        "extreme": extreme_max,
        "ultra": ultra_max,
    }.get(level, medium_max)

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        # Avoid a full lossless-save pass for large files. Every native
        # compression candidate already performs the same optimized save.
        if original_size <= level_max:
            base_optimized = _save_pdf_optimized(doc)
            if len(base_optimized) >= original_size:
                base_optimized = file_bytes
        else:
            base_optimized = file_bytes

        if level == "ultra":
            size_limit = _target_size_limit(ultra_target, ultra_max, original_size)
            if len(base_optimized) <= size_limit and len(base_optimized) < original_size:
                return base_optimized

            native_candidates = [
                (300, 220, 86),
                (220, 170, 76),
            ]

            native_match, native_results = _search_ordered_candidates(
                native_candidates,
                lambda candidate: _compress_native_pdf(
                    file_bytes,
                    dpi_threshold=candidate[0],
                    dpi_target=candidate[1],
                    quality=candidate[2],
                ),
                size_limit,
            )
            if native_match:
                return native_match

            ghostscript_candidates = [(160, 76)]
            ghostscript_match, ghostscript_results = _search_ordered_candidates(
                ghostscript_candidates,
                lambda candidate: _compress_with_ghostscript(
                    file_bytes,
                    image_dpi=candidate[0],
                    jpeg_quality=candidate[1],
                ),
                size_limit,
            )
            if ghostscript_match:
                return ghostscript_match

            raster_candidates = [(2.0, 74)]
            raster_match, raster_results = _search_ordered_candidates(
                raster_candidates,
                lambda candidate: _render_pdf_as_image_pdf(
                    file_bytes,
                    zoom=candidate[0],
                    quality=candidate[1],
                ),
                size_limit,
            )
            if raster_match:
                return raster_match

            return _pick_best_result(
                original_size,
                ultra_target,
                ultra_min,
                ultra_max,
                [base_optimized, *native_results, *ghostscript_results, *raster_results],
                base_optimized,
            )

        if level == "extreme":
            size_limit = _target_size_limit(extreme_target, extreme_max, original_size)
            if len(base_optimized) <= size_limit and len(base_optimized) < original_size:
                return base_optimized

            native_candidates = [
                (360, 255, 88),
                (280, 190, 80),
            ]
            native_match, native_results = _search_ordered_candidates(
                native_candidates,
                lambda candidate: _compress_native_pdf(
                    file_bytes,
                    dpi_threshold=candidate[0],
                    dpi_target=candidate[1],
                    quality=candidate[2],
                ),
                size_limit,
            )
            if native_match:
                return native_match

            ghostscript_candidates = [(195, 80)]
            ghostscript_match, ghostscript_results = _search_ordered_candidates(
                ghostscript_candidates,
                lambda candidate: _compress_with_ghostscript(
                    file_bytes,
                    image_dpi=candidate[0],
                    jpeg_quality=candidate[1],
                ),
                size_limit,
            )
            if ghostscript_match:
                return ghostscript_match

            raster_candidates = [(2.4, 78)]
            raster_match, raster_results = _search_ordered_candidates(
                raster_candidates,
                lambda candidate: _render_pdf_as_image_pdf(
                    file_bytes,
                    zoom=candidate[0],
                    quality=candidate[1],
                ),
                size_limit,
            )
            if raster_match:
                return raster_match

            return _pick_best_result(
                original_size,
                extreme_target,
                extreme_min,
                extreme_max,
                [base_optimized, *native_results, *ghostscript_results, *raster_results],
                base_optimized,
            )

        size_limit = _target_size_limit(medium_target, medium_max, original_size)
        if len(base_optimized) < original_size and len(base_optimized) <= size_limit:
            return base_optimized

        if original_size <= medium_max:
            return base_optimized

        native_candidates = [
            (420, 315, 93),
            (340, 250, 88),
        ]
        native_match, native_results = _search_ordered_candidates(
            native_candidates,
            lambda candidate: _compress_native_pdf(
                file_bytes,
                dpi_threshold=candidate[0],
                dpi_target=candidate[1],
                quality=candidate[2],
            ),
            size_limit,
        )
        if native_match:
            return native_match

        ghostscript_candidates = [(220, 88)]
        ghostscript_match, ghostscript_results = _search_ordered_candidates(
            ghostscript_candidates,
            lambda candidate: _compress_with_ghostscript(
                file_bytes,
                image_dpi=candidate[0],
                jpeg_quality=candidate[1],
            ),
            size_limit,
        )
        if ghostscript_match:
            return ghostscript_match

        raster_candidates = [(2.2, 90)]
        raster_match, raster_results = _search_ordered_candidates(
            raster_candidates,
            lambda candidate: _render_pdf_as_image_pdf(
                file_bytes,
                zoom=candidate[0],
                quality=candidate[1],
            ),
            size_limit,
        )
        if raster_match:
            return raster_match

        return _pick_best_result(
            original_size,
            medium_target,
            medium_min,
            medium_max,
            [base_optimized, *native_results, *ghostscript_results, *raster_results],
            base_optimized,
        )
    finally:
        doc.close()
