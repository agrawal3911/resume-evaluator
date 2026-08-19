from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import MAX_FILE_SIZE_BYTES, MAX_JD_LENGTH_CHARS
from app.core.logging_config import logger
from app.schemas.evaluation_response import EvaluationResponse
from app.parsers.document_parser import parse_document
from app.parsers.exceptions import DocumentParsingError, UnsupportedFormatError
from app.services.llm_service import extract_resume, extract_job_description
from app.services.matching_service import match_resume_to_job
from app.services.reasoning_service import generate_match_reasoning
from app.services.exceptions import LLMConfigurationError, LLMExtractionError

router = APIRouter(tags=["Evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a resume against a job description",
    description="""
    Upload a resume file (.pdf or .docx) and provide a job description as text.
    
    Returns a comprehensive evaluation including:
    - Deterministic match score (0-100) and verdict
    - Matched & missing required skills
    - Matched & missing preferred skills
    - Experience & education alignment
    - LLM-generated human-readable reasoning & feedback
    """,
    responses={
        400: {"description": "Invalid input, empty file, oversized content, or parsing error"},
        415: {"description": "Unsupported file format (only .pdf and .docx allowed)"},
        500: {"description": "Internal server error during LLM processing or matching"},
    },
)
async def evaluate_resume(
    jd_text: str = Form(..., description="Job Description text"),
    file: UploadFile = File(..., description="Resume file in .pdf or .docx format"),
) -> EvaluationResponse:
    logger.info("Evaluation request received")

    # 1. Validate JD input
    if not jd_text or not jd_text.strip():
        logger.warning("Evaluation rejected: Empty job description")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text cannot be empty.",
        )

    if len(jd_text) > MAX_JD_LENGTH_CHARS:
        logger.warning(f"Evaluation rejected: Job description exceeds max length ({len(jd_text)} > {MAX_JD_LENGTH_CHARS})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job description exceeds maximum allowed length of {MAX_JD_LENGTH_CHARS} characters.",
        )

    # 2. Validate file presence & filename
    if not file or not file.filename:
        logger.warning("Evaluation rejected: Missing resume file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file must be provided.",
        )

    # 3. Read file bytes and check size
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file.",
        )

    if not file_bytes or not file_bytes.strip():
        logger.warning("Evaluation rejected: Empty resume file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        logger.warning(f"Evaluation rejected: File size exceeds max limit ({len(file_bytes)} > {MAX_FILE_SIZE_BYTES} bytes)")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    # 4. Parse document into clean text
    try:
        resume_text = parse_document(file_bytes, file.filename)
        logger.info(f"Successfully parsed document format for file")
    except UnsupportedFormatError as e:
        logger.warning(f"Evaluation rejected: Unsupported file format")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )
    except DocumentParsingError as e:
        logger.warning(f"Evaluation rejected: Document parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to parse document: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse resume document: {e}",
        )

    # 5. LLM Structured Extraction
    try:
        resume_model = extract_resume(resume_text)
        jd_model = extract_job_description(jd_text)
        logger.info("LLM extraction successful")
    except LLMConfigurationError as e:
        logger.error(f"LLM Configuration Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except LLMExtractionError as e:
        logger.error(f"LLM Extraction Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during LLM extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during information extraction.",
        )

    # 6. Deterministic Matching & Scoring
    try:
        match_result = match_resume_to_job(resume_model, jd_model)
        logger.info(f"Deterministic matching complete: score={match_result.score}, verdict={match_result.verdict}")
    except Exception as e:
        logger.error(f"Matching calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Matching calculation failed: {e}",
        )

    # 7. LLM Reasoning
    try:
        reasoning = generate_match_reasoning(match_result)
        logger.info("LLM reasoning generation successful")
    except (LLMConfigurationError, LLMExtractionError) as e:
        logger.error(f"LLM Reasoning Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during reasoning generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during reasoning generation.",
        )

    logger.info("Evaluation completed successfully")
    return EvaluationResponse(
        score=match_result.score,
        verdict=match_result.verdict,
        match_result=match_result,
        reasoning=reasoning,
    )
