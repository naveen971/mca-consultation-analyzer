"""
Summary generation service using Google Gemini API.
Produces per-comment summaries and executive batch summaries.
"""

import os
import json
import asyncio
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from backend.models.schemas import CommentInput, SummaryResult, BatchSummaryResult
from backend.utils.preprocessor import preprocess_for_analysis

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

RATE_LIMIT_DELAY = 4.0
BATCH_SIZE = 5


def _build_single_prompt(text: str) -> str:
    """Build prompt for summarizing a single comment."""
    return f"""You are a professional summarizer for government policy consultation comments.
Summarize the following stakeholder comment submitted to India's Ministry of Corporate Affairs (MCA).

Rules:
- Write a concise summary in 2-3 sentences.
- Preserve the original meaning and key points.
- Do not add your own opinions or interpretations.
- Use neutral, professional language.
- Capture the stakeholder's main concern, suggestion, or observation.

Comment:
\"\"\"{text}\"\"\"

Respond in ONLY valid JSON format (no markdown, no code fences):
{{"summary": "Your 2-3 sentence summary here."}}"""


def _build_batch_prompt(comments: list[tuple[int, str]]) -> str:
    """Build prompt for batch comment summarization."""
    comments_text = "\n\n".join(
        f"[Comment {idx}]:\n\"\"\"{text}\"\"\"" for idx, text in comments
    )
    
    return f"""You are a professional summarizer for government policy consultation comments.
Summarize each of the following stakeholder comments submitted to India's Ministry of Corporate Affairs (MCA).

Rules for each comment summary:
- Write a concise summary in 2-3 sentences.
- Preserve the original meaning and key points.
- Do not add your own opinions or interpretations.
- Use neutral, professional language.

{comments_text}

Respond in ONLY valid JSON format (no markdown, no code fences).
Return a JSON array with one object per comment, in the same order:
[{{"comment_index": 0, "summary": "..."}}]"""


def _build_executive_prompt(summaries: list[str]) -> str:
    """Build prompt for generating an executive summary of all comments."""
    all_summaries = "\n".join(f"- {s}" for s in summaries)
    
    return f"""You are a senior policy analyst. Based on the following individual comment summaries from a public consultation conducted by India's Ministry of Corporate Affairs (MCA), write an executive summary.

Requirements:
- Length: 150-200 words
- Cover the key themes, recurring concerns, and notable recommendations
- Mention the overall sentiment balance (how many support vs. oppose vs. neutral)
- Use formal, professional language suitable for a government report
- Do NOT add information not present in the summaries

Individual Comment Summaries:
{all_summaries}

Respond in ONLY valid JSON format (no markdown, no code fences):
{{"executive_summary": "Your 150-200 word executive summary here."}}"""


def _parse_gemini_json(text: str) -> dict | list:
    """Parse JSON from Gemini response, handling markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split('\n')
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = '\n'.join(lines)
    return json.loads(cleaned)


async def summarize_single(comment: CommentInput) -> SummaryResult:
    """
    Generate a summary for a single comment.
    
    Returns:
        SummaryResult with original text and summary.
    """
    cleaned_text = preprocess_for_analysis(comment.text)
    prompt = _build_single_prompt(cleaned_text)
    
    try:
        response = model.generate_content(prompt)
        result = _parse_gemini_json(response.text)
        
        return SummaryResult(
            text=comment.text,
            summary=result["summary"]
        )
    except Exception as e:
        logger.error(f"Gemini summary generation failed: {e}")
        # Fallback: use first 100 chars as summary
        fallback = comment.text[:100] + ("..." if len(comment.text) > 100 else "")
        return SummaryResult(
            text=comment.text,
            summary=f"[Auto-truncated] {fallback}"
        )


async def summarize_batch(comments: list[CommentInput]) -> BatchSummaryResult:
    """
    Generate summaries for multiple comments + an executive summary.
    Processes in batches of BATCH_SIZE, falls back to single if batch fails.
    
    Returns:
        BatchSummaryResult with individual summaries and executive summary.
    """
    all_summaries: list[SummaryResult] = []
    
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
                    all_summaries.append(SummaryResult(
                        text=batch[j].text,
                        summary=item["summary"]
                    ))
            
        except Exception as e:
            logger.warning(f"Batch summary failed, falling back to single: {e}")
            for comment in batch:
                result = await summarize_single(comment)
                all_summaries.append(result)
                await asyncio.sleep(RATE_LIMIT_DELAY)
        
        # Rate limiting between batches
        if i + BATCH_SIZE < len(comments):
            await asyncio.sleep(RATE_LIMIT_DELAY)
    
    # Generate executive summary
    executive_summary = await _generate_executive_summary(
        [s.summary for s in all_summaries]
    )
    
    return BatchSummaryResult(
        summaries=all_summaries,
        executive_summary=executive_summary
    )


async def _generate_executive_summary(summaries: list[str]) -> str:
    """Generate an executive summary from individual comment summaries."""
    if not summaries:
        return "No comments were provided for analysis."
    
    prompt = _build_executive_prompt(summaries)
    
    try:
        response = model.generate_content(prompt)
        result = _parse_gemini_json(response.text)
        return result["executive_summary"]
    except Exception as e:
        logger.error(f"Executive summary generation failed: {e}")
        return (
            f"Executive summary generation failed. "
            f"{len(summaries)} comments were analyzed individually. "
            f"Please review the individual summaries below for key themes and concerns."
        )
