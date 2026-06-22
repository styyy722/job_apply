"""Extract raw text from an uploaded CV (PDF, DOCX, or plain text)."""

from __future__ import annotations

import io


class UnsupportedFileType(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    """Return the plain text of a CV file based on its extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _from_pdf(data)
    if lower.endswith(".docx"):
        return _from_docx(data)
    if lower.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise UnsupportedFileType(
        f"Unsupported file type for {filename!r}. Use PDF, DOCX, TXT, or MD."
    )


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _from_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()
