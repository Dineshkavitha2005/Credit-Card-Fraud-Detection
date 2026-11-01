"""
Sentinel Backend Application Root Package
"""
import os
import sys

# Ensure backend root and subpackages are discoverable
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import (
    create_app, app, db, init_db, get_db,
    User, UserCard, Transaction, Alert, FraudRule, BlockedCard, AuditLog,
    UserSession, LoginAttempt, IPAddress, UserActivity, EmailVerificationToken,
    PasswordResetToken, Notification, SecurityQuestion, RateLimitRecord,
    Report, SuspiciousActivity, AdminAction, CardEncryption, mask_card_number
)

__all__ = [
    'create_app', 'app', 'db', 'init_db', 'get_db',
    'User', 'UserCard', 'Transaction', 'Alert', 'FraudRule', 'BlockedCard', 'AuditLog',
    'UserSession', 'LoginAttempt', 'IPAddress', 'UserActivity', 'EmailVerificationToken',
    'PasswordResetToken', 'Notification', 'SecurityQuestion', 'RateLimitRecord',
    'Report', 'SuspiciousActivity', 'AdminAction', 'CardEncryption', 'mask_card_number'
]

