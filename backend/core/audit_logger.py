"""
Audit Logger Module for Credit Card Fraud Detection System
Asynchronous, secure audit logging engine with automated data sanitization.
"""

import re
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import request, current_app
from flask_login import current_user

logger = logging.getLogger(__name__)

# ─── Event Types ─────────────────────────────────────────────────────────────
class EventType:
    LOGIN = 'login'
    LOGOUT = 'logout'
    FAILED_LOGIN = 'failed_login'
    REGISTRATION = 'registration'
    PASSWORD_CHANGE = 'password_change'
    TRANSACTION_SUBMISSION = 'transaction_submission'
    FRAUD_DETECTION = 'fraud_detection'
    ADMIN_USER_CHANGE = 'admin_user_change'
    ACCOUNT_BLOCK = 'account_block'
    ACCOUNT_UNBLOCK = 'account_unblock'
    REPORT_GENERATION = 'report_generation'
    REPORT_DOWNLOAD = 'report_download'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    API_AUTH_FAILURE = 'api_auth_failure'
    
    # Google OAuth Authentication Events
    GOOGLE_LOGIN_SUCCESS = 'google_login_success'
    GOOGLE_LOGIN_FAILURE = 'google_login_failure'
    GOOGLE_ACCOUNT_CREATED = 'google_account_created'
    GOOGLE_ACCOUNT_LINKED = 'google_account_linked'
    GOOGLE_ACCOUNT_UNLINKED = 'google_account_unlinked'
    GOOGLE_LOGIN_CANCELLED = 'google_login_cancelled'

    CORE_EVENTS = [
        LOGIN, LOGOUT, FAILED_LOGIN, REGISTRATION, PASSWORD_CHANGE,
        TRANSACTION_SUBMISSION, FRAUD_DETECTION, ADMIN_USER_CHANGE,
        ACCOUNT_BLOCK, ACCOUNT_UNBLOCK, REPORT_GENERATION, REPORT_DOWNLOAD,
        SUSPICIOUS_ACTIVITY, API_AUTH_FAILURE
    ]

    OAUTH_EVENTS = [
        GOOGLE_LOGIN_SUCCESS, GOOGLE_LOGIN_FAILURE, GOOGLE_ACCOUNT_CREATED,
        GOOGLE_ACCOUNT_LINKED, GOOGLE_ACCOUNT_UNLINKED, GOOGLE_LOGIN_CANCELLED
    ]

    ALL_EVENTS = CORE_EVENTS + OAUTH_EVENTS

# Sensitive key names that must be redacted
SENSITIVE_KEYS = {
    'password', 'pass', 'passwd', 'confirm_password', 'new_password',
    'current_password', 'password_hash', 'secret', 'secret_key', 'token',
    'reset_token', 'api_key', 'authorization', 'auth', 'cvv', 'cvc',
    'ssn', 'pin', '2fa_secret', 'two_factor_secret', 'answer_hash',
    'card_encryption_key', 'private_key', 'code', 'access_token',
    'refresh_token', 'id_token', 'client_secret', 'code_verifier',
    'code_challenge'
}

# Regex to detect raw credit card numbers (13-19 digits)
CARD_NUMBER_REGEX = re.compile(
    r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b'
)

def mask_card_str(val: str) -> str:
    """Mask a credit card string to **** **** **** 1234 format"""
    if not val:
        return ""
    clean = str(val).replace(" ", "").replace("-", "").strip()
    if clean.startswith("****") or clean.startswith("••••"):
        return val
    if len(clean) < 4:
        return "**** **** **** ****"
    last4 = clean[-4:]
    return f"**** **** **** {last4}"

def redact_string(val: str) -> str:
    """Mask any embedded credit card numbers within a raw string"""
    if not isinstance(val, str):
        return val
    return CARD_NUMBER_REGEX.sub(lambda m: mask_card_str(m.group(0)), val)

