import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Maximum allowed file size for uploaded resumes (10 MB)
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

# Maximum allowed character length for Job Description text (50,000 chars)
MAX_JD_LENGTH_CHARS: int = 50_000

# Allowed resume file extensions
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx"}

