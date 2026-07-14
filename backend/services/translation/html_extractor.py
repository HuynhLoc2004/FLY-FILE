"""
PDF → HTML Extractor (layout-preserving).

Converts each PDF page to clean HTML that preserves:
- Font sizes (PDF points → CSS pt)
- Bold / italic
- Text alignment (left / center / right)
- Vertical spacing between blocks (margin-top heuristic)
- Tables (converted to <table> elements)

Uses pymupdf_layout when available for improved block grouping.
Falls back to PyMuPDF dict extraction otherwise.
For image-only (scanned) PDFs, uses RapidOCR.

The resulting HTML is sent verbatim to Gemini for translation.
"""
import html as html_lib
import fitz  # PyMuPDF

# pymupdf-layout is installed — suppress the advisory log message.
# We use PyMuPDF's native dict extraction which is already accurate for legal docs.
try:
    from pymupdf.layout import DocumentLayoutAnalyzer  # noqa: F401 — suppress warning
    _HAS_LAYOUT = True
except ImportError:
    _HAS_LAYOUT = False

import logging as _logging
_logging.getLogger("pymupdf").setLevel(_logging.ERROR)


# ── helpers ───────────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    return html_lib.escape(text, quote=False)


def _css_font_family(pdf_font_name: str) -> str:
    """Map embedded PDF font names to browser-safe families."""
    name = (pdf_font_name or "").lower()
    if "times" in name or "serif" in name:
        return "'Times New Roman',Times,serif"
    if "arial" in name or "helvetica" in name or "sans" in name:
        return "Arial,Helvetica,sans-serif"
    if "courier" in name or "mono" in name:
        return "'Courier New',Courier,monospace"
    return "'Times New Roman',Times,serif"


def _extract_qr_assets(page: fitz.Page, zoom: float = 3.0) -> list[dict]:
    """Detect QR regions in the original page and preserve their real pixels."""
    try:
        import base64
        import cv2
        import numpy as np

        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = cv2.imdecode(np.frombuffer(pix.tobytes("png"), dtype=np.uint8), cv2.IMREAD_COLOR)
        found, points = cv2.QRCodeDetector().detectMulti(image)
        if not found or points is None:
            return []

        assets = []
        height, width = image.shape[:2]
        for corners in points:
            xs = corners[:, 0]
            ys = corners[:, 1]
            padding = max(8, int(min(xs.max() - xs.min(), ys.max() - ys.min()) * 0.08))
            x0 = max(0, int(xs.min()) - padding)
            y0 = max(0, int(ys.min()) - padding)
            x1 = min(width, int(xs.max()) + padding)
            y1 = min(height, int(ys.max()) + padding)
            crop = image[y0:y1, x0:x1]
            ok, encoded = cv2.imencode(".png", crop)
            if not ok or crop.size == 0:
                continue
            assets.append({
                "kind": "qr",
                "data_uri": "data:image/png;base64," + base64.b64encode(encoded.tobytes()).decode(),
                "bbox": [x0 / zoom, y0 / zoom, x1 / zoom, y1 / zoom],
            })
        return assets
    except Exception as exc:
        _logging.getLogger(__name__).warning("QR extraction failed: %s", exc)
        return []


def _extract_colored_mark_assets(page: fitz.Page, zoom: float = 3.0) -> list[dict]:
    """Preserve red/blue stamps and handwritten signatures as transparent PNGs."""
    try:
        import base64
        import cv2
        import numpy as np

        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = cv2.imdecode(np.frombuffer(pix.tobytes("png"), dtype=np.uint8), cv2.IMREAD_COLOR)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        red = cv2.inRange(hsv, np.array([0, 65, 35]), np.array([12, 255, 255]))
        red |= cv2.inRange(hsv, np.array([165, 65, 35]), np.array([179, 255, 255]))
        blue = cv2.inRange(hsv, np.array([85, 55, 30]), np.array([145, 255, 255]))
        color_mask = red | blue

        # Join nearby pen/stamp strokes into visual regions without retaining
        # the white page behind them.
        joined = cv2.dilate(color_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 11)))
        contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = image.shape[:2]
        assets = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 18 or h < 10 or w * h < 450 or w * h > width * height * 0.20:
                continue
            padding = max(5, int(min(w, h) * 0.08))
            x0, y0 = max(0, x - padding), max(0, y - padding)
            x1, y1 = min(width, x + w + padding), min(height, y + h + padding)
            alpha = color_mask[y0:y1, x0:x1]
            if cv2.countNonZero(alpha) < 35:
                continue
            crop = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2BGRA)
            crop[:, :, 3] = alpha
            ok, encoded = cv2.imencode(".png", crop)
            if not ok:
                continue
            assets.append({
                "kind": "original_mark",
                "data_uri": "data:image/png;base64," + base64.b64encode(encoded.tobytes()).decode(),
                "bbox": [x0 / zoom, y0 / zoom, x1 / zoom, y1 / zoom],
            })
        return assets
    except Exception as exc:
        _logging.getLogger(__name__).warning("Stamp/signature extraction failed: %s", exc)
        return []


