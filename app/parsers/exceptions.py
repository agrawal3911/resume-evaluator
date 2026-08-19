class DocumentParsingError(Exception):
    """Exception raised when a document cannot be parsed (e.g., image-only PDF, corrupted)."""
    pass

class UnsupportedFormatError(Exception):
    """Exception raised when the document format is not supported."""
    pass
