import io
import shutil
import subprocess
import tempfile
from pathlib import Path

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


def _pick_smallest_result(original_size: int, results: list[bytes], fallback_bytes: bytes) -> bytes:
    valid = [blob for blob in results if blob and len(blob) < original_size]
    if not valid:
        return fallback_bytes
    return min(valid, key=len)


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
        return min(in_window, key=lambda blob: abs(len(blob) - target_bytes))

    above_target = [blob for blob in valid if len(blob) > target_bytes]
    if above_target:
        return min(above_target, key=lambda blob: len(blob) - target_bytes)

    below_target = [blob for blob in valid if len(blob) <= target_bytes]
    if below_target:
        return min(below_target, key=lambda blob: target_bytes - len(blob))

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

            native_results = [
                _compress_native_pdf(
                    file_bytes,
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=quality,
                )
                for dpi_threshold, dpi_target, quality in native_candidates
            ]
            ghostscript_results = [
                _compress_with_ghostscript(file_bytes, image_dpi=180, jpeg_quality=86),
                _compress_with_ghostscript(file_bytes, image_dpi=160, jpeg_quality=82),
                _compress_with_ghostscript(file_bytes, image_dpi=145, jpeg_quality=78),
            ]
            raster_results = [
                _render_pdf_as_image_pdf(file_bytes, zoom=1.9, quality=88),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.7, quality=84),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.55, quality=80),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.4, quality=76),
            ]
            return _pick_best_result(
                original_size,
                ultra_target,
                ultra_min,
                ultra_max,
                [base_optimized, *native_results, *ghostscript_results, *raster_results],
                base_optimized,
            )

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
            native_results = [
                _compress_native_pdf(
                    file_bytes,
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=quality,
                )
                for dpi_threshold, dpi_target, quality in native_candidates
            ]
            ghostscript_results = [
                _compress_with_ghostscript(file_bytes, image_dpi=220, jpeg_quality=90),
                _compress_with_ghostscript(file_bytes, image_dpi=200, jpeg_quality=86),
                _compress_with_ghostscript(file_bytes, image_dpi=180, jpeg_quality=82),
            ]
            raster_results = [
                _render_pdf_as_image_pdf(file_bytes, zoom=2.2, quality=92),
                _render_pdf_as_image_pdf(file_bytes, zoom=2.0, quality=88),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.8, quality=84),
                _render_pdf_as_image_pdf(file_bytes, zoom=1.65, quality=80),
            ]
            return _pick_best_result(
                original_size,
                extreme_target,
                extreme_min,
                extreme_max,
                [base_optimized, *native_results, *ghostscript_results, *raster_results],
                base_optimized,
            )

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
        native_results = [
            _compress_native_pdf(
                file_bytes,
                dpi_threshold=dpi_threshold,
                dpi_target=dpi_target,
                quality=quality,
            )
            for dpi_threshold, dpi_target, quality in native_candidates
        ]
        ghostscript_results = [
            _compress_with_ghostscript(file_bytes, image_dpi=260, jpeg_quality=92),
            _compress_with_ghostscript(file_bytes, image_dpi=240, jpeg_quality=90),
            _compress_with_ghostscript(file_bytes, image_dpi=220, jpeg_quality=88),
        ]
        raster_results = [
            _render_pdf_as_image_pdf(file_bytes, zoom=2.5, quality=95),
            _render_pdf_as_image_pdf(file_bytes, zoom=2.3, quality=93),
            _render_pdf_as_image_pdf(file_bytes, zoom=2.1, quality=91),
        ]
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