def sanitize_audit_metadata(data):
    """
    Recursively sanitize metadata dictionary to ensure:
    - Never log passwords, tokens, or secret keys
    - Never log full card numbers (masked to **** **** **** 1234)
    - Convert non-serializable objects cleanly
    """
    if data is None:
        return {}
    if isinstance(data, dict):
        sanitized = {}
        for key, val in data.items():
            key_str = str(key).lower()
            if any(s_key in key_str for s_key in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif any(c_key in key_str for c_key in ['card', 'card_number', 'pan', 'cc_num', 'credit_card']):
                if isinstance(val, str) or isinstance(val, (int, float)):
                    sanitized[key] = mask_card_str(str(val))
                else:
                    sanitized[key] = sanitize_audit_metadata(val)
            else:
                sanitized[key] = sanitize_audit_metadata(val)
        return sanitized
    elif isinstance(data, (list, tuple, set)):
        return [sanitize_audit_metadata(item) for item in data]
    elif isinstance(data, str):
        return redact_string(data)
    elif isinstance(data, (int, float, bool)):
        return data
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return str(data)


class AuditLogger:
    """
    Asynchronous audit logger service.
    Persists AuditLog records asynchronously using a thread pool.
    """

    def __init__(self, app=None, max_workers=4):
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="audit_log_worker")
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

    def log_event(
        self,
        event_type: str,
        user_id: int = None,
        status: str = 'success',
        target_resource: str = None,
        ip_address: str = None,
        user_agent: str = None,
        details: dict = None,
        async_log: bool = True
    ):
        """
        Record an audit log event.
        - Sanitizes all metadata automatically
        - Auto-extracts request IP, User-Agent, Path, and User ID if context available
        - Runs asynchronously via ThreadPoolExecutor unless testing or async_log=False
        """
        # Context extraction if inside request context
        try:
            if request:
                if not ip_address:
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if ip_address and ',' in ip_address:
                        ip_address = ip_address.split(',')[0].strip()
                if not user_agent:
                    user_agent = request.headers.get('User-Agent', '')[:500]
                if not target_resource:
                    target_resource = request.path[:255]
        except RuntimeError:
            # Outside request context
            pass

        # Extract current user if available and user_id not provided
        if user_id is None:
            try:
                if current_user and getattr(current_user, 'is_authenticated', False):
                    user_id = getattr(current_user, 'id', None)
            except Exception:
                pass

        # Sanitize metadata
        safe_details = sanitize_audit_metadata(details or {})

        # Build payload
        payload = {
            'user_id': user_id,
            'event_type': event_type,
            'action': event_type,
            'target_resource': target_resource or 'system',
            'resource': (target_resource or 'system')[:100],
            'ip_address': ip_address or '127.0.0.1',
            'user_agent': user_agent or 'system',
            'status': 'success' if status in (True, 'success', 200, 201) else 'failure',
            'details': safe_details,
            'created_at': datetime.utcnow()
        }

        # Check if we should execute synchronously (e.g. testing or explicit setting)
        app_obj = (current_app._get_current_object() if current_app else None) or self.app
        is_testing = False
        if app_obj:
            is_testing = app_obj.config.get('TESTING', False)
        elif os.getenv('TESTING'):
            is_testing = True

        if not async_log or is_testing or not app_obj:
            self._write_log(app_obj, payload)
        else:
            self.executor.submit(self._write_log, app_obj, payload)

    def _write_log(self, app_obj, payload):
        """Internal helper to write log record inside Flask app context"""
        try:
            if app_obj:
                with app_obj.app_context():
                    from app.extensions import db
                    from app.models.audit import AuditLog
                    log_record = AuditLog(**payload)
                    db.session.add(log_record)
                    db.session.commit()
            else:
                from app.extensions import db
                from app.models.audit import AuditLog
                log_record = AuditLog(**payload)
                db.session.add(log_record)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to persist audit log record: {str(e)}", exc_info=True)
            try:
                from app.extensions import db
                db.session.rollback()
            except Exception:
                pass

    def shutdown(self):
        """Gracefully shut down background worker threads"""
        self.executor.shutdown(wait=True)


# Global singleton instance
audit_logger = AuditLogger()
