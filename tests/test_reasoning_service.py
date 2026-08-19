import json
import pytest
from unittest.mock import patch, MagicMock

from app.schemas.match_result import MatchResult, ScoreBreakdown
from app.schemas.match_reasoning import MatchReasoning
from app.services.reasoning_service import generate_match_reasoning
from app.services.exceptions import LLMConfigurationError, LLMExtractionError


# --- Fixtures: pre-built MatchResult objects ---

STRONG_MATCH_RESULT = MatchResult(
    score=92.0,
    verdict="Strong Match",
    matched_required_skills=["Python", "FastAPI", "SQL"],
    missing_required_skills=[],
    matched_preferred_skills=["Docker"],
    missing_preferred_skills=["Kubernetes"],
    experience_match="Meets requirement: 5.0 years >= 3 years required",
    education_match="Education matches: B.S. Computer Science from MIT",
    score_breakdown=ScoreBreakdown(
        required_skills_score=60.0,
        preferred_skills_score=7.5,
        experience_score=15.0,
        education_score=10.0,
    ),
)

MODERATE_MATCH_RESULT = MatchResult(
    score=65.0,
    verdict="Moderate Match",
    matched_required_skills=["Python", "FastAPI"],
    missing_required_skills=["Docker"],
    matched_preferred_skills=[],
    missing_preferred_skills=["AWS"],
    experience_match="Below requirement: 1.0 years < 3 years required",
    education_match="No education requirement specified",
    score_breakdown=ScoreBreakdown(
        required_skills_score=40.0,
        preferred_skills_score=0.0,
        experience_score=5.0,
        education_score=10.0,
    ),
)

POOR_MATCH_RESULT = MatchResult(
    score=15.0,
    verdict="Poor Match",
    matched_required_skills=[],
    missing_required_skills=["Python", "SQL", "Docker"],
    matched_preferred_skills=[],
    missing_preferred_skills=["AWS"],
    experience_match="No education listed; requirement is 5+ years",
    education_match="Education does not match requirement: Master's in CS",
    score_breakdown=ScoreBreakdown(
        required_skills_score=0.0,
        preferred_skills_score=0.0,
        experience_score=7.5,
        education_score=0.0,
    ),
)

MISSING_INFO_RESULT = MatchResult(
    score=47.5,
    verdict="Weak Match",
    matched_required_skills=["Python"],
    missing_required_skills=["SQL", "Docker"],
    matched_preferred_skills=[],
    missing_preferred_skills=[],
    experience_match="Cannot determine candidate experience (missing dates); requirement is 3+ years",
    education_match="No education listed; requirement is Bachelor's in CS",
    score_breakdown=ScoreBreakdown(
        required_skills_score=20.0,
        preferred_skills_score=15.0,
        experience_score=7.5,
        education_score=0.0,
    ),
)


# --- Helper to create mock LLM reasoning responses ---

def _make_reasoning_json(
    summary: str = "Test summary",
    strengths: list[str] | None = None,
    gaps: list[str] | None = None,
    experience_reasoning: str = "Experience analysis.",
    education_reasoning: str = "Education analysis.",
    final_reasoning: str = "Final assessment.",
) -> str:
    return json.dumps({
        "summary": summary,
        "strengths": strengths if strengths is not None else ["Strength 1"],
        "gaps": gaps if gaps is not None else ["Gap 1"],
        "experience_reasoning": experience_reasoning,
        "education_reasoning": education_reasoning,
        "final_reasoning": final_reasoning,
    })


def _mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


def _patch_env_and_client(mock_response_text: str):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(mock_response_text)
    env_patch = patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-not-real"})
    client_patch = patch(
        "app.services.reasoning_service.genai.Client",
        return_value=mock_client,
    )
    return env_patch, client_patch, mock_client


# ========================================
# Reasoning Tests
# ========================================

