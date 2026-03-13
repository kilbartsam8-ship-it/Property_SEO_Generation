import io
from pathlib import Path
from typing import BinaryIO

import PyPDF2
from pdf2image import convert_from_bytes
import pytesseract


class PdfExtractionError(Exception):
    """Raised when PDF extraction fails."""


def extract_pdf_text(file_obj: BinaryIO, min_page_text_threshold: int = 30) -> str:
    if file_obj is None:
        return ""

    try:
        pdf_bytes = file_obj.read()
        file_obj.seek(0)
    except Exception as exc:
        raise PdfExtractionError(f"Unable to read PDF stream: {exc}") from exc

    if not pdf_bytes:
        raise PdfExtractionError("PDF file is empty")

    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise PdfExtractionError(f"Failed to parse PDF: {exc}") from exc

    text_parts = []
    ocr_parts = []

    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        text_parts.append(page_text)

        if len(page_text.strip()) >= min_page_text_threshold:
            continue

        try:
            images = convert_from_bytes(pdf_bytes, first_page=page_index, last_page=page_index)
            for image in images:
                ocr_parts.append(pytesseract.image_to_string(image))
        except Exception:
            continue

    combined = "\n".join(text_parts + ocr_parts).strip()
    if not combined:
        raise PdfExtractionError("No text could be extracted from PDF")
    return combined


def extract_text_from_path(path: Path) -> str:
    with path.open("rb") as fp:
        return extract_pdf_text(fp)
