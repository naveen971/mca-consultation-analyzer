"""
API routes for summary generation.
"""

from fastapi import APIRouter
from backend.models.schemas import (
    CommentInput, BatchCommentInput,
    SummaryResult, BatchSummaryResult, ErrorResponse
)
from backend.services import summary_service

router = APIRouter(prefix="/api/summary", tags=["Summary Generation"])


@router.post(
    "/single",
    response_model=SummaryResult,
    responses={500: {"model": ErrorResponse}},
    summary="Summarize a single comment"
)
async def summarize_single(comment: CommentInput):
    """
    Generate a concise 2-3 sentence summary of a single stakeholder comment.
    """
    return await summary_service.summarize_single(comment)


@router.post(
    "/batch",
    response_model=BatchSummaryResult,
    responses={500: {"model": ErrorResponse}},
    summary="Summarize multiple comments with executive summary"
)
async def summarize_batch(batch: BatchCommentInput):
    """
    Generate individual summaries for each comment plus a 150-200 word executive summary
    synthesizing all key themes, concerns, and recommendations.
    """
    return await summary_service.summarize_batch(batch.comments)
