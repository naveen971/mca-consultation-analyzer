"""
API routes for sentiment analysis.
"""

from fastapi import APIRouter
from backend.models.schemas import (
    CommentInput, BatchCommentInput,
    SentimentResult, BatchSentimentResult, ErrorResponse
)
from backend.services import sentiment_service

router = APIRouter(prefix="/api/sentiment", tags=["Sentiment Analysis"])


@router.post(
    "/single",
    response_model=SentimentResult,
    responses={500: {"model": ErrorResponse}},
    summary="Analyze sentiment of a single comment"
)
async def analyze_single(comment: CommentInput):
    """
    Analyze the sentiment of a single stakeholder comment.
    Returns sentiment label (Positive/Negative/Neutral), confidence score, and reasoning.
    """
    return await sentiment_service.analyze_single(comment)


@router.post(
    "/batch",
    response_model=BatchSentimentResult,
    responses={500: {"model": ErrorResponse}},
    summary="Analyze sentiment of multiple comments"
)
async def analyze_batch(batch: BatchCommentInput):
    """
    Analyze sentiment of multiple comments in optimized batches.
    Returns individual results for each comment plus aggregate statistics.
    """
    return await sentiment_service.analyze_batch(batch.comments)
