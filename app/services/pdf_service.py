from __future__ import annotations

import io

from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Minimal PDF text extraction for the Week 2 stretch.

    Notes:
    - Extraction quality varies a lot by PDF type (scanned vs digital).
    - We do not preserve page boundaries yet.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()

