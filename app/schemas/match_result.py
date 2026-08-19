from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    """Breakdown of the individual scoring components."""
    required_skills_score: float
    preferred_skills_score: float
    experience_score: float
    education_score: float


class MatchResult(BaseModel):
    """Complete result of matching a Resume against a JobDescription."""
    score: float
    verdict: str
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_preferred_skills: list[str]
    missing_preferred_skills: list[str]
    experience_match: str
    education_match: str
    score_breakdown: ScoreBreakdown
