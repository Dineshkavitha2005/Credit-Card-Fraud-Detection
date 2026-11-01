"""
Audit Logger Module
Re-exported from core.audit_logger
"""
try:
    from backend.core.audit_logger import *  # noqa: F401, F403
except ImportError:
    from core.audit_logger import *  # noqa: F401, F403
