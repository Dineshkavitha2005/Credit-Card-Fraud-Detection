"""
Backend Core Infrastructure Package
Centralized exceptions, input validation, audit logging, and utility services.
"""
import os
import sys

# Ensure core package path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from backend.core.errors import (
        APIError, BadRequestError, UnauthorizedError, ForbiddenError,
        NotFoundError, ConflictError, UnprocessableEntityError,
        PayloadTooLargeError, RateLimitExceededError, ValidationError,
        format_error_response, is_json_request
    )
except ImportError:
    from errors import (
        APIError, BadRequestError, UnauthorizedError, ForbiddenError,
        NotFoundError, ConflictError, UnprocessableEntityError,
        PayloadTooLargeError, RateLimitExceededError, ValidationError,
        format_error_response, is_json_request
    )

try:
    from backend.core.validators import (
        validate_email, validate_password, validate_username,
        validate_card_number, validate_amount, sanitize_string,
        validate_pagination, validate_json_payload
    )
except ImportError:
    from validators import (
        validate_email, validate_password, validate_username,
        validate_card_number, validate_amount, sanitize_string,
        validate_pagination, validate_json_payload
    )

try:
    from backend.core.audit_logger import (
        audit_logger, EventType, sanitize_audit_metadata, mask_card_str
    )
except ImportError:
    from audit_logger import (
        audit_logger, EventType, sanitize_audit_metadata, mask_card_str
    )

try:
    from backend.core.utils import (
        SecurityHelper, EmailService, GeolocationService, ReportGenerator
    )
except ImportError:
    from utils import (
        SecurityHelper, EmailService, GeolocationService, ReportGenerator
    )

__all__ = [
    'APIError', 'BadRequestError', 'UnauthorizedError', 'ForbiddenError',
    'NotFoundError', 'ConflictError', 'UnprocessableEntityError',
    'PayloadTooLargeError', 'RateLimitExceededError', 'ValidationError',
    'format_error_response', 'is_json_request',
    'validate_email', 'validate_password', 'validate_username',
    'validate_card_number', 'validate_amount', 'sanitize_string',
    'validate_pagination', 'validate_json_payload',
    'audit_logger', 'EventType', 'sanitize_audit_metadata', 'mask_card_str',
    'SecurityHelper', 'EmailService', 'GeolocationService', 'ReportGenerator'
]

