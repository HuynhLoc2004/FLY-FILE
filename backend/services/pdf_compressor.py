import io
import fitz  # PyMuPDF

def compress_pdf(file_bytes: bytes, level: str = "medium") -> bytes:
    """
    Compress a PDF using PyMuPDF image re-rendering.
    Levels:
      - 'medium': Clear text/table focus, smaller size. (~144 DPI, 82% JPEG quality)
      - 'extreme': Strong compression, still readable. (~104 DPI, 62% JPEG quality)
      - 'ultra': Maximum compression while keeping text usable. (~86 DPI, 50% JPEG quality)
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    new_doc = fitz.open()

    if level == "ultra":
        zoom = 1.2
        quality = 50
    elif level == "extreme":
        zoom = 1.45
        quality = 62
    else: # medium
        zoom = 2.0
        quality = 82

    for page in doc:
        # Render page to image at desired resolution
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        
        # Save as compressed JPEG bytes
        img_bytes = pix.tobytes("jpeg", jpg_quality=quality)
        
        # Insert into a new PDF page with the original dimensions
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=img_bytes)
        
    out_io = io.BytesIO()
    # Save with garbage collection and deflation enabled
    new_doc.save(out_io, garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    
    return out_io.getvalue()
