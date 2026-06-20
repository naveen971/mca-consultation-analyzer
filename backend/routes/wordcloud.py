"""
API routes for word cloud generation.
"""

from fastapi import APIRouter
from backend.models.schemas import (
    WordCloudRequest, WordCloudBySentimentRequest,
    WordCloudResult, SentimentWordCloudResult, ErrorResponse
)
from backend.services import wordcloud_service

router = APIRouter(prefix="/api/wordcloud", tags=["Word Cloud"])


@router.post(
    "/generate",
    response_model=WordCloudResult,
    responses={500: {"model": ErrorResponse}},
    summary="Generate word cloud from comments"
)
async def generate_wordcloud(request: WordCloudRequest):
    """
    Generate a word cloud image and extract top keywords from a list of comments.
    Returns a base64-encoded PNG image and top 20 keywords with TF-IDF scores.
    """
    return await wordcloud_service.generate_wordcloud(request.comments)


@router.post(
    "/by-sentiment",
    response_model=SentimentWordCloudResult,
    responses={500: {"model": ErrorResponse}},
    summary="Generate per-sentiment word clouds"
)
async def generate_by_sentiment(request: WordCloudBySentimentRequest):
    """
    Generate separate word clouds for Positive, Negative, and Neutral comments.
    Each cloud uses a distinct color scheme.
    """
    return await wordcloud_service.generate_by_sentiment(
        request.comments, request.sentiments
    )
