import json
import pytest
from unittest.mock import patch, MagicMock

from app.schemas.resume import Resume
from app.schemas.job_description import JobDescription
from app.services.llm_service import extract_resume, extract_job_description
from app.services.exceptions import LLMConfigurationError, LLMExtractionError


# --- Sample valid JSON responses (what the mocked LLM would return) ---

VALID_RESUME_JSON = json.dumps({
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1-555-1234",
    "skills": ["Python", "FastAPI"],
    "education": [
        {
            "institution": "MIT",
            "degree": "B.S.",
            "field": "Computer Science",
            "start_date": "2015",
            "end_date": "2019",
        }
    ],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Software Engineer",
            "start_date": "2019-06",
            "end_date": "2023-01",
            "description": "Built REST APIs.",
        }
    ],
    "projects": [],
    "certifications": [],
})

VALID_JD_JSON = json.dumps({
    "job_title": "Backend Engineer",
    "required_skills": ["Python", "SQL"],
    "preferred_skills": ["Docker"],
    "experience_required": "3+ years",
    "education_required": "Bachelor's in CS",
    "responsibilities": ["Design APIs", "Write tests"],
})

MINIMAL_RESUME_JSON = json.dumps({
    "name": "John Doe",
    "email": None,
    "phone": None,
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
})

MINIMAL_JD_JSON = json.dumps({
    "job_title": "Intern",
    "required_skills": [],
    "preferred_skills": [],
    "experience_required": None,
    "education_required": None,
    "responsibilities": [],
})


# --- Helper to build a mock Gemini response ---

def _mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


def _patch_env_and_client(mock_response_text: str):
    """Returns a tuple of patches: (env patch, client patch)."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(mock_response_text)

    env_patch = patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-not-real"})
    client_patch = patch("app.services.llm_service.genai.Client", return_value=mock_client)
    return env_patch, client_patch, mock_client


# --- Resume Extraction Tests ---

class TestExtractResume:
    def test_valid_resume_extraction(self):
        env_p, client_p, _ = _patch_env_and_client(VALID_RESUME_JSON)
        with env_p, client_p:
            resume = extract_resume("Jane Doe\nSoftware Engineer\n...")
            assert isinstance(resume, Resume)
            assert resume.name == "Jane Doe"
            assert resume.email == "jane@example.com"
            assert len(resume.skills) == 2
            assert len(resume.experience) == 1
            assert resume.experience[0].company == "Acme Corp"

    def test_minimal_resume_extraction(self):
        env_p, client_p, _ = _patch_env_and_client(MINIMAL_RESUME_JSON)
        with env_p, client_p:
            resume = extract_resume("John Doe")
            assert resume.name == "John Doe"
            assert resume.email is None
            assert resume.skills == []
            assert resume.experience == []

    def test_empty_resume_text_raises(self):
        with pytest.raises(LLMExtractionError, match="empty text"):
            extract_resume("")

    def test_whitespace_resume_text_raises(self):
        with pytest.raises(LLMExtractionError, match="empty text"):
            extract_resume("   \n  ")

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
                extract_resume("Some resume text")

    def test_api_failure_raises(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("Network error")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch("app.services.llm_service.genai.Client", return_value=mock_client):
            with pytest.raises(LLMExtractionError, match="LLM API call failed"):
                extract_resume("Some resume text")

    def test_invalid_json_response_raises(self):
        env_p, client_p, _ = _patch_env_and_client("not valid json at all")
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                extract_resume("Some resume text")

    def test_malformed_schema_response_raises(self):
        """LLM returns valid JSON but missing required 'name' field."""
        bad_json = json.dumps({"skills": ["Python"]})
        env_p, client_p, _ = _patch_env_and_client(bad_json)
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                extract_resume("Some resume text")

    def test_markdown_fenced_json_extraction(self):
        """LLM returns valid JSON wrapped inside markdown ```json ... ``` fences."""
        fenced_json = f"```json\n{VALID_RESUME_JSON}\n```"
        env_p, client_p, _ = _patch_env_and_client(fenced_json)
        with env_p, client_p:
            resume = extract_resume("Jane Doe\nSoftware Engineer\n...")
            assert isinstance(resume, Resume)
            assert resume.name == "Jane Doe"



# --- Job Description Extraction Tests ---

class TestExtractJobDescription:
    def test_valid_jd_extraction(self):
        env_p, client_p, _ = _patch_env_and_client(VALID_JD_JSON)
        with env_p, client_p:
            jd = extract_job_description("Backend Engineer role...")
            assert isinstance(jd, JobDescription)
            assert jd.job_title == "Backend Engineer"
            assert len(jd.required_skills) == 2
            assert jd.experience_required == "3+ years"

    def test_minimal_jd_extraction(self):
        env_p, client_p, _ = _patch_env_and_client(MINIMAL_JD_JSON)
        with env_p, client_p:
            jd = extract_job_description("Intern position")
            assert jd.job_title == "Intern"
            assert jd.required_skills == []
            assert jd.experience_required is None

    def test_empty_jd_text_raises(self):
        with pytest.raises(LLMExtractionError, match="empty text"):
            extract_job_description("")

    def test_whitespace_jd_text_raises(self):
        with pytest.raises(LLMExtractionError, match="empty text"):
            extract_job_description("   \n  ")

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
                extract_job_description("Some JD text")

    def test_api_failure_raises(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("Timeout")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch("app.services.llm_service.genai.Client", return_value=mock_client):
            with pytest.raises(LLMExtractionError, match="LLM API call failed"):
                extract_job_description("Some JD text")

    def test_invalid_json_response_raises(self):
        env_p, client_p, _ = _patch_env_and_client("{broken json")
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                extract_job_description("Some JD text")

    def test_malformed_schema_response_raises(self):
        """LLM returns valid JSON but missing required 'job_title' field."""
        bad_json = json.dumps({"required_skills": ["Python"]})
        env_p, client_p, _ = _patch_env_and_client(bad_json)
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                extract_job_description("Some JD text")
