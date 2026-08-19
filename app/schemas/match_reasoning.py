from pydantic import BaseModel


class MatchReasoning(BaseModel):
    """Structured LLM-generated explanation of a matching result."""
    summary: str
    strengths: list[str]
    gaps: list[str]
    experience_reasoning: str
    education_reasoning: str
    final_reasoning: str
