"""Shared constants for W2 FactsBuilder workers.

This module provides shared constants used across multiple W2 FactsBuilder
modules to maintain a single source of truth and avoid duplication.

TC-1050-T3: Extract Stopwords to Shared Constant
"""

# Stopwords for text tokenization and filtering
# Used by embeddings.py and map_evidence.py for semantic analysis
STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
