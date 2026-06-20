"""
Sentiment analysis service using Google Gemini API.
Classifies comments as Positive, Negative, or Neutral with confidence scores.
"""

import os
import json
import asyncio
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from backend.models.schemas import (
    CommentInput, SentimentResult, BatchSentimentResult,
    SentimentStats, SentimentLabel
)
from backend.utils.preprocessor import preprocess_for_analysis

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# Rate limiting: ~15 requests/min for free tier → ~4s between calls
RATE_LIMIT_DELAY = 4.0
BATCH_SIZE = 5


def _build_single_prompt(text: str) -> str:
    """Build the Gemini prompt for single comment sentiment analysis."""
    return f"""You are an expert sentiment analyst for government policy consultations.
Analyze the following stakeholder comment submitted to India's Ministry of Corporate Affairs (MCA) eConsultation portal.

Classify the sentiment as exactly one of: Positive, Negative, or Neutral.
- Positive: The commenter supports, appreciates, or agrees with the proposed provision.
- Negative: The commenter opposes, criticizes, or expresses concern about the provision.
- Neutral: The commenter makes a factual observation, asks a question, or provides information without clear sentiment.

Provide a confidence score between 0.0 and 1.0.
Provide a brief one-sentence reasoning for your classification.

Comment:
\"\"\"{text}\"\"\"

Respond in ONLY valid JSON format (no markdown, no code fences):
{{"sentiment": "Positive|Negative|Neutral", "confidence": 0.0, "reasoning": "..."}}"""


def _build_batch_prompt(comments: list[tuple[int, str]]) -> str:
    """Build the Gemini prompt for batch comment sentiment analysis."""
    comments_text = "\n\n".join(
        f"[Comment {idx}]:\n\"\"\"{text}\"\"\"" for idx, text in comments
    )
    
    return f"""You are an expert sentiment analyst for government policy consultations.
Analyze each of the following stakeholder comments submitted to India's Ministry of Corporate Affairs (MCA) eConsultation portal.

For each comment, classify the sentiment as exactly one of: Positive, Negative, or Neutral.
- Positive: The commenter supports, appreciates, or agrees with the proposed provision.
- Negative: The commenter opposes, criticizes, or expresses concern about the provision.
- Neutral: The commenter makes a factual observation, asks a question, or provides information without clear sentiment.

Provide a confidence score between 0.0 and 1.0.
Provide a brief one-sentence reasoning for each.

{comments_text}

Respond in ONLY valid JSON format (no markdown, no code fences).
Return a JSON array with one object per comment, in the same order:
[{{"comment_index": 0, "sentiment": "Positive|Negative|Neutral", "confidence": 0.0, "reasoning": "..."}}]"""


def _parse_gemini_json(text: str) -> dict | list:
    """Parse JSON from Gemini response, handling markdown code fences."""
    cleaned = text.strip()
    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split('\n')
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = '\n'.join(lines)
    
    return json.loads(cleaned)


async def analyze_single(comment: CommentInput) -> SentimentResult:
    """
    Analyze sentiment of a single comment using Gemini.
    
    Args:
        comment: The comment to analyze
        
    Returns:
        SentimentResult with sentiment label, confidence, and reasoning
    """
    cleaned_text = preprocess_for_analysis(comment.text)
    prompt = _build_single_prompt(cleaned_text)
    
    try:
        response = model.generate_content(prompt)
        result = _parse_gemini_json(response.text)
        
        return SentimentResult(
            text=comment.text,
            stakeholder_name=comment.stakeholder_name,
            section=comment.section,
            sentiment=SentimentLabel(result["sentiment"]),
            confidence=min(max(float(result["confidence"]), 0.0), 1.0),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Gemini sentiment analysis failed: {e}")
        # Fallback: return Neutral with low confidence
        return SentimentResult(
            text=comment.text,
            stakeholder_name=comment.stakeholder_name,
            section=comment.section,
            sentiment=SentimentLabel.NEUTRAL,
            confidence=0.0,
            reasoning=f"Analysis failed: {str(e)}"
        )


async def analyze_batch(comments: list[CommentInput]) -> BatchSentimentResult:
    """
    Analyze sentiment of multiple comments in batches of BATCH_SIZE.
    Falls back to single analysis if batch parsing fails.
    
    Args:
        comments: List of comments to analyze
        
    Returns:
        BatchSentimentResult with individual results and aggregate statistics
    """
    all_results: list[SentimentResult] = []
    
    # Process in batches
    for i in range(0, len(comments), BATCH_SIZE):
        batch = comments[i:i + BATCH_SIZE]
        batch_with_idx = [(j, preprocess_for_analysis(c.text)) for j, c in enumerate(batch)]
        prompt = _build_batch_prompt(batch_with_idx)
        
        try:
            response = model.generate_content(prompt)
            results = _parse_gemini_json(response.text)
            
            if not isinstance(results, list):
                raise ValueError("Expected a JSON array from Gemini")
            
            for j, item in enumerate(results):
                if j < len(batch):
                    all_results.append(SentimentResult(
                        text=batch[j].text,
                        stakeholder_name=batch[j].stakeholder_name,
                        section=batch[j].section,
                        sentiment=SentimentLabel(item["sentiment"]),
                        confidence=min(max(float(item["confidence"]), 0.0), 1.0),
                        reasoning=item.get("reasoning", "")
                    ))
            
        except Exception as e:
            logger.warning(f"Batch sentiment failed, falling back to single: {e}")
            # Fallback: analyze one by one
            for comment in batch:
                result = await analyze_single(comment)
                all_results.append(result)
                await asyncio.sleep(RATE_LIMIT_DELAY)
        
        # Rate limiting between batches
        if i + BATCH_SIZE < len(comments):
            await asyncio.sleep(RATE_LIMIT_DELAY)
    
    # Calculate statistics
    stats = _calculate_stats(all_results)
    
    return BatchSentimentResult(results=all_results, statistics=stats)


def _calculate_stats(results: list[SentimentResult]) -> SentimentStats:
    """Calculate aggregate sentiment statistics from results."""
    total = len(results)
    if total == 0:
        return SentimentStats(
            total=0, positive_count=0, negative_count=0, neutral_count=0,
            positive_pct=0.0, negative_pct=0.0, neutral_pct=0.0
        )
    
    pos = sum(1 for r in results if r.sentiment == SentimentLabel.POSITIVE)
    neg = sum(1 for r in results if r.sentiment == SentimentLabel.NEGATIVE)
    neu = sum(1 for r in results if r.sentiment == SentimentLabel.NEUTRAL)
    
    return SentimentStats(
        total=total,
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        positive_pct=round((pos / total) * 100, 1),
        negative_pct=round((neg / total) * 100, 1),
        neutral_pct=round((neu / total) * 100, 1)
    )
     
