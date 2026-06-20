"""
Word cloud generation service using TF-IDF and the wordcloud library.
Generates word cloud images and extracts top keywords from comments.
"""

import io
import base64
import logging
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from backend.models.schemas import (
    WordCloudResult, SentimentWordCloudResult,
    KeywordScore, SentimentLabel
)
from backend.utils.preprocessor import preprocess_for_wordcloud

logger = logging.getLogger(__name__)

# Word cloud styling
WORDCLOUD_CONFIG = {
    'width': 800,
    'height': 400,
    'background_color': '#0f1117',
    'colormap': 'cool',
    'max_words': 100,
    'min_font_size': 10,
    'max_font_size': 80,
    'prefer_horizontal': 0.7,
    'relative_scaling': 0.5,
    'margin': 10,
}

# Per-sentiment color schemes
SENTIMENT_COLORS = {
    SentimentLabel.POSITIVE: 'Greens',
    SentimentLabel.NEGATIVE: 'Reds',
    SentimentLabel.NEUTRAL: 'Blues',
}


def _extract_keywords(texts: list[str], top_n: int = 20) -> list[KeywordScore]:
    """
    Extract top keywords using TF-IDF scoring.
    
    Args:
        texts: List of preprocessed text strings
        top_n: Number of top keywords to return
        
    Returns:
        List of KeywordScore with keyword and TF-IDF score
    """
    if not texts or all(t.strip() == '' for t in texts):
        return []
    
    try:
        vectorizer = TfidfVectorizer(
            max_features=200,
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,
            max_df=0.95,
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # Sum TF-IDF scores across all documents for each feature
        scores = tfidf_matrix.sum(axis=0).A1
        
        # Sort by score descending
        keyword_scores = sorted(
            zip(feature_names, scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        # Normalize scores to 0-1 range
        if keyword_scores:
            max_score = keyword_scores[0][1]
            if max_score > 0:
                keyword_scores = [
                    (kw, round(score / max_score, 3))
                    for kw, score in keyword_scores
                ]
        
        return [KeywordScore(keyword=kw, score=score) for kw, score in keyword_scores]
    
    except Exception as e:
        logger.error(f"TF-IDF extraction failed: {e}")
        return []


def _generate_cloud_image(word_scores: dict[str, float], colormap: str = 'cool') -> str:
    """
    Generate a word cloud PNG and return as base64 string.
    
    Args:
        word_scores: Dictionary mapping words to their importance scores
        colormap: Matplotlib colormap name for coloring
        
    Returns:
        Base64-encoded PNG image string
    """
    if not word_scores:
        # Return a placeholder image
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, 'No keywords found', ha='center', va='center',
                fontsize=20, color='#666666')
        ax.set_facecolor('#0f1117')
        fig.patch.set_facecolor('#0f1117')
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='#0f1117', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    config = WORDCLOUD_CONFIG.copy()
    config['colormap'] = colormap
    
    wc = WordCloud(**config)
    wc.generate_from_frequencies(word_scores)
    
    # Render to PNG
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    fig.patch.set_facecolor('#0f1117')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#0f1117', edgecolor='none', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    
    return base64.b64encode(buf.read()).decode('utf-8')


async def generate_wordcloud(comments: list[str]) -> WordCloudResult:
    """
    Generate a word cloud from a list of comment texts.
    
    Pipeline:
    1. Preprocess each comment (clean → remove stopwords → lemmatize)
    2. Run TF-IDF to extract keyword importance
    3. Generate word cloud PNG image
    4. Return base64 image + top 20 keywords
    """
    # Preprocess all comments
    processed = [preprocess_for_wordcloud(c) for c in comments]
    processed = [p for p in processed if p.strip()]
    
    if not processed:
        return WordCloudResult(
            image_base64=_generate_cloud_image({}),
            top_keywords=[]
        )
    
    # Extract keywords via TF-IDF
    keywords = _extract_keywords(processed, top_n=20)
    
    # Build frequency dict for word cloud
    word_scores = {kw.keyword: kw.score for kw in keywords}
    
    # Also add individual word frequencies for a richer cloud
    all_words = ' '.join(processed).split()
    word_freq = {}
    for word in all_words:
        if len(word) > 2:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Merge TF-IDF scores with raw frequencies (TF-IDF weighted higher)
    combined = {}
    max_freq = max(word_freq.values()) if word_freq else 1
    for word, freq in word_freq.items():
        tfidf_score = word_scores.get(word, 0)
        combined[word] = tfidf_score * 2 + (freq / max_freq)
    
    # Generate image
    image_b64 = _generate_cloud_image(combined)
    
    return WordCloudResult(
        image_base64=image_b64,
        top_keywords=keywords
    )


async def generate_by_sentiment(
    comments: list[str],
    sentiments: list[SentimentLabel]
) -> SentimentWordCloudResult:
    """
    Generate separate word clouds for each sentiment category.
    
    Args:
        comments: List of comment texts
        sentiments: Corresponding sentiment labels
        
    Returns:
        SentimentWordCloudResult with separate clouds for positive/negative/neutral
    """
    # Group comments by sentiment
    grouped: dict[SentimentLabel, list[str]] = {
        SentimentLabel.POSITIVE: [],
        SentimentLabel.NEGATIVE: [],
        SentimentLabel.NEUTRAL: [],
    }
    
    for comment, sentiment in zip(comments, sentiments):
        grouped[sentiment].append(comment)
    
    result = SentimentWordCloudResult()
    
    for sentiment, group_comments in grouped.items():
        if group_comments:
            processed = [preprocess_for_wordcloud(c) for c in group_comments]
            processed = [p for p in processed if p.strip()]
            
            if processed:
                keywords = _extract_keywords(processed, top_n=15)
                word_scores = {kw.keyword: kw.score for kw in keywords}
                colormap = SENTIMENT_COLORS.get(sentiment, 'cool')
                image_b64 = _generate_cloud_image(word_scores, colormap)
                
                cloud = WordCloudResult(
                    image_base64=image_b64,
                    top_keywords=keywords
                )
                
                if sentiment == SentimentLabel.POSITIVE:
                    result.positive = cloud
                elif sentiment == SentimentLabel.NEGATIVE:
                    result.negative = cloud
                else:
                    result.neutral = cloud
    
    return result
