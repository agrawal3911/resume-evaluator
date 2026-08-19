import os
from google import genai
from pydantic import ValidationError

from app.schemas.resume import Resume
from app.schemas.job_description import JobDescription
from app.services.prompts import RESUME_EXTRACTION_PROMPT, JOB_DESCRIPTION_EXTRACTION_PROMPT
from app.services.exceptions import LLMConfigurationError, LLMExtractionError


def _get_client() -> genai.Client:
    """Creates a Gemini client using the API key from environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMConfigurationError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your .env file or environment."
        )
    return genai.Client(api_key=api_key)


def _get_model_name() -> str:
    """Returns the model name, allowing override via environment variable."""
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def _clean_json_response(text: str | None) -> str:
    """Removes markdown codeblock fences (e.g. ```json ... ```) if present."""
    if not text:
        return ""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


def extract_resume(resume_text: str) -> Resume:
    """
    Uses Google Gemini to extract structured resume data from plain text.
    Returns a validated Resume Pydantic model.
    """
    if not resume_text or not resume_text.strip():
        raise LLMExtractionError("Cannot extract resume from empty text.")

    client = _get_client()
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)

    try:
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Resume,
            ),
        )
    except Exception as e:
        raise LLMExtractionError(f"LLM API call failed: {e}") from e

    # Parse the JSON response into our Pydantic model
    try:
        cleaned_text = _clean_json_response(response.text)
        return Resume.model_validate_json(cleaned_text)
    except (ValidationError, Exception) as e:
        raise LLMExtractionError(f"Failed to validate LLM response: {e}") from e


def extract_job_description(jd_text: str) -> JobDescription:
    """
    Uses Google Gemini to extract structured job description data from plain text.
    Returns a validated JobDescription Pydantic model.
    """
    if not jd_text or not jd_text.strip():
        raise LLMExtractionError("Cannot extract job description from empty text.")

    client = _get_client()
    prompt = JOB_DESCRIPTION_EXTRACTION_PROMPT.format(jd_text=jd_text)

    try:
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobDescription,
            ),
        )
    except Exception as e:
        raise LLMExtractionError(f"LLM API call failed: {e}") from e

    try:
        cleaned_text = _clean_json_response(response.text)
        return JobDescription.model_validate_json(cleaned_text)
    except (ValidationError, Exception) as e:
        raise LLMExtractionError(f"Failed to validate LLM response: {e}") from e

