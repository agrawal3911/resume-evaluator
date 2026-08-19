import os
from app.parsers.pdf_parser import parse_pdf
from app.parsers.docx_parser import parse_docx
from app.parsers.exceptions import UnsupportedFormatError

def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Routes a document to the appropriate parser based on its file extension.
    Returns the extracted, cleaned text.
    Raises UnsupportedFormatError for unknown file types.
    """
    _, ext = os.path.splitext(filename.lower())
    
    if ext == ".pdf":
        return parse_pdf(file_bytes)
    elif ext == ".docx":
        return parse_docx(file_bytes)
    else:
        raise UnsupportedFormatError(f"Unsupported file format: {ext}. Only .pdf and .docx are supported.")
