import pytest

from app.schemas.resume import Resume, Experience, Education
from app.schemas.job_description import JobDescription
from app.schemas.match_result import MatchResult
from app.services.matching_service import (
    match_resume_to_job,
    WEIGHT_REQUIRED_SKILLS,
    WEIGHT_PREFERRED_SKILLS,
    WEIGHT_EXPERIENCE,
    WEIGHT_EDUCATION,
)


# --- Helpers ---

def _make_resume(**kwargs) -> Resume:
    defaults = {"name": "Test Candidate"}
    defaults.update(kwargs)
    return Resume(**defaults)


def _make_jd(**kwargs) -> JobDescription:
    defaults = {"job_title": "Test Role"}
    defaults.update(kwargs)
    return JobDescription(**defaults)


# ========================================
# Skill Matching Tests
# ========================================

class TestSkillMatching:
    def test_perfect_required_skill_match(self):
        resume = _make_resume(skills=["Python", "SQL", "Docker"])
        jd = _make_jd(required_skills=["Python", "SQL", "Docker"])
        result = match_resume_to_job(resume, jd)
        assert result.matched_required_skills == ["Python", "SQL", "Docker"]
        assert result.missing_required_skills == []
        assert result.score_breakdown.required_skills_score == WEIGHT_REQUIRED_SKILLS

    def test_partial_required_skill_match(self):
        resume = _make_resume(skills=["Python", "SQL"])
        jd = _make_jd(required_skills=["Python", "SQL", "Docker"])
        result = match_resume_to_job(resume, jd)
        assert result.matched_required_skills == ["Python", "SQL"]
        assert result.missing_required_skills == ["Docker"]
        expected_score = round((2 / 3) * WEIGHT_REQUIRED_SKILLS, 1)
        assert result.score_breakdown.required_skills_score == expected_score

    def test_no_required_skill_match(self):
        resume = _make_resume(skills=["Java", "C++"])
        jd = _make_jd(required_skills=["Python", "SQL", "Docker"])
        result = match_resume_to_job(resume, jd)
        assert result.matched_required_skills == []
        assert result.missing_required_skills == ["Python", "SQL", "Docker"]
        assert result.score_breakdown.required_skills_score == 0.0

    def test_preferred_skills_matching(self):
        resume = _make_resume(skills=["Python", "AWS"])
        jd = _make_jd(
            required_skills=["Python"],
            preferred_skills=["AWS", "Kubernetes"],
        )
        result = match_resume_to_job(resume, jd)
        assert result.matched_preferred_skills == ["AWS"]
        assert result.missing_preferred_skills == ["Kubernetes"]

    def test_case_insensitive_matching(self):
        resume = _make_resume(skills=["python", "FASTAPI", "Sql"])
        jd = _make_jd(required_skills=["Python", "FastAPI", "SQL"])
        result = match_resume_to_job(resume, jd)
        assert len(result.matched_required_skills) == 3
        assert result.missing_required_skills == []

    def test_duplicate_skills_handled(self):
        resume = _make_resume(skills=["Python", "python", "PYTHON"])
        jd = _make_jd(required_skills=["Python", "Python", "python"])
        result = match_resume_to_job(resume, jd)
        # Deduplicated: only 1 unique skill
        assert len(result.matched_required_skills) == 1
        assert result.missing_required_skills == []
        assert result.score_breakdown.required_skills_score == WEIGHT_REQUIRED_SKILLS

    def test_whitespace_in_skills(self):
        resume = _make_resume(skills=["  Python  ", "FastAPI"])
        jd = _make_jd(required_skills=["Python", "  FastAPI  "])
        result = match_resume_to_job(resume, jd)
        assert len(result.matched_required_skills) == 2

    def test_empty_required_skills(self):
        resume = _make_resume(skills=["Python"])
        jd = _make_jd(required_skills=[])
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.required_skills_score == WEIGHT_REQUIRED_SKILLS

    def test_empty_preferred_skills(self):
        resume = _make_resume(skills=["Python"])
        jd = _make_jd(preferred_skills=[])
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.preferred_skills_score == WEIGHT_PREFERRED_SKILLS

    def test_empty_resume_skills(self):
        resume = _make_resume(skills=[])
        jd = _make_jd(required_skills=["Python", "SQL"])
        result = match_resume_to_job(resume, jd)
        assert result.matched_required_skills == []
        assert result.missing_required_skills == ["Python", "SQL"]
        assert result.score_breakdown.required_skills_score == 0.0


