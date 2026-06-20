"""
File upload handler for CSV and Excel files.
Auto-detects comment, stakeholder, and section columns.
"""

import os
import pandas as pd
from fastapi import UploadFile, HTTPException
from backend.models.schemas import CommentInput, DetectedColumns, FileUploadResponse


# Maximum upload size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Keywords to detect column types (case-insensitive)
COMMENT_KEYWORDS = [
    'comment', 'comments', 'feedback', 'remark', 'remarks', 'observation',
    'observations', 'suggestion', 'suggestions', 'response', 'opinion',
    'input', 'text', 'message', 'content', 'description', 'note', 'notes',
    'submission', 'view', 'views', 'concern', 'concerns'
]

STAKEHOLDER_KEYWORDS = [
    'stakeholder', 'name', 'author', 'submitted_by', 'submitter',
    'organization', 'organisation', 'org', 'entity', 'person',
    'respondent', 'participant', 'contributor', 'from', 'user'
]

SECTION_KEYWORDS = [
    'section', 'provision', 'clause', 'rule', 'article', 'chapter',
    'topic', 'category', 'subject', 'area', 'part', 'heading',
    'regulation', 'item', 'point', 'reference'
]


def _match_column(columns: list[str], keywords: list[str]) -> str | None:
    """
    Find the best matching column name from a list of keywords.
    Tries exact match first, then substring match.
    """
    col_lower = {col: col.lower().strip().replace(' ', '_') for col in columns}
    
    # Exact match
    for col, normalized in col_lower.items():
        if normalized in keywords:
            return col
    
    # Substring match
    for col, normalized in col_lower.items():
        for keyword in keywords:
            if keyword in normalized or normalized in keyword:
                return col
    
    return None


def detect_columns(df: pd.DataFrame) -> DetectedColumns:
    """
    Auto-detect comment, stakeholder, and section columns from dataframe.
    
    Raises HTTPException if no comment column can be identified.
    """
    columns = list(df.columns)
    
    comment_col = _match_column(columns, COMMENT_KEYWORDS)
    stakeholder_col = _match_column(
        [c for c in columns if c != comment_col],
        STAKEHOLDER_KEYWORDS
    )
    section_col = _match_column(
        [c for c in columns if c not in (comment_col, stakeholder_col)],
        SECTION_KEYWORDS
    )
    
    # Fallback: if no comment column detected, use the column with the longest average text
    if comment_col is None:
        text_cols = df.select_dtypes(include=['object']).columns
        if len(text_cols) > 0:
            avg_lengths = {col: df[col].astype(str).str.len().mean() for col in text_cols}
            comment_col = max(avg_lengths, key=avg_lengths.get)
        else:
            raise HTTPException(
                status_code=400,
                detail="Could not detect a comment column in the uploaded file. "
                       "Please ensure your file has a column with comments/feedback."
            )
    
    return DetectedColumns(
        comment_column=comment_col,
        stakeholder_column=stakeholder_col,
        section_column=section_col
    )


async def read_uploaded_file(file: UploadFile) -> pd.DataFrame:
    """
    Read an uploaded CSV or Excel file into a pandas DataFrame.
    
    Validates file type and size before reading.
    """
    # Validate file extension
    filename = file.filename.lower()
    if not filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a CSV or Excel (.xlsx/.xls) file."
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
        )
    
    # Parse file
    try:
        if filename.endswith('.csv'):
            from io import StringIO
            df = pd.read_csv(StringIO(content.decode('utf-8')))
        else:
            from io import BytesIO
            df = pd.read_excel(BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {str(e)}"
        )
    
    # Validate content
    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    
    # Drop rows where all values are NaN
    df = df.dropna(how='all')
    
    return df


def extract_comments(df: pd.DataFrame, columns: DetectedColumns) -> list[CommentInput]:
    """
    Extract structured comments from a DataFrame using detected column mappings.
    """
    comments = []
    
    for _, row in df.iterrows():
        text = str(row.get(columns.comment_column, '')).strip()
        if not text or text.lower() == 'nan':
            continue
        
        stakeholder = None
        if columns.stakeholder_column:
            val = str(row.get(columns.stakeholder_column, '')).strip()
            stakeholder = val if val and val.lower() != 'nan' else None
        
        section = None
        if columns.section_column:
            val = str(row.get(columns.section_column, '')).strip()
            section = val if val and val.lower() != 'nan' else None
        
        comments.append(CommentInput(
            text=text,
            stakeholder_name=stakeholder,
            section=section
        ))
    
    return comments


def get_preview(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """Return the first n rows of the dataframe as a list of dicts."""
    preview_df = df.head(n).fillna('')
    return preview_df.to_dict(orient='records')


async def process_upload(file: UploadFile) -> FileUploadResponse:
    """
    Full upload processing pipeline:
    1. Read file
    2. Detect columns
    3. Extract comments
    4. Return structured response with preview
    """
    df = await read_uploaded_file(file)
    columns = detect_columns(df)
    comments = extract_comments(df, columns)
    preview = get_preview(df)
    
    return FileUploadResponse(
        filename=file.filename,
        total_rows=len(df),
        detected_columns=columns,
        preview=preview,
        comments=comments
    )
