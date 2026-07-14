from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
import io, json, os, logging, traceback

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    # Production installs python-dotenv from requirements.txt. Keeping startup
    # compatible makes diagnostics possible in an older local virtualenv too.
    pass

from services.pdf_merger import merge_pdfs
from services.pdf_compressor import compress_pdf
from services.pdf_page_merger import merge_pages_by_manifest
from services.pdf_to_word import convert_pdf_bytes_to_docx_bytes, parse_pdf_to_blocks, build_docx_from_blocks
from services.word_to_pdf import convert_word_bytes_to_pdf_bytes
from services.translation import build_docx_from_translation
from services.translation.html_extractor import pdf_to_html_pages

# Upload limits: unlimited (no cap applied)

import urllib.parse
def make_safe_filename_header(filename: str) -> str:
    quoted = urllib.parse.quote(filename or "document")
    return f"attachment; filename*=UTF-8''{quoted}"

app = FastAPI(title="Fly FILE API", description="SmartPDF-powered backend for Fly FILE")
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {
        "service": "Fly FILE API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/merge")
async def api_merge(
    files: list[UploadFile] = File(...),
    rotations: str = Form(default="[]"),   # JSON array of ints, one per file
    output_name: str = Form(default=""),
):
    try:
        file_contents = [await f.read() for f in files]
        rot_list = json.loads(rotations) if rotations else []
        merged_pdf = merge_pdfs(file_contents, rot_list if rot_list else None)
        base = output_name.strip() or (files[0].filename or "merged").rsplit(".", 1)[0]
        out_name = f"{base}_merged.pdf"
        return StreamingResponse(
            io.BytesIO(merged_pdf),
            media_type="application/pdf",
            headers={"Content-Disposition": make_safe_filename_header(out_name)}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/merge-pages")
async def api_merge_pages(
    files: list[UploadFile] = File(...),
    manifest: str = Form(...),
    output_name: str = Form(default=""),
):
    """Merge specific pages in a custom order.
    manifest JSON: [{ "file_index": 0, "page": 1, "rotation": 0 }, ...]
    """
    try:
        manifest_data = json.loads(manifest)
        file_contents = [await f.read() for f in files]
        merged_pdf = merge_pages_by_manifest(file_contents, manifest_data)
        base = output_name.strip() or (files[0].filename or "merged").rsplit(".", 1)[0]
        out_name = f"{base}_merged.pdf"
        return StreamingResponse(
            io.BytesIO(merged_pdf),
            media_type="application/pdf",
            headers={"Content-Disposition": make_safe_filename_header(out_name)}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compress")
async def api_compress(
    file: UploadFile = File(...),
    level: str = Form("medium")
):
    try:
        # Validate file type - only PDF allowed
        filename = file.filename or ""
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"File không hợp lệ: '{filename}'. Công cụ Nén PDF chỉ hỗ trợ file PDF (.pdf)."
            )
        
        content = await file.read()
        compressed = compress_pdf(content, level=level)
        return StreamingResponse(
            io.BytesIO(compressed),
            media_type="application/pdf",
            headers={"Content-Disposition": make_safe_filename_header(f"compressed_{file.filename}")}
        )
    except Exception:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=tb)