def _extract_preserved_assets(page: fitz.Page) -> list[dict]:
    """Return original non-translatable visual marks from a PDF page."""
    import base64

    assets = _extract_qr_assets(page) + _extract_colored_mark_assets(page)
    page_area = max(page.rect.width * page.rect.height, 1)
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        if block.get("type") != 1 or not block.get("image"):
            continue
        bbox = list(block.get("bbox", []))
        if len(bbox) != 4:
            continue
        area = max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])
        # Preserve small embedded marks/logos/signatures, never a full-page scan.
        if area < 25 or area / page_area > 0.20:
            continue
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        if any(a["bbox"][0] <= cx <= a["bbox"][2] and a["bbox"][1] <= cy <= a["bbox"][3]
               for a in assets):
            continue
        extension = str(block.get("ext") or "png").lower()
        mime_extension = "jpeg" if extension in {"jpg", "jpeg"} else extension
        assets.append({
            "kind": "original_image",
            "data_uri": f"data:image/{mime_extension};base64," + base64.b64encode(block["image"]).decode(),
            "bbox": bbox,
        })
    return assets


def _inside_preserved_asset(bbox: list, assets: list[dict]) -> bool:
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return any(
        asset["bbox"][0] <= cx <= asset["bbox"][2]
        and asset["bbox"][1] <= cy <= asset["bbox"][3]
        for asset in assets
    )


def _is_inside_table(bbox: list, table_bboxes: list) -> bool:
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for tx0, ty0, tx1, ty1 in table_bboxes:
        if tx0 - 5 <= cx <= tx1 + 5 and ty0 - 5 <= cy <= ty1 + 5:
            return True
    return False


def _alignment(x0: float, block_w: float, page_w: float, is_large: bool) -> str:
    margin_l = x0
    margin_r = page_w - (x0 + block_w)
    mid_block = x0 + block_w / 2
    mid_page = page_w / 2

    if x0 > mid_page * 1.1 and block_w < page_w * 0.5:
        return "right"
    if abs(margin_l - margin_r) < page_w * 0.07 and block_w < page_w * 0.75:
        return "center"
    if is_large and abs(mid_block - mid_page) < page_w * 0.08:
        return "center"
    return "left"


def _gap_to_margin(gap_pt: float) -> int:
    """Convert vertical gap (PDF points) to CSS margin-top in pixels."""
    if gap_pt < 2:
        return 0
    if gap_pt < 6:
        return 4
    if gap_pt < 12:
        return 8
    if gap_pt < 20:
        return 14
    if gap_pt < 35:
        return 20
    return 30


def _table_to_html(grid: list, font_size: float = 11.0) -> str:
    """Convert a 2-D grid of strings to an HTML <table>."""
    rows_html = []
    for row in grid:
        cells_html = []
        for cell in row:
            text = _escape((cell or "").strip())
            cells_html.append(
                f'<td style="border:1px solid #999;padding:5px 8px;'
                f'font-size:{font_size:.0f}pt;vertical-align:top;'
                f'white-space:pre-wrap;">{text}</td>'
            )
        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
    return (
        '<table style="width:100%;border-collapse:collapse;'
        'border:1px solid #999;margin:6px 0;">'
        "<tbody>" + "".join(rows_html) + "</tbody></table>"
    )


# ── main entry point ──────────────────────────────────────────────────────────

