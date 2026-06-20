"""
FastAPI application entry point for the eConsultation Sentiment Analysis System.
Configures CORS, mounts routers, serves static frontend, and handles file uploads.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.models.schemas import FileUploadResponse, HealthResponse, ErrorResponse
from backend.routes import sentiment, summary, wordcloud
from backend.utils.file_handler import process_upload
from backend.utils.preprocessor import ensure_nltk_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: ensure NLTK data is available
    logger.info("Starting eConsultation Sentiment Analysis System...")
    ensure_nltk_data()
    logger.info("NLTK data verified.")
    yield
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="eConsultation Sentiment Analysis API",
    description=(
        "AI-powered analysis of stakeholder comments from India's "
        "Ministry of Corporate Affairs (MCA) eConsultation portal. "
        "Features sentiment classification, summary generation, and word cloud visualization."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ─────────────────────────────────────────────────────────────

app.include_router(sentiment.router)
app.include_router(summary.router)
app.include_router(wordcloud.router)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check"
)
async def health_check():
    """Check if the API is running and healthy."""
    return HealthResponse()


@app.post(
    "/api/upload",
    response_model=FileUploadResponse,
    tags=["File Upload"],
    summary="Upload CSV or Excel file"
)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel file containing stakeholder comments.
    Auto-detects comment, stakeholder, and section columns.
    Returns a preview and extracted comments.
    """
    return await process_upload(file)


# ── Global Error Handler ──────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=str(exc.detail)).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


# ── Static Files (Frontend) ───────────────────────────────────────────────
# Mount frontend LAST so API routes take priority

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"Frontend mounted from: {frontend_dir}")
else:
    logger.warning(f"Frontend directory not found: {frontend_dir}")
