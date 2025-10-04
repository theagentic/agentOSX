"""
Evaluation Metrics

Common metrics for agent evaluation.
"""

from typing import Optional


def accuracy(input: str, expected: Optional[str], actual: str, **kwargs) -> float:
    """
    Exact match accuracy.
    
    Returns 1.0 if actual matches expected, 0.0 otherwise.
    """
    if expected is None:
        return 0.0
    
    return 1.0 if actual.strip().lower() == expected.strip().lower() else 0.0


def latency(duration: float, **kwargs) -> float:
    """
    Response latency in seconds.
    
    Returns the duration directly.
    """
    return duration


def token_usage(actual: str, **kwargs) -> float:
    """
    Approximate token count.
    
    Uses simple word count estimation (1 word ≈ 1.3 tokens).
    """
    words = len(actual.split())
    return words * 1.3


def semantic_similarity(input: str, expected: Optional[str], actual: str, **kwargs) -> float:
    """
    Semantic similarity between expected and actual.
    
    Uses simple word overlap as proxy. For production, use embeddings.
    """
    if expected is None:
        return 0.0
    
    expected_words = set(expected.lower().split())
    actual_words = set(actual.lower().split())
    
    if not expected_words or not actual_words:
        return 0.0
    
    overlap = len(expected_words & actual_words)
    total = len(expected_words | actual_words)
    
    return overlap / total if total > 0 else 0.0


def response_length(actual: str, **kwargs) -> float:
    """
    Length of response in characters.
    """
    return float(len(actual))


def word_count(actual: str, **kwargs) -> float:
    """
    Number of words in response.
    """
    return float(len(actual.split()))
