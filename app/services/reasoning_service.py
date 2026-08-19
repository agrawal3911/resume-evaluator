from google import genai
from pydantic import ValidationError

from app.schemas.match_result import MatchResult
from app.schemas.match_reasoning import MatchReasoning
from app.services.llm_service import _get_client, _get_model_name, _clean_json_response
from app.services.prompts import MATCH_REASONING_PROMPT
from app.services.exceptions import LLMExtractionError
from app.services.matching_service import (
    WEIGHT_REQUIRED_SKILLS,
    WEIGHT_PREFERRED_SKILLS,
    WEIGHT_EXPERIENCE,
    WEIGHT_EDUCATION,
)


def generate_match_reasoning(match_result: MatchResult) -> MatchReasoning:
    """
    Uses the LLM to generate a human-readable explanation of a matching result.

    The LLM does NOT calculate or modify the score — the Phase 5 result is authoritative.
    It only explains why the candidate received the given score and verdict.
    """
    prompt = MATCH_REASONING_PROMPT.format(
        score=match_result.score,
        verdict=match_result.verdict,
        required_skills_score=match_result.score_breakdown.required_skills_score,
        required_skills_weight=WEIGHT_REQUIRED_SKILLS,
        preferred_skills_score=match_result.score_breakdown.preferred_skills_score,
        preferred_skills_weight=WEIGHT_PREFERRED_SKILLS,
        experience_score=match_result.score_breakdown.experience_score,
        experience_weight=WEIGHT_EXPERIENCE,
        education_score=match_result.score_breakdown.education_score,
        education_weight=WEIGHT_EDUCATION,
        matched_required=", ".join(match_result.matched_required_skills) or "None",
        missing_required=", ".join(match_result.missing_required_skills) or "None",
        matched_preferred=", ".join(match_result.matched_preferred_skills) or "None",
        missing_preferred=", ".join(match_result.missing_preferred_skills) or "None",
        experience_match=match_result.experience_match,
        education_match=match_result.education_match,
    )

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatchReasoning,
            ),
        )
    except Exception as e:
        raise LLMExtractionError(f"LLM API call failed during reasoning: {e}") from e

    try:
        cleaned_text = _clean_json_response(response.text)
        return MatchReasoning.model_validate_json(cleaned_text)
    except (ValidationError, Exception) as e:
        raise LLMExtractionError(
            f"Failed to validate LLM reasoning response: {e}"
        ) from e

