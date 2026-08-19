RESUME_EXTRACTION_PROMPT = """You are a precise resume parser. Extract structured information from the resume text below.

Rules:
- Extract ONLY information that is explicitly present in the resume.
- Do NOT invent experience, skills, education, projects, or certifications.
- If a field is not present in the resume, use null or an empty list as appropriate.
- Preserve important technical skills exactly as written.
- Keep dates, company names, and institutions accurate.
- Normalize obvious formatting noise (e.g., extra bullets, decorative characters).
- For dates, use the format found in the resume (e.g., "2020", "Jan 2020", "2020-01").

Resume text:
{resume_text}"""

JOB_DESCRIPTION_EXTRACTION_PROMPT = """You are a precise job description parser. Extract structured information from the job description text below.

Rules:
- Extract requirements from the supplied job description.
- Separate required skills from preferred/nice-to-have skills when possible.
- Extract required experience level (e.g., "3+ years", "5-7 years").
- Extract education requirements if stated.
- Extract key responsibilities.
- Do NOT invent requirements that are not present in the text.
- If a field is not present, use null or an empty list as appropriate.

Job description text:
{jd_text}"""

MATCH_REASONING_PROMPT = """You are an expert hiring analyst. Explain the following resume-to-job matching result.

IMPORTANT RULES:
- Use ONLY the information supplied below. Do NOT infer or invent candidate qualifications.
- Do NOT change, recalculate, or contradict the score or verdict.
- The score and verdict provided are authoritative and final.
- If information is missing or unavailable, explicitly say so.
- Be concise, professional, and grounded in the data.

Matching Result:
- Score: {score}/100
- Verdict: {verdict}

Score Breakdown:
- Required Skills: {required_skills_score}/{required_skills_weight}
- Preferred Skills: {preferred_skills_score}/{preferred_skills_weight}
- Experience: {experience_score}/{experience_weight}
- Education: {education_score}/{education_weight}

Skill Analysis:
- Matched Required Skills: {matched_required}
- Missing Required Skills: {missing_required}
- Matched Preferred Skills: {matched_preferred}
- Missing Preferred Skills: {missing_preferred}

Experience: {experience_match}
Education: {education_match}

Provide a structured explanation with:
- A brief summary of the match quality
- Key strengths the candidate demonstrates
- Important gaps or missing qualifications
- Experience compatibility reasoning
- Education compatibility reasoning
- A concise final assessment"""
