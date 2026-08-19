from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.evaluate import router as evaluate_router
from app.core.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Resume Evaluator API starting up")
    yield
    logger.info("Resume Evaluator API shutting down")


app = FastAPI(
    title="Resume Evaluator API",
    description="API for parsing, extracting, and evaluating resumes against job descriptions.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluate_router)

# Serve the frontend UI
_static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend single-page application."""
    return FileResponse(str(_static_dir / "index.html"))



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent leaking stack traces to clients."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=False)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Health check endpoint to ensure the application is running.
    """
    return {"status": "healthy"}
