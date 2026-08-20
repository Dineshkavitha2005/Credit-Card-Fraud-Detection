"""
Credit Card Fraud Detection System - Entry Point
Refactored into a modular architecture under app/
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from app import (
    app, create_app, db, init_db, get_db, migrate_database_security,
    migrate_audit_logs_table, fraud_engine, sanitize_numpy_types,
    CustomJSONProvider, handle_error_response, reports_dir,
    User, UserCard, Transaction, Alert, FraudRule, BlockedCard, AuditLog,
    UserSession, LoginAttempt, IPAddress, UserActivity, EmailVerificationToken,
    PasswordResetToken, Notification, SecurityQuestion, RateLimitRecord,
    Report, SuspiciousActivity, AdminAction, CardEncryption, mask_card_number
)

if __name__ == '__main__':
    init_db()
    print("\n🔒 Credit Card Fraud Detection System")
    print("=" * 45)
    print("🌐 Server: http://127.0.0.1:5000")
    print("👤 Login:  admin / admin123")
    print("=" * 45 + "\n")
    app.run(debug=True, port=5000)