@app.post("/api/translate-pdf/html")
async def api_translate_pdf_html(
    file: UploadFile = File(...),
):
    """
    HTML-based translation pipeline:
    - Text PDFs: PDF → structured HTML → Gemini translates preserving all tags/styles
    - Scanned/image PDFs: render page → PNG → Gemini Vision (reads layout visually, no OCR errors)
    Paired pages (e.g. tax slip page1+page2) are sent as a combined image to Gemini.
    """
    import base64
    import fitz  # PyMuPDF
    import re as _re
    from concurrent.futures import ThreadPoolExecutor
    from services.translation.html_translator import (
        TranslationConfigurationError,
        TranslationProviderError,
        get_gemini_api_key,
        translate_html_page,
        translate_pdf_page_to_html,
    )

    def _extract_pages_as_pdf_b64(pdf_bytes: bytes, *page_nums: int) -> str:
        """Extract one or more pages from a PDF and return as base64 PDF bytes."""
        src = fitz.open(stream=pdf_bytes, filetype="pdf")
        out = fitz.open()
        for page_num in page_nums:
            out.insert_pdf(src, from_page=page_num - 1, to_page=page_num - 1)
        return base64.b64encode(out.tobytes()).decode()

    try:
        # Fail once with an actionable message instead of returning one red
        # "Translation failed" placeholder for every page.
        get_gemini_api_key()
        content = await file.read()
        pages = pdf_to_html_pages(content)

        # Keep every page independent. Pairing pages through a vision model lets
        # the model recreate (and often alter) fonts, emphasis and preserved QR.
        page_groups = [{"pages": [page], "paired": False} for page in pages]

        def _translate_group(group):
            page_list = group["pages"]
            if group["paired"]:
                b64 = _extract_pages_as_pdf_b64(content, page_list[0]["page_num"], page_list[1]["page_num"])
                translated_html = translate_pdf_page_to_html(b64)
                group_pages = [p["page_num"] for p in page_list]
                lead = {**page_list[0], "translated_html": translated_html,
                        "group_id": page_list[0]["page_num"], "is_group_lead": True, "group_pages": group_pages}
                follower = {**page_list[1], "translated_html": "",
                            "group_id": page_list[0]["page_num"], "is_group_lead": False, "group_pages": group_pages}
                return [lead, follower]
            else:
                p = page_list[0]
                # Translate text nodes only whenever extraction produced usable HTML.
                # This deterministically preserves the source DOM/CSS instead of
                # asking the vision model to guess fonts and emphasis.
                if p.get("html", "").strip():
                    translated_html = translate_html_page(p["html"], is_scanned=p.get("is_scanned", False))
                else:
                    b64 = _extract_pages_as_pdf_b64(content, p["page_num"])
                    translated_html = translate_pdf_page_to_html(b64)

                assets = p.get("preserved_assets", [])
                if assets:
                    from bs4 import BeautifulSoup

                    asset_tags = []
                    page_width = max(float(p.get("width") or 1), 1)
                    max_asset_height = 1.0
                    for asset in assets:
                        x0, y0, x1, y1 = asset["bbox"]
                        max_asset_height = max(max_asset_height, y1 - y0)
                        asset_tags.append(
                            f'<img src="{asset["data_uri"]}" '
                            f'alt="{"QR Code" if asset.get("kind") == "qr" else "Original stamp or signature"}" '
                            'data-preserved-asset="true" '
                            f'style="position:absolute;left:{x0/page_width*100:.3f}%;'
                            f'top:0;width:{(x1-x0)/page_width*100:.3f}%;'
                            'height:auto;z-index:2"/>'
                        )
                    soup = BeautifulSoup(translated_html, "html.parser")
                    flow_page = soup.select_one(".pdf-flow-page")
                    if flow_page is not None:
                        asset_row = BeautifulSoup(
                            f'<div class="preserved-assets-row" style="position:relative;width:100%;'
                            f'height:{max_asset_height:.2f}pt;margin-top:8pt">'
                            + "".join(asset_tags) + "</div>",
                            "html.parser",
                        )
                        flow_page.append(asset_row.div)
                        translated_html = str(soup)
                    else:
                        translated_html = (
                            f'<div style="position:relative;min-height:240mm">{translated_html}'
                            + "".join(asset_tags) + "</div>"
                        )
                public_page = {key: value for key, value in p.items()
                               if key not in {"html", "image_b64", "preserved_assets"}}
                return [{**public_page, "translated_html": translated_html,
                         "group_id": p["page_num"], "is_group_lead": True, "group_pages": [p["page_num"]]}]

        # Translate groups in parallel (max 4 concurrent Gemini calls)
        with ThreadPoolExecutor(max_workers=4) as ex:
            group_results = list(ex.map(_translate_group, page_groups))
        translated_pages = [page for group in group_results for page in group]

        return {
            "original_filename": file.filename or "document.pdf",
            "total_pages": len(translated_pages),
            "mode": "html",
            "pages": translated_pages,
        }
    except TranslationConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except TranslationProviderError as e:
        logger.error("/api/translate-pdf/html provider failed", exc_info=True)
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("/api/translate-pdf/html failed")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"translate_html_failed: {str(e)}")


class DownloadEditedRequest(BaseModel):
    result: dict


