import pytest
from pydantic import ValidationError
from app.schemas.resume import Resume, Experience, Education, Project, Certification
from app.schemas.job_description import JobDescription


# --- Resume Tests ---

class TestResume:
    def test_valid_full_resume(self):
        resume = Resume(
            name="Jane Doe",
            email="jane@example.com",
            phone="+1-555-1234",
            skills=["Python", "FastAPI", "SQL"],
            education=[
                Education(
                    institution="MIT",
                    degree="B.S.",
                    field="Computer Science",
                    start_date="2015",
                    end_date="2019",
                )
            ],
            experience=[
                Experience(
                    company="Acme Corp",
                    role="Software Engineer",
                    start_date="2019-06",
                    end_date="2023-01",
                    description="Built REST APIs.",
                )
            ],
            projects=[
                Project(
                    name="Resume Evaluator",
                    description="AI-powered resume screening tool.",
                    technologies=["Python", "FastAPI", "Gemini"],
                )
            ],
            certifications=[
                Certification(
                    name="AWS Solutions Architect",
                    issuer="Amazon",
                    date="2022",
                )
            ],
        )
        assert resume.name == "Jane Doe"
        assert resume.email == "jane@example.com"
        assert len(resume.skills) == 3
        assert len(resume.education) == 1
        assert len(resume.experience) == 1
        assert len(resume.projects) == 1
        assert len(resume.certifications) == 1

    def test_minimal_resume(self):
        """Only name is required; everything else should default gracefully."""
        resume = Resume(name="John Doe")
        assert resume.name == "John Doe"
        assert resume.email is None
        assert resume.phone is None
        assert resume.skills == []
        assert resume.education == []
        assert resume.experience == []
        assert resume.projects == []
        assert resume.certifications == []

    def test_resume_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Resume()  # type: ignore[call-arg]

    def test_resume_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            Resume(name="Jane", email="not-an-email")

    def test_resume_model_dump(self):
        resume = Resume(
            name="Jane Doe",
            skills=["Python"],
            experience=[
                Experience(company="Acme", role="Dev")
            ],
        )
        data = resume.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "Jane Doe"
        assert data["skills"] == ["Python"]
        assert data["experience"][0]["company"] == "Acme"

    def test_resume_json_serialization(self):
        resume = Resume(name="Jane Doe", skills=["Python"])
        json_str = resume.model_dump_json()
        assert isinstance(json_str, str)
        assert "Jane Doe" in json_str
        assert "Python" in json_str

    def test_resume_empty_lists(self):
        resume = Resume(name="A", skills=[], education=[], experience=[])
        assert resume.skills == []
        assert resume.education == []
        assert resume.experience == []


# --- Nested Model Tests ---

class TestNestedModels:
    def test_experience_minimal(self):
        exp = Experience(company="Acme", role="Dev")
        assert exp.start_date is None
        assert exp.end_date is None
        assert exp.description is None

    def test_education_minimal(self):
        edu = Education(institution="MIT")
        assert edu.degree is None
        assert edu.field is None

    def test_project_minimal(self):
        proj = Project(name="Side project")
        assert proj.description is None
        assert proj.technologies == []

    def test_certification_minimal(self):
        cert = Certification(name="AWS SAA")
        assert cert.issuer is None
        assert cert.date is None

    def test_experience_missing_company_raises(self):
        with pytest.raises(ValidationError):
            Experience(role="Dev")  # type: ignore[call-arg]

    def test_education_missing_institution_raises(self):
        with pytest.raises(ValidationError):
            Education(degree="B.S.")  # type: ignore[call-arg]

    def test_project_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Project(description="something")  # type: ignore[call-arg]

    def test_certification_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Certification(issuer="Amazon")  # type: ignore[call-arg]


# --- JobDescription Tests ---

class TestJobDescription:
    def test_valid_full_job_description(self):
        jd = JobDescription(
            job_title="Backend Engineer",
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker", "Kubernetes"],
            experience_required="3+ years",
            education_required="Bachelor's in CS",
            responsibilities=["Design APIs", "Write tests"],
        )
        assert jd.job_title == "Backend Engineer"
        assert len(jd.required_skills) == 2
        assert len(jd.preferred_skills) == 2
        assert jd.experience_required == "3+ years"
        assert len(jd.responsibilities) == 2

    def test_minimal_job_description(self):
        jd = JobDescription(job_title="Intern")
        assert jd.job_title == "Intern"
        assert jd.required_skills == []
        assert jd.preferred_skills == []
        assert jd.experience_required is None
        assert jd.education_required is None
        assert jd.responsibilities == []

    def test_job_description_missing_title_raises(self):
        with pytest.raises(ValidationError):
            JobDescription()  # type: ignore[call-arg]

    def test_job_description_invalid_skills_type_raises(self):
        with pytest.raises(ValidationError):
            JobDescription(job_title="Dev", required_skills="Python")  # type: ignore[arg-type]

    def test_job_description_model_dump(self):
        jd = JobDescription(
            job_title="Dev",
            required_skills=["Python"],
        )
        data = jd.model_dump()
        assert data["job_title"] == "Dev"
        assert data["required_skills"] == ["Python"]
        assert data["preferred_skills"] == []

    def test_job_description_json_serialization(self):
        jd = JobDescription(job_title="Dev")
        json_str = jd.model_dump_json()
        assert isinstance(json_str, str)
        assert "Dev" in json_str