# ========================================
# Experience Matching Tests
# ========================================

class TestExperienceMatching:
    def test_experience_satisfied(self):
        resume = _make_resume(
            experience=[
                Experience(
                    company="Acme", role="Dev",
                    start_date="2018-01", end_date="2023-01",
                )
            ]
        )
        jd = _make_jd(experience_required="3+ years")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.experience_score == WEIGHT_EXPERIENCE
        assert "Meets requirement" in result.experience_match

    def test_experience_not_satisfied(self):
        resume = _make_resume(
            experience=[
                Experience(
                    company="Acme", role="Dev",
                    start_date="2022-01", end_date="2023-01",
                )
            ]
        )
        jd = _make_jd(experience_required="5+ years")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.experience_score < WEIGHT_EXPERIENCE
        assert "Below requirement" in result.experience_match

    def test_missing_experience_dates(self):
        resume = _make_resume(
            experience=[
                Experience(company="Acme", role="Dev")
            ]
        )
        jd = _make_jd(experience_required="3+ years")
        result = match_resume_to_job(resume, jd)
        assert "Cannot determine" in result.experience_match
        # Gets half credit
        assert result.score_breakdown.experience_score == WEIGHT_EXPERIENCE * 0.5

    def test_no_experience_requirement(self):
        resume = _make_resume()
        jd = _make_jd(experience_required=None)
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.experience_score == WEIGHT_EXPERIENCE
        assert "No experience requirement" in result.experience_match

    def test_no_resume_experience(self):
        resume = _make_resume(experience=[])
        jd = _make_jd(experience_required="3+ years")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.experience_score == 0.0
        assert "Below requirement" in result.experience_match

    def test_present_experience_date_parsing(self):
        resume = _make_resume(
            experience=[
                Experience(
                    company="Acme", role="Senior Dev",
                    start_date="2020-01", end_date="Present",
                )
            ]
        )
        jd = _make_jd(experience_required="3+ years")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.experience_score == WEIGHT_EXPERIENCE
        assert "Meets requirement" in result.experience_match



# ========================================
# Education Matching Tests
# ========================================

class TestEducationMatching:
    def test_education_satisfied(self):
        resume = _make_resume(
            education=[
                Education(
                    institution="MIT",
                    degree="Bachelor's",
                    field="Computer Science",
                )
            ]
        )
        jd = _make_jd(education_required="Bachelor's in Computer Science")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.education_score == WEIGHT_EDUCATION
        assert "Education matches" in result.education_match

    def test_education_mismatch(self):
        resume = _make_resume(
            education=[
                Education(institution="Art School", degree="BFA", field="Art")
            ]
        )
        jd = _make_jd(education_required="Bachelor's in Computer Science")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.education_score == 0.0
        assert "does not match" in result.education_match

    def test_no_education_requirement(self):
        resume = _make_resume()
        jd = _make_jd(education_required=None)
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.education_score == WEIGHT_EDUCATION

    def test_no_resume_education(self):
        resume = _make_resume(education=[])
        jd = _make_jd(education_required="Bachelor's in CS")
        result = match_resume_to_job(resume, jd)
        assert result.score_breakdown.education_score == 0.0
        assert "No education listed" in result.education_match


# ========================================
# Score Calculation Tests
# ========================================

