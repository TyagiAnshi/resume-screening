"""
pdf_extractor.py
────────────────
Extracts plain text from a PDF file or returns text as-is if
the uploaded file is already plain text (.txt).

No LLM calls — pure local processing.
"""

import io
import pdfplumber


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from a PDF or plain-text file.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename (used to detect file type).

    Returns:
        Extracted text as a single string.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_from_pdf(file_bytes)
    elif lower.endswith(".txt") or lower.endswith(".md"):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        # Try PDF first, fall back to UTF-8 decode
        try:
            return _extract_from_pdf(file_bytes)
        except Exception:
            return file_bytes.decode("utf-8", errors="replace")


def _extract_from_pdf(file_bytes: bytes) -> str:
    """Use pdfplumber to extract text from a PDF byte stream."""
    text_pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_pages.append(page_text)
    return "\n\n".join(text_pages)
