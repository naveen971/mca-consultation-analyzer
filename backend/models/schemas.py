"""
Pydantic models for the eConsultation Sentiment Analysis System.
Defines request/response schemas for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class SentimentLabel(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


# ── Request Models ─────────────────────────────────────────────────────────

class CommentInput(BaseModel):
    """Single comment input with optional metadata."""
    text: str = Field(..., min_length=1, description="The comment text to analyze")
    stakeholder_name: Optional[str] = Field(None, description="Name of the stakeholder")
    section: Optional[str] = Field(None, description="Section/provision being commented on")


class BatchCommentInput(BaseModel):
    """Batch of comments for analysis."""
    comments: list[CommentInput] = Field(..., min_length=1, description="List of comments to analyze")


class WordCloudRequest(BaseModel):
    """Request for word cloud generation."""
    comments: list[str] = Field(..., min_length=1, description="List of comment texts")


class WordCloudBySentimentRequest(BaseModel):
    """Request for per-sentiment word clouds."""
    comments: list[str] = Field(..., min_length=1, description="List of comment texts")
    sentiments: list[SentimentLabel] = Field(..., description="Corresponding sentiment for each comment")


# ── Response Models ────────────────────────────────────────────────────────

class SentimentResult(BaseModel):
    """Sentiment analysis result for a single comment."""
    text: str
    stakeholder_name: Optional[str] = None
    section: Optional[str] = None
    sentiment: SentimentLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class SentimentStats(BaseModel):
    """Aggregate sentiment statistics."""
    total: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float


class BatchSentimentResult(BaseModel):
    """Batch sentiment analysis result."""
    results: list[SentimentResult]
    statistics: SentimentStats


class SummaryResult(BaseModel):
    """Summary result for a single comment."""
    text: str
    summary: str


class BatchSummaryResult(BaseModel):
    """Batch summary result with executive summary."""
    summaries: list[SummaryResult]
    executive_summary: str


class KeywordScore(BaseModel):
    """A keyword with its TF-IDF importance score."""
    keyword: str
    score: float


class WordCloudResult(BaseModel):
    """Word cloud generation result."""
    image_base64: str = Field(..., description="Base64-encoded PNG image")
    top_keywords: list[KeywordScore]


class SentimentWordCloudResult(BaseModel):
    """Per-sentiment word cloud results."""
    positive: Optional[WordCloudResult] = None
    negative: Optional[WordCloudResult] = None
    neutral: Optional[WordCloudResult] = None


class DetectedColumns(BaseModel):
    """Detected column mappings from uploaded file."""
    comment_column: str
    stakeholder_column: Optional[str] = None
    section_column: Optional[str] = None


class FileUploadResponse(BaseModel):
    """Response after file upload and parsing."""
    filename: str
    total_rows: int
    detected_columns: DetectedColumns
    preview: list[dict]
    comments: list[CommentInput]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    service: str = "eConsultation Sentiment Analysis"


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
