"""
Text preprocessing utilities for the eConsultation Sentiment Analysis System.
Handles text cleaning, stopword removal, and preparation for NLP analysis.
"""

import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


def ensure_nltk_data():
    """Download required NLTK data if not already present."""
    resources = ['stopwords', 'punkt', 'punkt_tab', 'wordnet']
    for resource in resources:
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass


# Legal/MCA-specific stopwords to filter out boilerplate language
LEGAL_STOPWORDS = {
    'pursuant', 'whereas', 'hereinafter', 'thereof', 'herein', 'hereby',
    'aforesaid', 'notwithstanding', 'foregoing', 'hereunder', 'therein',
    'thereto', 'thereunder', 'shall', 'may', 'must', 'would', 'could',
    'section', 'subsection', 'clause', 'provision', 'act', 'rule',
    'regulation', 'amendment', 'proposed', 'existing', 'current',
    'company', 'companies', 'ministry', 'corporate', 'affairs',
    'government', 'india', 'consultation', 'comment', 'feedback',
    'stakeholder', 'suggestion', 'recommendation', 'submission',
    'draft', 'notification', 'gazette', 'circular', 'order',
    'compliance', 'also', 'would', 'like', 'make', 'made',
    'one', 'two', 'three', 'first', 'second', 'third',
    'per', 'etc', 'viz', 'ie', 'eg', 'note', 'refer',
    'respect', 'regard', 'regards', 'reference', 'mentioned',
}


def clean_text(text: str) -> str:
    """
    Clean raw text by removing HTML, special characters, and normalizing whitespace.
    
    Args:
        text: Raw input text
        
    Returns:
        Cleaned text string
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', ' ', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,;:!?\'-]', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def remove_stopwords(text: str, include_legal: bool = True) -> str:
    """
    Remove English stopwords and optionally legal boilerplate terms.
    
    Args:
        text: Input text
        include_legal: Whether to also remove legal/MCA-specific stopwords
        
    Returns:
        Text with stopwords removed
    """
    ensure_nltk_data()
    
    stop_words = set(stopwords.words('english'))
    if include_legal:
        stop_words.update(LEGAL_STOPWORDS)
    
    tokens = word_tokenize(text.lower())
    filtered = [word for word in tokens if word.isalpha() and word not in stop_words and len(word) > 2]
    
    return ' '.join(filtered)


def lemmatize_text(text: str) -> str:
    """
    Lemmatize text to reduce words to their base form.
    
    Args:
        text: Input text
        
    Returns:
        Lemmatized text
    """
    ensure_nltk_data()
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(text.lower())
    lemmatized = [lemmatizer.lemmatize(word) for word in tokens if word.isalpha()]
    return ' '.join(lemmatized)


def preprocess_for_wordcloud(text: str) -> str:
    """
    Full preprocessing pipeline for word cloud generation.
    Cleans text → removes stopwords → lemmatizes.
    
    Args:
        text: Raw input text
        
    Returns:
        Fully preprocessed text ready for TF-IDF / word cloud
    """
    cleaned = clean_text(text)
    no_stops = remove_stopwords(cleaned, include_legal=True)
    lemmatized = lemmatize_text(no_stops)
    return lemmatized


def preprocess_for_analysis(text: str) -> str:
    """
    Light preprocessing for sentiment/summary analysis.
    Only cleans HTML and normalizes whitespace — preserves meaning for AI.
    
    Args:
        text: Raw input text
        
    Returns:
        Lightly cleaned text
    """
    return clean_text(text)
