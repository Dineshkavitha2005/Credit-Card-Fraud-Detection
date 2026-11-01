"""
Security, Email, Geolocation, and Report Utilities
Re-exported from backend.core.utils for backward compatibility.
"""
import sys
import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.core.utils import *  # noqa: F401, F403
