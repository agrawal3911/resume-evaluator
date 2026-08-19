import re
from datetime import datetime

from app.schemas.resume import Resume
from app.schemas.job_description import JobDescription
from app.schemas.match_result import MatchResult, ScoreBreakdown

# --- Scoring weight constants ---
WEIGHT_REQUIRED_SKILLS: float = 60.0
WEIGHT_PREFERRED_SKILLS: float = 15.0
WEIGHT_EXPERIENCE: float = 15.0
WEIGHT_EDUCATION: float = 10.0

# --- Verdict thresholds ---
VERDICT_STRONG_MIN: float = 80.0
VERDICT_MODERATE_MIN: float = 60.0
VERDICT_WEAK_MIN: float = 40.0


def _normalize_skill(skill: str) -> str:
    """Lowercase and strip whitespace for fair comparison."""
    return skill.strip().lower()


def _match_skills(
    resume_skills: list[str],
    jd_skills: list[str],
) -> tuple[list[str], list[str]]:
    """
    Compare resume skills against a list of JD skills.
    Returns (matched, missing) using the original JD skill casing.
    Handles duplicates by working with normalized sets.
    """
    resume_normalized: set[str] = {_normalize_skill(s) for s in resume_skills}

    matched: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()

    for skill in jd_skills:
        norm = _normalize_skill(skill)
        if norm in seen:
            continue  # skip duplicates in JD
        seen.add(norm)
        if norm in resume_normalized:
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing


def _calculate_skill_score(matched_count: int, total_count: int, weight: float) -> float:
    """Calculate a weighted skill score. Returns full weight if total is 0."""
    if total_count == 0:
        return weight
    return (matched_count / total_count) * weight


def _parse_years_from_requirement(requirement: str) -> float | None:
    """
    Extract a numeric year value from a JD experience requirement string.
    Examples: "3+ years", "5-7 years", "2 years".
    Returns the minimum number found, or None if unparsable.
    """
    # Match patterns like "3+", "5-7", or standalone numbers before "year"
    match = re.search(r"(\d+)", requirement)
    if match:
        return float(match.group(1))
    return None


def _estimate_candidate_experience_years(resume: Resume) -> float | None:
    """
    Estimate total years of experience from the resume's experience entries.
    Returns None if dates are missing or unparsable.
    """
    if not resume.experience:
        return 0.0

    total_years: float = 0.0
    has_any_dates: bool = False

    for exp in resume.experience:
        start = _parse_date(exp.start_date)
        end = _parse_date(exp.end_date)

        if start is None:
            continue

        has_any_dates = True

        if end is None:
            # Assume current role
            end = datetime.now()

        delta_years = (end - start).days / 365.25
        if delta_years > 0:
            total_years += delta_years

    if not has_any_dates:
        return None

    return round(total_years, 1)


