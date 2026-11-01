"""
Centralized Exception Classes and Error Formatters for Fraud Detection Application.
"""

from datetime import datetime
from flask import jsonify, request, render_template

class APIError(Exception):
    """Base exception class for API errors."""
    def __init__(self, message, status_code=500, code="INTERNAL_SERVER_ERROR", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

    def to_dict(self):
        res = {
            "error": self.message,
            "status_code": self.status_code,
            "code": self.code,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if self.details:
            res["details"] = self.details
        return res


class BadRequestError(APIError):
    def __init__(self, message="Bad Request", details=None):
        super().__init__(message, status_code=400, code="BAD_REQUEST", details=details)


class UnauthorizedError(APIError):
    def __init__(self, message="Authentication required", details=None):
        super().__init__(message, status_code=401, code="UNAUTHORIZED", details=details)


class ForbiddenError(APIError):
    def __init__(self, message="Access forbidden", details=None):
        super().__init__(message, status_code=403, code="FORBIDDEN", details=details)


class NotFoundError(APIError):
    def __init__(self, message="Resource not found", details=None):
        super().__init__(message, status_code=404, code="NOT_FOUND", details=details)


class MethodNotAllowedError(APIError):
    def __init__(self, message="Method not allowed", details=None):
        super().__init__(message, status_code=405, code="METHOD_NOT_ALLOWED", details=details)


class ConflictError(APIError):
    def __init__(self, message="Resource conflict", details=None):
        super().__init__(message, status_code=409, code="CONFLICT", details=details)


class PayloadTooLargeError(APIError):
    def __init__(self, message="Request payload exceeds allowed limit", details=None):
        super().__init__(message, status_code=413, code="PAYLOAD_TOO_LARGE", details=details)


class UnprocessableEntityError(APIError):
    def __init__(self, message="Unprocessable entity", details=None):
        super().__init__(message, status_code=422, code="UNPROCESSABLE_ENTITY", details=details)


class ValidationError(APIError):
    def __init__(self, message="Validation error", details=None):
        super().__init__(message, status_code=422, code="VALIDATION_ERROR", details=details)


class RateLimitExceededError(APIError):
    def __init__(self, message="Too many requests. Please try again later.", details=None):
        super().__init__(message, status_code=429, code="RATE_LIMIT_EXCEEDED", details=details)


class InternalServerError(APIError):
    def __init__(self, message="An internal server error occurred", details=None):
        super().__init__(message, status_code=500, code="INTERNAL_SERVER_ERROR", details=details)


def format_error_response(message, status_code=500, code="INTERNAL_SERVER_ERROR", details=None):
    """Format consistent JSON error dictionary."""
    res = {
        "error": message,
        "status_code": status_code,
        "code": code,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if details:
        res["details"] = details
    return res


def is_json_request():
    """Determine whether the current request expects a JSON error response."""
    if request.path.startswith("/api/"):
        return True
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    if "application/json" in accept:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    return False
