from pydantic import BaseModel
from app.schemas.match_result import MatchResult
from app.schemas.match_reasoning import MatchReasoning


class EvaluationResponse(BaseModel):
    """Complete response model for resume evaluation."""
    score: float
    verdict: str
    match_result: MatchResult
    reasoning: MatchReasoning
