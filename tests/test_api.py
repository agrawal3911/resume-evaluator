import io
import pymupdf as fitz
import pytest
from unittest.mock import patch, MagicMock
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.resume import Resume, Experience
from app.schemas.job_description import JobDescription
from app.schemas.match_reasoning import MatchReasoning
from app.services.exceptions import LLMExtractionError, LLMConfigurationError

client = TestClient(app)


# --- Helpers for creating sample test files ---

def create_valid_pdf_bytes(text: str = "Jane Doe\nPython Developer") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    return doc.write()


def create_valid_docx_bytes(text: str = "Jane Doe\nPython Developer") -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


# --- Sample mocked models ---

MOCK_RESUME = Resume(
    name="Jane Doe",
    email="jane@example.com",
    skills=["Python", "FastAPI"],
    experience=[
        Experience(
            company="Tech Corp",
            role="Software Engineer",
            start_date="2020-01",
            end_date="2023-01",
        )
    ],
)

MOCK_JD = JobDescription(
    job_title="Python Developer",
    required_skills=["Python", "FastAPI"],
    preferred_skills=["Docker"],
    experience_required="2+ years",
)

MOCK_REASONING = MatchReasoning(
    summary="Strong candidate with good skill alignment.",
    strengths=["Matches Python and FastAPI"],
    gaps=["Missing Docker"],
    experience_reasoning="Meets experience requirement.",
    education_reasoning="No education requirement specified.",
    final_reasoning="Overall strong fit for the position.",
)


def _patch_llm_services(
    resume_mock=MOCK_RESUME,
    jd_mock=MOCK_JD,
    reasoning_mock=MOCK_REASONING,
):
    """Context manager patches for LLM extraction and reasoning services."""
    p1 = patch("app.api.evaluate.extract_resume", return_value=resume_mock)
    p2 = patch("app.api.evaluate.extract_job_description", return_value=jd_mock)
    p3 = patch("app.api.evaluate.generate_match_reasoning", return_value=reasoning_mock)
    return p1, p2, p3


# --- Health Check Test ---

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# --- Evaluation Endpoint Tests ---

class TestEvaluateEndpoint:
    def test_valid_pdf_evaluation(self):
        pdf_bytes = create_valid_pdf_bytes()
        p1, p2, p3 = _patch_llm_services()
        with p1, p2, p3:
            response = client.post(
                "/evaluate",
                data={"jd_text": "We need a Python Developer with FastAPI skills."},
                files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()

        # Structure checks
        assert "score" in data
        assert "verdict" in data
        assert "match_result" in data
        assert "reasoning" in data

        # Values check
        assert data["score"] == 85.0  # 60 (req skills) + 0 (preferred Docker missing) + 15 (exp) + 10 (no edu req)
        assert data["verdict"] == "Strong Match"
        assert data["match_result"]["matched_required_skills"] == ["Python", "FastAPI"]
        assert data["reasoning"]["summary"] == "Strong candidate with good skill alignment."

    def test_valid_docx_evaluation(self):
        docx_bytes = create_valid_docx_bytes()
        p1, p2, p3 = _patch_llm_services()
        with p1, p2, p3:
            response = client.post(
                "/evaluate",
                data={"jd_text": "Python Developer needed."},
                files={
                    "file": (
                        "resume.docx",
                        docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "Strong Match"
        assert data["match_result"]["matched_required_skills"] == ["Python", "FastAPI"]

    def test_missing_jd_fails(self):
        pdf_bytes = create_valid_pdf_bytes()
        response = client.post(
            "/evaluate",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 422  # Unprocessable Entity (missing form field)

    def test_empty_jd_fails(self):
        pdf_bytes = create_valid_pdf_bytes()
        response = client.post(
            "/evaluate",
            data={"jd_text": "   \n  "},
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 400
        assert "Job description text cannot be empty" in response.json()["detail"]

    def test_missing_resume_fails(self):
        response = client.post(
            "/evaluate",
            data={"jd_text": "Valid JD text"},
        )
        assert response.status_code == 422  # Missing required file parameter

    def test_unsupported_file_format_fails(self):
        response = client.post(
            "/evaluate",
            data={"jd_text": "Valid JD text"},
            files={"file": ("resume.txt", b"plain text content", "text/plain")},
        )
        assert response.status_code == 415
        assert "Unsupported file format" in response.json()["detail"]

    def test_invalid_corrupted_pdf_fails(self):
        response = client.post(
            "/evaluate",
            data={"jd_text": "Valid JD text"},
            files={"file": ("resume.pdf", b"corrupted pdf bytes", "application/pdf")},
        )
        assert response.status_code == 400
        assert "Failed to open PDF document" in response.json()["detail"]

    def test_invalid_corrupted_docx_fails(self):
        response = client.post(
            "/evaluate",
            data={"jd_text": "Valid JD text"},
            files={
                "file": (
                    "resume.docx",
                    b"corrupted docx bytes",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert response.status_code == 400
        assert "Failed to open DOCX document" in response.json()["detail"]

    def test_mocked_llm_extraction_failure(self):
        pdf_bytes = create_valid_pdf_bytes()
        with patch("app.api.evaluate.extract_resume", side_effect=LLMExtractionError("LLM API call failed")):
            response = client.post(
                "/evaluate",
                data={"jd_text": "Valid JD text"},
                files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            )
        assert response.status_code == 500
        assert "LLM API call failed" in response.json()["detail"]

    def test_mocked_reasoning_failure(self):
        pdf_bytes = create_valid_pdf_bytes()
        p1 = patch("app.api.evaluate.extract_resume", return_value=MOCK_RESUME)
        p2 = patch("app.api.evaluate.extract_job_description", return_value=MOCK_JD)
        p3 = patch("app.api.evaluate.generate_match_reasoning", side_effect=LLMExtractionError("Reasoning failed"))
        with p1, p2, p3:
            response = client.post(
                "/evaluate",
                data={"jd_text": "Valid JD text"},
                files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            )
        assert response.status_code == 500
        assert "Reasoning failed" in response.json()["detail"]

    def test_score_and_verdict_authoritative(self):
        """Verify that Phase 5 score and verdict are unchanged in the EvaluationResponse."""
        pdf_bytes = create_valid_pdf_bytes()
        p1, p2, p3 = _patch_llm_services()
        with p1, p2, p3:
            response = client.post(
                "/evaluate",
                data={"jd_text": "Valid JD text"},
                files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()

        # Score and verdict at top level must match match_result exactly
        assert data["score"] == data["match_result"]["score"]
        assert data["verdict"] == data["match_result"]["verdict"]

    def test_oversized_jd_text_fails(self):
        pdf_bytes = create_valid_pdf_bytes()
        huge_jd = "A" * 50_001
        response = client.post(
            "/evaluate",
            data={"jd_text": huge_jd},
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 400
        assert "exceeds maximum allowed length" in response.json()["detail"]

    def test_oversized_file_upload_fails(self):
        huge_file_bytes = b"0" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/evaluate",
            data={"jd_text": "Valid JD text"},
            files={"file": ("resume.pdf", huge_file_bytes, "application/pdf")},
        )
        assert response.status_code == 400
        assert "exceeds maximum allowed limit" in response.json()["detail"]

    def test_unhandled_exception_caught_by_global_handler(self):
        pdf_bytes = create_valid_pdf_bytes()
        with patch("app.api.evaluate.parse_document", side_effect=ZeroDivisionError("Unexpected math bug")):
            response = client.post(
                "/evaluate",
                data={"jd_text": "Valid JD text"},
                files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            )
        assert response.status_code == 400  # Caught by parse exception handler in route