def _ocr_page_to_elements(page: fitz.Page, page_w: float, preserved_assets: list[dict] | None = None) -> list[tuple]:
    """
    Run RapidOCR on a scanned page and return (y0, html_str, y1) elements.
    Each OCR result is a text box; we map bounding box position to alignment.
    """
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return []

    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")

    ocr = RapidOCR()
    result, _ = ocr(img_bytes)
    if not result:
        return []

    # Group OCR boxes into logical lines by proximity of y-centers
    # Sort by y0 then group into rows within 8px of each other
    boxes = []
    for box, text, conf in result:
        if not text.strip():
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        x0 = min(xs) / zoom
        y0 = min(ys) / zoom
        x1 = max(xs) / zoom
        y1 = max(ys) / zoom
        if _inside_preserved_asset([x0, y0, x1, y1], preserved_assets or []):
            continue
        h = y1 - y0
        font_size = round(h * 0.70, 1)  # heuristic: 70% of box height
        bold = font_size > 13.5
        boxes.append((y0, x0, x1, y1, font_size, bold, text.strip()))

    boxes.sort(key=lambda b: (b[0], b[1]))

    # Group into rows (same horizontal line)
    rows: list[list] = []
    current_row: list = []
    prev_y_mid = None
    for box in boxes:
        y0, x0, x1, y1, fs, bold, text = box
        y_mid = (y0 + y1) / 2
        if prev_y_mid is None or abs(y_mid - prev_y_mid) < (y1 - y0) * 0.6:
            current_row.append(box)
            prev_y_mid = y_mid
        else:
            if current_row:
                rows.append(current_row)
            current_row = [box]
            prev_y_mid = y_mid
    if current_row:
        rows.append(current_row)

    elements: list[tuple] = []
    for row in rows:
        row.sort(key=lambda b: b[1])  # sort by x0
        row_y0 = min(b[0] for b in row)
        row_y1 = max(b[3] for b in row)
        row_x0 = min(b[1] for b in row)
        row_x1 = max(b[2] for b in row)
        row_w = row_x1 - row_x0
        avg_fs = sum(b[4] for b in row) / len(row)
        is_large = avg_fs > 13.0

        align = _alignment(row_x0, row_w, page_w, is_large)

        parts = []
        for _, _, _, _, fs, bold, text in row:
            style = f"font-size:{fs:.1f}pt;"
            if bold:
                style += "font-weight:bold;"
            parts.append(f'<span style="{style}">{_escape(text)}</span>')

        p_style = f"text-align:{align};margin:0;line-height:1.55;"
        elements.append((
            row_y0,
            f'<p style="{p_style}">{"&nbsp;&nbsp;".join(parts)}</p>',
            row_y1,
            [row_x0, row_y0, row_x1, row_y1],
        ))

    return elements


