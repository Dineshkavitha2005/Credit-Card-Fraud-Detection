"""
Backend Machine Learning & Feature Engineering Package
Deterministic preprocessing, feature transformations, and model utilities.
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from backend.ml.preprocessor import (
        TransactionPreprocessor, FEATURE_NAMES,
        DEFAULT_CATEGORY_RISK, DEFAULT_HIGH_RISK_COUNTRIES, DEFAULT_MEDIUM_RISK_COUNTRIES
    )
except ImportError:
    from preprocessor import (
        TransactionPreprocessor, FEATURE_NAMES,
        DEFAULT_CATEGORY_RISK, DEFAULT_HIGH_RISK_COUNTRIES, DEFAULT_MEDIUM_RISK_COUNTRIES
    )

__all__ = [
    'TransactionPreprocessor',
    'FEATURE_NAMES',
    'DEFAULT_CATEGORY_RISK',
    'DEFAULT_HIGH_RISK_COUNTRIES',
    'DEFAULT_MEDIUM_RISK_COUNTRIES'
]

