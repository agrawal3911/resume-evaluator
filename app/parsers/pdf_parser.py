import pymupdf as fitz
from app.parsers.cleaning import clean_text
from app.parsers.exceptions import DocumentParsingError

def parse_pdf(file_bytes: bytes) -> str:
    """
    Parses a PDF from bytes and extracts its text.
    Raises DocumentParsingError if no text can be extracted or if the file is invalid.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise DocumentParsingError(f"Failed to open PDF document: {e}") from e

    try:
        extracted_text: list[str] = []

        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                extracted_text.append(page_text)
    finally:
        doc.close()

    # Combine, clean, then validate
    combined_text = "\n".join(extracted_text)
    cleaned = clean_text(combined_text)

    if not cleaned:
        raise DocumentParsingError(
            "No extractable text found in PDF. It may be an image-only scan or empty."
        )

    return cleaned