def pdf_page_to_html(page: fitz.Page, preserved_assets: list[dict] | None = None) -> str:
    """
    Convert one fitz.Page to a self-contained HTML fragment.
    - For selectable-text PDFs: uses PyMuPDF dict extraction (preserves exact font sizes/bold).
    - For image-only (scanned) PDFs: falls back to RapidOCR with heuristic font sizing.
    The fragment is sent to Gemini for translation.
    """
    page_w = page.rect.width

    # ── 1. Detect tables ─────────────────────────────────────────────────────
    tables = page.find_tables()
    table_bboxes = [list(t.bbox) for t in tables]

    table_elements: list[tuple] = []  # (y0, html_str, y1)
    for t in tables:
        grid = t.extract()
        t_html = _table_to_html(grid)
        table_elements.append((t.bbox[1], t_html, t.bbox[3], list(t.bbox)))

    # ── 2. Check if page has extractable text via dict mode ───────────────────
    # NOTE: get_text("text") fails for custom-encoded Vietnamese fonts.
    # get_text("dict") is more reliable — it processes each span individually.
    raw_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES)
    has_native_text = any("lines" in b and any(
        sp["text"].strip() for ln in b["lines"] for sp in ln["spans"]
    ) for b in raw_dict["blocks"])

    block_elements: list[tuple] = []
    is_scanned = False    # True = no native text (pure image, OCR needed)
    scale = 1.0           # font-size normalisation factor

    if not has_native_text:
        # ── Pure image page: run RapidOCR ────────────────────────────────────
        block_elements = _ocr_page_to_elements(page, page_w, preserved_assets)
        is_scanned = True
    else:
        raw = raw_dict  # reuse already-fetched dict

        all_sizes: list[float] = []
        for blk in raw["blocks"]:
            if "lines" not in blk:
                continue
            for ln in blk["lines"]:
                for sp in ln["spans"]:
                    if sp["text"].strip():
                        all_sizes.append(sp["size"])
        avg_size = (sum(all_sizes) / len(all_sizes)) if all_sizes else 11.0

        # Detect scan-embedded text layer: font sizes inflated > 20 pt on average
        # (scanners embed OCR text at high-res coordinates).
        # We normalise so body text ≈ 11 pt and headings scale proportionally.
        TARGET_BODY = 11.0
        if avg_size > 20.0:
            is_scanned = True
            scale = TARGET_BODY / avg_size   # e.g. avg=28pt → scale=0.39

        for blk in raw["blocks"]:
            if "lines" not in blk:
                continue
            bbox = blk["bbox"]
            if _is_inside_table(bbox, table_bboxes):
                continue
            if _inside_preserved_asset(bbox, preserved_assets or []):
                continue

            lines_html: list[str] = []
            max_size = 0.0

            for ln in blk["lines"]:
                span_parts: list[str] = []
                for sp in ln["spans"]:
                    t = sp["text"]
                    if not t:
                        continue
                    raw_size = sp["size"]
                    # Apply normalisation and cap extremes
                    size = round(min(raw_size * scale, 28.0), 1)
                    # Floor to avoid sub-6pt invisible text (e.g. watermarks)
                    if size < 6.0:
                        size = 6.0
                    if size > max_size:
                        max_size = size
                    bold = bool(sp["flags"] & 16)
                    italic = bool(sp["flags"] & 2)

                    style = f"font-family:{_css_font_family(sp.get('font', ''))};font-size:{size:.1f}pt;"
                    if bold:
                        style += "font-weight:bold;"
                    if italic:
                        style += "font-style:italic;"

                    span_parts.append(f'<span style="{style}">{_escape(t)}</span>')

                if span_parts:
                    lines_html.append("".join(span_parts))

            if not lines_html:
                continue

            x0, y0, x1, y1 = bbox
            block_w = x1 - x0
            is_large = max_size > TARGET_BODY * 1.2
            align = _alignment(x0, block_w, page_w, is_large)

            content = "<br/>".join(lines_html)
            p_style = f"text-align:{align};margin:0;line-height:1.6;"
            block_elements.append((y0, f'<p style="{p_style}">{content}</p>', y1, list(bbox)))

    # ── 3. Merge tables + text, sort by y0 ───────────────────────────────────
    all_elems: list[tuple] = block_elements + table_elements
    all_elems.sort(key=lambda e: (e[0], e[3][0]))

    # ── 4. Assemble responsive source rows ────────────────────────────────────
    # Blocks sharing a visual line stay left/right in one CSS grid row. Rows
    # remain in normal flow, so longer English expands the row and pushes all
    # later content down instead of overlapping it.
    rows: list[list[tuple]] = []
    for element in all_elems:
        bbox = element[3]
        if rows:
            current = rows[-1]
            row_y0 = min(item[3][1] for item in current)
            row_y1 = max(item[3][3] for item in current)
            elem_h = max(bbox[3] - bbox[1], 1)
            row_h = max(row_y1 - row_y0, 1)
            vertical_overlap = max(0.0, min(row_y1, bbox[3]) - max(row_y0, bbox[1]))
            same_band = (
                abs(bbox[1] - row_y0) <= 7
                or vertical_overlap >= min(elem_h, row_h) * 0.55
            )
            horizontal_collision = any(
                min(bbox[2], item[3][2]) - max(bbox[0], item[3][0]) > 2
                for item in current
            )
            if same_band and not horizontal_collision:
                current.append(element)
                continue
        rows.append([element])

    row_parts: list[str] = []
    previous_source_y1 = 0.0
    for row in rows:
        row.sort(key=lambda item: item[3][0])
        row_y0 = min(item[3][1] for item in row)
        row_y1 = max(item[3][3] for item in row)
        source_gap = max(0.0, row_y0 - previous_source_y1)
        margin_top = min(source_gap, 30.0)
        cells = []
        multiple_columns = len(row) > 1
        for _y0, elem_html, _y1, bbox in row:
            x0, _top, x1, _bottom = bbox
            center = (x0 + x1) / 2 / page_w
            source_width = (x1 - x0) / page_w
            if multiple_columns:
                cell_style = "min-width:0"
            elif source_width >= 0.55 or 0.35 <= center <= 0.65:
                cell_style = "width:100%;min-width:0"
            elif center > 0.65:
                cell_style = "width:50%;min-width:0;margin-left:auto"
            else:
                cell_style = "width:50%;min-width:0;margin-right:auto"
            cells.append(
                f'<div class="pdf-flow-block" style="{cell_style};overflow-wrap:break-word">'
                f'{elem_html}</div>'
            )
        row_layout = (
            f'display:grid;grid-template-columns:repeat({len(row)},minmax(0,1fr));column-gap:18pt;'
            if multiple_columns else "display:block;"
        )
        row_parts.append(
            f'<div class="pdf-flow-row" style="{row_layout}'
            f'align-items:start;width:100%;margin-top:{margin_top:.2f}pt">'
            + "".join(cells) + "</div>"
        )
        previous_source_y1 = max(previous_source_y1, row_y1)

    html_out = '<div class="pdf-flow-page" style="width:100%;overflow:visible">' + "\n".join(row_parts) + "</div>"
    return html_out, is_scanned


def pdf_to_html_pages(pdf_bytes: bytes) -> list[dict]:
    """
    Convert all pages of a PDF to HTML.
    Returns a list of dicts:
      { "page_num": int, "html": str, "width": float, "height": float,
        "is_scanned": bool, "image_b64": str (only for scanned pages) }
    """
    import base64
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        preserved_assets = _extract_preserved_assets(page)
        html_content, is_scanned = pdf_page_to_html(page, preserved_assets)
        page_dict = {
            "page_num": i + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "html": html_content,
            "is_scanned": is_scanned,
            "preserved_assets": preserved_assets,
        }
        if is_scanned:
            # Render high-res image for Gemini vision (3x = ~216 DPI)
            zoom = 3.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            page_dict["image_b64"] = base64.b64encode(img_bytes).decode()
        pages.append(page_dict)
    doc.close()
    return pages
