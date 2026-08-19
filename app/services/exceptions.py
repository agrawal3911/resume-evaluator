class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass

class LLMConfigurationError(LLMServiceError):
    """Raised when the LLM is not properly configured (e.g., missing API key)."""
    pass

class LLMExtractionError(LLMServiceError):
    """Raised when the LLM fails to extract or return valid structured data."""
    pass