def _html_to_pdf_bytes(html: str) -> bytes:
    """Render HTML to PDF, with a portable fallback for missing native libs."""
    import sys

    weasyprint_error = None
    if sys.platform != "win32":
        try:
            from weasyprint import HTML as WeasyHTML
            return WeasyHTML(string=html, base_url=os.path.dirname(__file__)).write_pdf()
        except Exception as exc:
            weasyprint_error = exc
            logger.warning("WeasyPrint unavailable; falling back to xhtml2pdf: %s", exc)

    try:
        from xhtml2pdf import pisa
        from bs4 import BeautifulSoup

        # xhtml2pdf cannot size absolutely-positioned images with percentages.
        # Convert preserved QR coordinates to the printable A4 content box.
        soup = BeautifulSoup(html, "html.parser")
        for image in soup.find_all("img", attrs={"data-preserved-asset": "true"}):
            declarations = {}
            for declaration in image.get("style", "").split(";"):
                name, separator, value = declaration.partition(":")
                if separator:
                    declarations[name.strip()] = value.strip()
            for property_name, reference_points in (("left", 450), ("width", 450), ("top", 730)):
                value = declarations.get(property_name, "")
                if value.endswith("%"):
                    declarations[property_name] = f"{float(value[:-1]) / 100 * reference_points:.2f}pt"
            image["style"] = ";".join(f"{name}:{value}" for name, value in declarations.items())
        portable_html = str(soup)

        output = io.BytesIO()
        status = pisa.CreatePDF(src=portable_html, dest=output, encoding="utf-8")
        if status.err:
            raise RuntimeError(f"xhtml2pdf reported {status.err} rendering error(s)")
        pdf_bytes = output.getvalue()
        if not pdf_bytes.startswith(b"%PDF"):
            raise RuntimeError("PDF renderer returned invalid data")
        return pdf_bytes
    except Exception as exc:
        if weasyprint_error is not None:
            raise RuntimeError(
                f"Không thể tạo PDF (WeasyPrint: {weasyprint_error}; xhtml2pdf: {exc})"
            ) from exc
        raise RuntimeError(f"Không thể tạo PDF: {exc}") from exc


@app.post("/api/translate-pdf/download-pdf")
async def api_translate_pdf_download_pdf(request: DownloadEditedRequest):
    """Convert translated HTML pages to a downloadable A4 PDF."""
    try:
        result = request.result
        pages = result.get("pages", [])

        if not pages:
            raise HTTPException(status_code=400, detail="Bản dịch không có trang để tạo PDF.")

        page_divs = []
        for page in pages:
            html = page.get("translated_html", "")
            page_divs.append(f'<div class="doc-page">{html}</div>')

        full_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  @page {{
    size: A4;
    margin: 18mm 20mm 18mm 22mm;
  }}
  body {{
    font-family: 'Times New Roman', Times, serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #000;
    margin: 0;
    padding: 0;
  }}
  .doc-page {{
    page-break-after: always;
  }}
  .doc-page:last-child {{
    page-break-after: avoid;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 9pt;
    margin-bottom: 6px;
  }}
  td, th {{
    vertical-align: top;
    word-wrap: break-word;
    padding: 3px 5px;
  }}
  p {{
    margin-top: 0;
    margin-bottom: 6px;
  }}
