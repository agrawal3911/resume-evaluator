import re

def clean_text(text: str | None) -> str:
    """
    Cleans extracted text by normalizing whitespace.
    - Replaces multiple spaces with a single space.
    - Replaces 3 or more consecutive newlines with exactly 2 newlines.
    - Strips leading and trailing whitespace.
    """
    if not text:
        return ""
    
    # Split into lines, strip each line to remove trailing/leading spaces per line, then rejoin
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Replace multiple spaces (excluding newlines) with a single space
    text = re.sub(r'[^\S\n]+', ' ', text)
    
    # Replace 3 or more consecutive newlines with 2 newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip leading and trailing whitespace from the entire document
    return text.strip()