def _parse_date(date_str: str | None) -> datetime | None:
    """Try to parse a date string in common resume formats."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Check for present/current role indicators
    if date_str.lower() in {"present", "current", "now", "ongoing", "till date", "today"}:
        return datetime.now()

    # Common formats to try
    formats = [
        "%Y-%m",      # 2020-06
        "%Y-%m-%d",   # 2020-06-15
        "%B %Y",      # June 2020
        "%b %Y",      # Jun 2020
        "%Y",         # 2020
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None



def _calculate_experience_score(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """
    Calculate experience score and match description.
    Returns (score, match_description).
    """
    if not jd.experience_required:
        return WEIGHT_EXPERIENCE, "No experience requirement specified"

    required_years = _parse_years_from_requirement(jd.experience_required)
    if required_years is None:
        return WEIGHT_EXPERIENCE, f"Could not parse requirement: {jd.experience_required}"

    candidate_years = _estimate_candidate_experience_years(resume)

    if candidate_years is None:
        return WEIGHT_EXPERIENCE * 0.5, (
            f"Cannot determine candidate experience (missing dates); "
            f"requirement is {jd.experience_required}"
        )

    if candidate_years >= required_years:
        return WEIGHT_EXPERIENCE, (
            f"Meets requirement: {candidate_years} years >= {required_years} years required"
        )

    # Proportional score for partial match
    ratio = candidate_years / required_years if required_years > 0 else 1.0
    score = ratio * WEIGHT_EXPERIENCE
    return score, (
        f"Below requirement: {candidate_years} years < {required_years} years required"
    )


def _calculate_education_score(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """
    Calculate education score and match description.
    Returns (score, match_description).
    """
    if not jd.education_required:
        return WEIGHT_EDUCATION, "No education requirement specified"

    if not resume.education:
        return 0.0, f"No education listed; requirement is {jd.education_required}"

    # Simple check: does any education entry's degree or field
    # loosely match the JD requirement?
    jd_req_lower = jd.education_required.lower()

    for edu in resume.education:
        edu_text = " ".join(
            part for part in [edu.degree, edu.field, edu.institution]
            if part
        ).lower()
        # Check if key terms from the requirement appear in the education
        if _has_education_overlap(jd_req_lower, edu_text):
            return WEIGHT_EDUCATION, (
                f"Education matches: {edu.degree or ''} {edu.field or ''} "
                f"from {edu.institution}"
            )

    return 0.0, (
        f"Education does not match requirement: {jd.education_required}"
    )


def _has_education_overlap(requirement: str, education: str) -> bool:
    """
    Check if key terms from the requirement appear in the education string.
    Uses simple keyword matching.
    """
    # Extract meaningful words (3+ characters)
    req_words = {w for w in re.findall(r"[a-z]+", requirement) if len(w) >= 3}
    edu_words = {w for w in re.findall(r"[a-z]+", education) if len(w) >= 3}

    if not req_words:
        return True

    # If at least half the requirement keywords appear in education text
    overlap = req_words & edu_words
    return len(overlap) >= len(req_words) * 0.4


def _get_verdict(score: float) -> str:
    """Determine the verdict based on the score."""
    if score >= VERDICT_STRONG_MIN:
        return "Strong Match"
    elif score >= VERDICT_MODERATE_MIN:
        return "Moderate Match"
    elif score >= VERDICT_WEAK_MIN:
        return "Weak Match"
    else:
        return "Poor Match"


def match_resume_to_job(resume: Resume, jd: JobDescription) -> MatchResult:
    """
    Compare a structured Resume against a structured JobDescription.
    Returns a deterministic MatchResult with score, verdict, and details.
    """
    # --- Skill matching ---
    matched_required, missing_required = _match_skills(
        resume.skills, jd.required_skills
    )
    matched_preferred, missing_preferred = _match_skills(
        resume.skills, jd.preferred_skills
    )

    total_required = len(set(_normalize_skill(s) for s in jd.required_skills))
    total_preferred = len(set(_normalize_skill(s) for s in jd.preferred_skills))

    required_score = _calculate_skill_score(
        len(matched_required), total_required, WEIGHT_REQUIRED_SKILLS
    )
    preferred_score = _calculate_skill_score(
        len(matched_preferred), total_preferred, WEIGHT_PREFERRED_SKILLS
    )

    # --- Experience matching ---
    experience_score, experience_match = _calculate_experience_score(resume, jd)

    # --- Education matching ---
    education_score, education_match = _calculate_education_score(resume, jd)

    # --- Final score ---
    raw_score = required_score + preferred_score + experience_score + education_score
    final_score = round(min(raw_score, 100.0), 1)

    return MatchResult(
        score=final_score,
        verdict=_get_verdict(final_score),
        matched_required_skills=matched_required,
        missing_required_skills=missing_required,
        matched_preferred_skills=matched_preferred,
        missing_preferred_skills=missing_preferred,
        experience_match=experience_match,
        education_match=education_match,
        score_breakdown=ScoreBreakdown(
            required_skills_score=round(required_score, 1),
            preferred_skills_score=round(preferred_score, 1),
            experience_score=round(experience_score, 1),
            education_score=round(education_score, 1),
        ),
    )
