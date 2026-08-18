"""
Input Validation and String Sanitization Utilities for Fraud Detection Application.
"""

import re
import math
from werkzeug.utils import secure_filename
from markupsafe import escape
from errors import BadRequestError, UnprocessableEntityError, ValidationError

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")

def sanitize_string(val):
    """
    Sanitize user-controlled string:
    - Remove null bytes
    - Trim leading/trailing whitespace
    - Escape HTML/script tags to prevent XSS
    """
    if val is None:
        return None
    if not isinstance(val, str):
        return val
    
    # Strip null bytes and control chars
    clean_str = val.replace("\x00", "").strip()
    # Escape HTML special characters
    return str(escape(clean_str))


def sanitize_payload(obj):
    """
    Recursively sanitize dicts, lists, and strings in request payloads.
    """
    if isinstance(obj, str):
        return sanitize_string(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_payload(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_payload(v) for v in obj]
    return obj


def parse_and_validate_json(request_obj, required_fields=None, field_types=None):
    """
    Safely extract JSON body from request without crashing on malformed payloads.
    Optionally validate presence of required fields and field types.
    """
    if not request_obj.is_json and request_obj.data and not request_obj.content_type.startswith("application/json"):
        raise BadRequestError("Content-Type must be application/json")

    try:
        data = request_obj.get_json(silent=True)
    except Exception as e:
        raise BadRequestError("Malformed JSON payload in request body")

    if data is None:
        if request_obj.data and len(request_obj.data) > 0:
            raise BadRequestError("Failed to parse JSON payload")
        data = {}

    if not isinstance(data, dict):
        raise BadRequestError("JSON payload must be a key-value object")

    # Required fields check
    if required_fields:
        missing = [f for f in required_fields if f not in data or data[f] is None or (isinstance(data[f], str) and data[f].strip() == "")]
        if missing:
            raise BadRequestError(f"Missing required field(s): {', '.join(missing)}")

    # Field types check
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                val = data[field]
                if expected_type in (float, int) and isinstance(val, (int, float)) and not isinstance(val, bool):
                    continue
                elif expected_type == float and isinstance(val, str):
                    try:
                        float(val)
                    except ValueError:
                        raise UnprocessableEntityError(f"Field '{field}' must be a valid number")
                elif not isinstance(val, expected_type):
                    raise UnprocessableEntityError(f"Field '{field}' must be of type {expected_type.__name__}")

    return sanitize_payload(data)


def validate_email(email_str):
    """Validate email address format."""
    if not email_str or not isinstance(email_str, str):
        raise ValidationError("Email address is required")
    clean_email = email_str.strip()
    if not EMAIL_REGEX.match(clean_email):
        raise ValidationError("Invalid email address format")
    return clean_email.lower()


def validate_username(username_str):
    """Validate username format."""
    if not username_str or not isinstance(username_str, str):
        raise ValidationError("Username is required")
    clean_user = username_str.strip()
    if not USERNAME_REGEX.match(clean_user):
        raise ValidationError("Username must be 3-50 characters long and contain only letters, numbers, underscores, dots, or hyphens")
    return clean_user


def validate_amount(amount_val, field_name="amount", min_val=0.01, allow_zero=False):
    """Validate monetary amount is numeric, finite, and within valid range."""
    if amount_val is None:
        raise ValidationError(f"'{field_name}' is required")
    
    try:
        val = float(amount_val)
    except (ValueError, TypeError):
        raise ValidationError(f"'{field_name}' must be a valid numeric amount")
        
    if math.isnan(val) or math.isinf(val):
        raise ValidationError(f"'{field_name}' cannot be NaN or Infinity")

    threshold = 0.0 if allow_zero else min_val
    if val < threshold:
        raise ValidationError(f"'{field_name}' must be greater than or equal to {threshold}")

    return round(val, 2)


def luhn_check(card_number_digits):
    """Verify card number using Luhn algorithm."""
    checksum = 0
    reverse_digits = card_number_digits[::-1]
    for i, digit_char in enumerate(reverse_digits):
        d = int(digit_char)
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def validate_card_number(card_num):
    """Validate credit card number format and Luhn checksum."""
    if not card_num or not isinstance(card_num, str):
        raise ValidationError("Card number is required")

    clean_card = card_num.strip().replace(" ", "").replace("-", "")
    
    # Support encrypted/masked formats used by app
    if clean_card.startswith("gAAAAA") or clean_card.startswith("****") or clean_card.startswith("••••"):
        return clean_card

    if not clean_card.isdigit() or len(clean_card) < 13 or len(clean_card) > 19:
        raise ValidationError("Card number must contain 13 to 19 numeric digits")

    if not luhn_check(clean_card):
        raise ValidationError("Invalid credit card number (Luhn checksum failed)")

    return clean_card


def validate_file_upload(file_obj, allowed_extensions=None, max_size_mb=10):
    """
    Validate uploaded file:
    - Verifies file presence
    - Sanitizes filename via secure_filename
    - Validates file extension
    - Validates file size
    """
    if not file_obj or file_obj.filename == "":
        raise ValidationError("No file selected for upload")

    filename = secure_filename(file_obj.filename)
    if not filename:
        raise ValidationError("Invalid filename")

    if allowed_extensions is None:
        allowed_extensions = {"csv", "pdf", "png", "jpg", "jpeg"}

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_extensions:
        raise ValidationError(f"File extension '.{ext}' is not allowed. Supported extensions: {', '.join(allowed_extensions)}")

    # Check file size if available via content_length or seeking
    file_obj.seek(0, 2)
    file_size = file_obj.tell()
    file_obj.seek(0)

    if file_size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size exceeds maximum limit of {max_size_mb}MB")

    return filename, file_size