</style>
</head>
<body>{pages_content}</body>
</html>""".format(pages_content="".join(page_divs))

        pdf_bytes = await run_in_threadpool(_html_to_pdf_bytes, full_html)

        base_name = (result.get("original_filename") or "document").rsplit(".", 1)[0]
        out_filename = f"{base_name}_translated.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": make_safe_filename_header(out_filename)},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate-pdf/download-edited-docx")
async def api_translate_pdf_download_edited_docx(request: DownloadEditedRequest):
    try:
        result = request.result
        logger.info(f"download-edited-docx: mode={result.get('mode')}, pages={len(result.get('pages',[]))}")
        docx_bytes = build_docx_from_translation(result)
        out_filename = "translated_edited.docx"
        if "original_filename" in result:
            base_name = result["original_filename"].rsplit(".", 1)[0]
            out_filename = f"{base_name}_translated.docx"

        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": make_safe_filename_header(out_filename)}
        )
    except Exception as e:
        logger.error(f"download-edited-docx failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/api/pdf-to-word")
async def api_pdf_to_word(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Vui lòng chọn file có định dạng PDF.")
        if not content:
            raise HTTPException(status_code=400, detail="File PDF trống.")

        # PDF parsing and OCR are CPU-bound; keep FastAPI's event loop free so
        # other requests remain usable during a large conversion.
        converted_docx = await run_in_threadpool(convert_pdf_bytes_to_docx_bytes, content)
        base_name = (file.filename or "converted").rsplit(".", 1)[0]
        return StreamingResponse(
            io.BytesIO(converted_docx),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": make_safe_filename_header(f"{base_name}.docx")}
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDF to Word conversion failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pdf-to-word/parse")
async def api_pdf_to_word_parse(file: UploadFile = File(...)):
    try:
        content = await file.read()
        parsed_blocks = parse_pdf_to_blocks(content)
        parsed_blocks["original_filename"] = file.filename or "document.pdf"
        return parsed_blocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DownloadEditedWordRequest(BaseModel):
    blocks_data: dict
    original_filename: str = "document.pdf"


@app.post("/api/pdf-to-word/download-edited")
async def api_pdf_to_word_download_edited(request: DownloadEditedWordRequest):
    try:
        docx_bytes = build_docx_from_blocks(request.blocks_data)
        base_name = request.original_filename.rsplit(".", 1)[0]
        out_filename = f"{base_name}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": make_safe_filename_header(out_filename)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Split PDF ─────────────────────────────────────────────────────────────────
@app.post("/api/split")
async def api_split(
    file: UploadFile = File(...),
    ranges: str = Form(...),  # e.g. "1-3,4,5-7" or "1,2,3"
    page_rotations: str = Form(default="{}"),  # JSON object: {"1": 90, "3": 180}
):
    """
    Split a PDF by page ranges. ranges = comma-separated items like "1-3,4,5-7".
    Returns a ZIP containing one PDF per range.
    """
    try:
        import fitz, zipfile
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        total = doc.page_count
        rotations = json.loads(page_rotations or "{}")

        # Parse ranges
        segments = []
        for part in ranges.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                start, end = int(a.strip()) - 1, int(b.strip()) - 1
            else:
                start = end = int(part) - 1
            start = max(0, min(start, total - 1))
            end   = max(0, min(end,   total - 1))
            segments.append((start, end))

        if not segments:
            raise HTTPException(status_code=400, detail="Không có range hợp lệ")

        base = (file.filename or "document").rsplit(".", 1)[0]
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, (s, e) in enumerate(segments, 1):
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=s, to_page=e)
                for offset, source_page_index in enumerate(range(s, e + 1)):
                    extra_rotation = int(rotations.get(str(source_page_index + 1), 0)) % 360
                    if extra_rotation:
                        page = new_doc[offset]
                        page.set_rotation((page.rotation + extra_rotation) % 360)
                pdf_bytes = new_doc.tobytes()
                new_doc.close()
                label = f"trang_{s+1}" if s == e else f"trang_{s+1}-{e+1}"
                zf.writestr(f"{base}_{label}.pdf", pdf_bytes)
        doc.close()
        zip_buf.seek(0)
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": make_safe_filename_header(f"{base}_split.zip")},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PDF → Images ──────────────────────────────────────────────────────────────
@app.post("/api/pdf-to-images")
async def api_pdf_to_images(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    fmt: str = Form("png"),   # "png" or "jpg"
):
    try:
        content = await file.read()
        doc = __import__("fitz").open(stream=content, filetype="pdf")
        zoom = dpi / 72
        mat = __import__("fitz").Matrix(zoom, zoom)
        images = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png" if fmt == "png" else "jpeg")
            import base64
            images.append({
                "page": i + 1,
                "data": base64.b64encode(img_bytes).decode(),
                "mime": "image/png" if fmt == "png" else "image/jpeg",
                "ext": fmt,
            })
        doc.close()
        return {"total": len(images), "images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Images / PDF → PDF ────────────────────────────────────────────────────────
@app.post("/api/images-to-pdf")
async def api_images_to_pdf(files: list[UploadFile] = File(...)):
    try:
        from PIL import Image as PILImage
        pages = []
        for f in files:
            data = await f.read()
            img = PILImage.open(io.BytesIO(data))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            pages.append(img)
        if not pages:
            raise HTTPException(status_code=400, detail="Không có ảnh hợp lệ")
        buf = io.BytesIO()
        pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=converted.pdf"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Word → PDF ────────────────────────────────────────────────────────────────
@app.post("/api/word-to-pdf")
async def api_word_to_pdf(file: UploadFile = File(...)):
    """Convert DOCX to PDF with embedded Vietnamese fonts and adaptive pages."""
    try:
        content = await file.read()
        if not (file.filename or "").lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail="Vui lòng chọn file Word định dạng .docx.")
        pdf_bytes = await run_in_threadpool(convert_word_bytes_to_pdf_bytes, content)

        base = (file.filename or "document").rsplit(".", 1)[0]
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": make_safe_filename_header(f"{base}.pdf")},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Image format conversion (JPG ↔ PNG, etc.) ─────────────────────────────────
@app.post("/api/convert-image")
async def api_convert_image(
    file: UploadFile = File(...),
    to_format: str = Form("png"),   # "png", "jpg", "webp"
):
    try:
        from PIL import Image as PILImage
        content = await file.read()
        img = PILImage.open(io.BytesIO(content)).convert("RGB")
        out = io.BytesIO()
        fmt_map = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}
        pil_fmt = fmt_map.get(to_format.lower(), "PNG")
        img.save(out, format=pil_fmt, quality=95)
        out.seek(0)
        mime = "image/png" if pil_fmt == "PNG" else ("image/webp" if pil_fmt == "WEBP" else "image/jpeg")
        base = (file.filename or "image").rsplit(".", 1)[0]
        ext = "png" if pil_fmt == "PNG" else ("webp" if pil_fmt == "WEBP" else "jpg")
        return StreamingResponse(
            out, media_type=mime,
            headers={"Content-Disposition": make_safe_filename_header(f"{base}.{ext}")},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
