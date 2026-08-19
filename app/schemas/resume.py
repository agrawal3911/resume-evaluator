from pydantic import BaseModel, EmailStr


class Experience(BaseModel):
    """A single work experience entry."""
    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Education(BaseModel):
    """A single education entry."""
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Project(BaseModel):
    """A single project entry."""
    name: str
    description: str | None = None
    technologies: list[str] = []


class Certification(BaseModel):
    """A single certification entry."""
    name: str
    issuer: str | None = None
    date: str | None = None


class Resume(BaseModel):
    """Structured representation of a parsed resume."""
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    skills: list[str] = []
    education: list[Education] = []
    experience: list[Experience] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
