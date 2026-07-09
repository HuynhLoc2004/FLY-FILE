import fitz  # PyMuPDF
import io

def merge_pages_by_manifest(files_bytes: list[bytes], manifest: list[dict]) -> bytes:
    """
    Merge specific pages in a custom order.
    manifest: [{ "file_index": 0, "page": 1 }, ...]  (page is 1-indexed)
    """
    docs = [fitz.open(stream=b, filetype="pdf") for b in files_bytes]
    result = fitz.open()

    for entry in manifest:
        file_idx = entry["file_index"]
        page_num = entry["page"] - 1  # Convert to 0-indexed
        doc = docs[file_idx]
        if 0 <= page_num < len(doc):
            result.insert_pdf(doc, from_page=page_num, to_page=page_num)

    out = io.BytesIO()
    result.save(out)
    result.close()
    for doc in docs:
        doc.close()

    return out.getvalue()
