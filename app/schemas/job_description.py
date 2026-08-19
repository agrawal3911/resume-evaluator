from pydantic import BaseModel


class JobDescription(BaseModel):
    """Structured representation of a job description."""
    job_title: str
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience_required: str | None = None
    education_required: str | None = None
    responsibilities: list[str] = []