class TestGenerateMatchReasoning:
    def test_strong_match_reasoning(self):
        reasoning_json = _make_reasoning_json(
            summary="Excellent candidate with strong technical alignment.",
            strengths=["Matches all 3 required skills", "Exceeds experience requirement"],
            gaps=["Missing Kubernetes (preferred)"],
        )
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            reasoning = generate_match_reasoning(STRONG_MATCH_RESULT)
            assert isinstance(reasoning, MatchReasoning)
            assert "Excellent" in reasoning.summary
            assert len(reasoning.strengths) == 2
            assert len(reasoning.gaps) == 1

    def test_moderate_match_reasoning(self):
        reasoning_json = _make_reasoning_json(
            summary="Candidate shows partial alignment with moderate gaps.",
            strengths=["Knows Python and FastAPI"],
            gaps=["Missing Docker (required)", "Missing AWS (preferred)", "Insufficient experience"],
        )
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            reasoning = generate_match_reasoning(MODERATE_MATCH_RESULT)
            assert isinstance(reasoning, MatchReasoning)
            assert len(reasoning.gaps) == 3

    def test_poor_match_reasoning(self):
        reasoning_json = _make_reasoning_json(
            summary="Candidate does not align with the role requirements.",
            strengths=[],
            gaps=["Missing all required skills", "Education mismatch"],
        )
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            reasoning = generate_match_reasoning(POOR_MATCH_RESULT)
            assert isinstance(reasoning, MatchReasoning)
            assert reasoning.strengths == []

    def test_missing_information_reasoning(self):
        reasoning_json = _make_reasoning_json(
            summary="Candidate has limited matching data available.",
            experience_reasoning="Experience could not be determined due to missing dates.",
            education_reasoning="No education information provided on resume.",
        )
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            reasoning = generate_match_reasoning(MISSING_INFO_RESULT)
            assert "missing dates" in reasoning.experience_reasoning
            assert "No education" in reasoning.education_reasoning

    def test_reasoning_does_not_modify_score(self):
        """The reasoning service must not alter the Phase 5 score."""
        reasoning_json = _make_reasoning_json()
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            original_score = STRONG_MATCH_RESULT.score
            original_verdict = STRONG_MATCH_RESULT.verdict
            generate_match_reasoning(STRONG_MATCH_RESULT)
            assert STRONG_MATCH_RESULT.score == original_score
            assert STRONG_MATCH_RESULT.verdict == original_verdict

    def test_reasoning_does_not_modify_verdict(self):
        """The reasoning service must not alter the Phase 5 verdict."""
        reasoning_json = _make_reasoning_json()
        env_p, client_p, _ = _patch_env_and_client(reasoning_json)
        with env_p, client_p:
            generate_match_reasoning(POOR_MATCH_RESULT)
            assert POOR_MATCH_RESULT.verdict == "Poor Match"
            assert POOR_MATCH_RESULT.score == 15.0


# ========================================
# Error Handling Tests
# ========================================

class TestReasoningErrorHandling:
    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
                generate_match_reasoning(STRONG_MATCH_RESULT)

    def test_api_failure_raises(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("Network timeout")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch("app.services.reasoning_service.genai.Client", return_value=mock_client):
            with pytest.raises(LLMExtractionError, match="LLM API call failed"):
                generate_match_reasoning(STRONG_MATCH_RESULT)

    def test_invalid_json_response_raises(self):
        env_p, client_p, _ = _patch_env_and_client("this is not json")
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                generate_match_reasoning(STRONG_MATCH_RESULT)

    def test_malformed_schema_response_raises(self):
        """Valid JSON but missing required fields."""
        bad_json = json.dumps({"summary": "Only summary, nothing else"})
        env_p, client_p, _ = _patch_env_and_client(bad_json)
        with env_p, client_p:
            with pytest.raises(LLMExtractionError, match="Failed to validate"):
                generate_match_reasoning(STRONG_MATCH_RESULT)