class TestScoreCalculation:
    def test_perfect_score(self):
        resume = _make_resume(
            skills=["Python", "SQL", "Docker"],
            experience=[
                Experience(
                    company="Acme", role="Dev",
                    start_date="2015-01", end_date="2023-01",
                )
            ],
            education=[
                Education(
                    institution="MIT",
                    degree="Bachelor's",
                    field="Computer Science",
                )
            ],
        )
        jd = _make_jd(
            required_skills=["Python", "SQL", "Docker"],
            preferred_skills=[],
            experience_required="3+ years",
            education_required="Bachelor's Computer Science",
        )
        result = match_resume_to_job(resume, jd)
        assert result.score == 100.0
        assert result.verdict == "Strong Match"

    def test_score_never_exceeds_100(self):
        # All categories get full marks → should still cap at 100
        resume = _make_resume(
            skills=["Python", "SQL", "Docker", "AWS", "K8s"],
            experience=[
                Experience(
                    company="Acme", role="Dev",
                    start_date="2010-01", end_date="2023-01",
                )
            ],
            education=[
                Education(institution="MIT", degree="PhD", field="CS")
            ],
        )
        jd = _make_jd(
            required_skills=["Python"],
            preferred_skills=["AWS"],
            experience_required="2+ years",
            education_required="CS",
        )
        result = match_resume_to_job(resume, jd)
        assert result.score <= 100.0

    def test_zero_score(self):
        resume = _make_resume(skills=[], experience=[], education=[])
        jd = _make_jd(
            required_skills=["Python", "SQL"],
            preferred_skills=["AWS"],
            experience_required="5+ years",
            education_required="Master's in CS",
        )
        result = match_resume_to_job(resume, jd)
        assert result.score == 0.0
        assert result.verdict == "Poor Match"

    def test_weights_sum_to_100(self):
        total = (
            WEIGHT_REQUIRED_SKILLS
            + WEIGHT_PREFERRED_SKILLS
            + WEIGHT_EXPERIENCE
            + WEIGHT_EDUCATION
        )
        assert total == 100.0


# ========================================
# Verdict Tests
# ========================================

class TestVerdict:
    def test_strong_match_boundary(self):
        resume = _make_resume(skills=["Python", "SQL", "Docker"])
        jd = _make_jd(required_skills=["Python", "SQL", "Docker"])
        # With empty preferred, no exp req, no edu req → full marks = 100
        result = match_resume_to_job(resume, jd)
        assert result.verdict == "Strong Match"

    def test_moderate_match(self):
        resume = _make_resume(skills=["Python", "SQL"])
        jd = _make_jd(
            required_skills=["Python", "SQL", "Docker"],
            experience_required="5+ years",
        )
        result = match_resume_to_job(resume, jd)
        # 40 required + 15 preferred + 0 exp + 10 edu = 65
        assert result.verdict == "Moderate Match"

    def test_poor_match(self):
        resume = _make_resume(skills=[])
        jd = _make_jd(
            required_skills=["Python", "SQL", "Docker"],
            preferred_skills=["AWS"],
            experience_required="5+ years",
            education_required="PhD in CS",
        )
        result = match_resume_to_job(resume, jd)
        assert result.verdict == "Poor Match"


# ========================================
# Edge Case Tests
# ========================================

class TestEdgeCases:
    def test_completely_empty_resume_and_jd(self):
        resume = _make_resume()
        jd = _make_jd()
        result = match_resume_to_job(resume, jd)
        # No requirements → full marks across all categories
        assert result.score == 100.0
        assert isinstance(result, MatchResult)

    def test_result_is_pydantic_model(self):
        resume = _make_resume(skills=["Python"])
        jd = _make_jd(required_skills=["Python"])
        result = match_resume_to_job(resume, jd)
        assert isinstance(result, MatchResult)
        data = result.model_dump()
        assert "score" in data
        assert "verdict" in data
        assert "score_breakdown" in data
