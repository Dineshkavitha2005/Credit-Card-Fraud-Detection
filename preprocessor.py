"""
Transaction Preprocessor Module
Re-exported from backend.ml.preprocessor for backward compatibility.
"""
import sys
import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.ml.preprocessor import *  # noqa: F401, F403
