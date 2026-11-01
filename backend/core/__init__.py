"""
Backend Core Infrastructure Package
Centralized exceptions, input validation, audit logging, and utility services.
"""
from .errors import (
    APIError, BadRequestError, UnauthorizedError, ForbiddenError,
    NotFoundError, ConflictError, UnprocessableEntityError,
    PayloadTooLargeError, RateLimitExceededError, ValidationError,
    format_error_response, is_json_request
)
from .validators import (
    validate_email, validate_password, validate_username,
    validate_card_number, validate_amount, sanitize_string,
    validate_pagination, validate_json_payload
)
from .audit_logger import (
    audit_logger, EventType, sanitize_audit_metadata, mask_card_str
)
from .utils import (
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
