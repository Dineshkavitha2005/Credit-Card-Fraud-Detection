"""
Database Models for Fraud Detection System
Secure user and transaction management with SQLAlchemy
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import bcrypt
import secrets
from cryptography.fernet import Fernet
import os

# Helper to automatically load .env if present
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

_load_env()

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model with secure password management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zipcode = db.Column(db.String(10))
    country = db.Column(db.String(50))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(255))
    notification_preferences = db.Column(db.JSON, default={'email': True, 'sms': False})
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cards = db.relationship('UserCard', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, foreign_keys='Transaction.user_id')
    
    def set_password(self, password):
        """Hash password using bcrypt"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserCard(db.Model):
    """User credit card information"""
    __tablename__ = 'user_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number = db.Column(db.String(255), nullable=False)  # Encrypted
    card_holder = db.Column(db.String(120), nullable=False)
    card_type = db.Column(db.String(20), default='visa')
    expiry_month = db.Column(db.Integer, nullable=False)
    expiry_year = db.Column(db.Integer, nullable=False)
    cvv = db.Column(db.String(255))  # Encrypted, never stored in plain text
    card_nickname = db.Column(db.String(50))
    is_primary = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    daily_limit = db.Column(db.Float, default=5000.0)
    monthly_limit = db.Column(db.Float, default=50000.0)
    last_used = db.Column(db.DateTime)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserCard {self.card_holder}>'


class Transaction(db.Model):
    """Transaction record"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    transaction_id = db.Column(db.String(100), unique=True, index=True)
    card_number = db.Column(db.String(255))
    card_holder = db.Column(db.String(120))
    amount = db.Column(db.Float, nullable=False)
    merchant = db.Column(db.String(120))
    category = db.Column(db.String(50))
    location = db.Column(db.String(120))
    ip_address = db.Column(db.String(50))
    device_type = db.Column(db.String(50))
    is_fraud = db.Column(db.Boolean, default=False, index=True)
    fraud_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending', index=True)
    risk_factors = db.Column(db.JSON, default=[])
    reviewed_by = db.Column(db.String(80))
    reviewed_at = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}>'


class Alert(db.Model):
    """Fraud alert"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), db.ForeignKey('transactions.transaction_id'))
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # Critical, High, Medium, Low
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Alert {self.alert_type}>'


class FraudRule(db.Model):
    """Configurable fraud detection rules"""
    __tablename__ = 'fraud_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(120), nullable=False)
    rule_type = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FraudRule {self.rule_name}>'


class BlockedCard(db.Model):
    """Blocked cards for fraud prevention"""
    __tablename__ = 'blocked_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(255), unique=True, nullable=False)
    reason = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    blocked_by = db.Column(db.String(80))
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BlockedCard {mask_card_number(self.card_number)}>'


class AuditLog(db.Model):
    """Security audit log for tracking user actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource = db.Column(db.String(100))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20), default='success')
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action}>'


class UserSession(db.Model):
    """Track active user sessions for security"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserSession {self.user_id}>'


# ─── Security & Verification Models ────────────────────────────────

class EmailVerificationToken(db.Model):
    """Email verification tokens for new users"""
    __tablename__ = 'email_verification_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    verified_at = db.Column(db.DateTime)
    
    @classmethod
    def generate_token(cls):
        """Generate secure verification token"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_verified and datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f'<EmailVerificationToken {self.user_id}>'


class PasswordResetToken(db.Model):
    """Password reset tokens for account recovery"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    used_at = db.Column(db.DateTime)
    
    @classmethod
    def generate_token(cls):
        """Generate secure reset token"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if reset token is still valid"""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f'<PasswordResetToken {self.user_id}>'


class LoginAttempt(db.Model):
    """Track login attempts for rate limiting and suspicious activity detection"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    ip_address = db.Column(db.String(50), nullable=False, index=True)
    user_agent = db.Column(db.String(255))
    success = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(100))  # wrong_password, user_not_found, account_locked, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    is_suspicious = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<LoginAttempt {self.username} from {self.ip_address}>'


class IPAddress(db.Model):
    """Track and manage IP addresses for geolocation and suspicious activity"""
    __tablename__ = 'ip_addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))
    isp = db.Column(db.String(100))
    is_vpn = db.Column(db.Boolean, default=False)
    is_proxy = db.Column(db.Boolean, default=False)
    is_tor = db.Column(db.Boolean, default=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    risk_score = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<IPAddress {self.ip_address}>'


class UserActivity(db.Model):
    """Comprehensive user activity logging for audit trail"""
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)  # login, logout, profile_change, card_add, etc.
    action_description = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    resource_type = db.Column(db.String(50))  # user, card, transaction, etc.
    resource_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='success')  # success, failure
    error_message = db.Column(db.Text)
    event_metadata = db.Column(db.JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type} by {self.user_id}>'


class Notification(db.Model):
    """Email and SMS notification queue"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notification_type = db.Column(db.String(50), nullable=False)  # fraud_alert, login_alert, password_change, etc.
    channel = db.Column(db.String(20), nullable=False)  # email, sms, push
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255))
    message = db.Column(db.Text)
    is_sent = db.Column(db.Boolean, default=False)
    attempt_count = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    sent_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    def __repr__(self):
        return f'<Notification {self.notification_type} to {self.user_id}>'


class SecurityQuestion(db.Model):
    """User security questions for account recovery"""
    __tablename__ = 'security_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    answer_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_answer(self, answer):
        """Hash security question answer"""
        self.answer_hash = bcrypt.hashpw(answer.lower().encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def check_answer(self, answer):
        """Verify security question answer"""
        return bcrypt.checkpw(answer.lower().encode('utf-8'), self.answer_hash.encode('utf-8'))
    
    def __repr__(self):
        return f'<SecurityQuestion {self.user_id}>'


class RateLimitRecord(db.Model):
    """Track API rate limiting per user/IP"""
    __tablename__ = 'rate_limit_records'
    
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(255), nullable=False, index=True)  # IP or user_id
    endpoint = db.Column(db.String(255), nullable=False)
    request_count = db.Column(db.Integer, default=0)
    first_request = db.Column(db.DateTime, default=datetime.utcnow)
    last_request = db.Column(db.DateTime, default=datetime.utcnow)
    is_limited = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<RateLimitRecord {self.identifier}>'


class Report(db.Model):
    """Generated reports (CSV, PDF) for export"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # transaction_report, fraud_report, activity_report, etc.
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    file_format = db.Column(db.String(20))  # csv, pdf
    file_size = db.Column(db.Integer)
    filters = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default='pending')  # pending, generating, completed, failed
    error_message = db.Column(db.Text)
    download_count = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Report {self.report_type} by {self.user_id}>'


class SuspiciousActivity(db.Model):
    """Log suspicious activities for analysis"""
    __tablename__ = 'suspicious_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    country = db.Column(db.String(100))
    risk_score = db.Column(db.Float, default=0.0)
    data = db.Column(db.JSON, default={})  # Extra context data
    is_reviewed = db.Column(db.Boolean, default=False)
    is_threat = db.Column(db.Boolean, default=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<SuspiciousActivity {self.activity_name}>'


class AdminAction(db.Model):
    """Track administrative actions for compliance"""
    __tablename__ = 'admin_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # user_block, card_unblock, password_reset, etc.
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    target_resource = db.Column(db.String(255))
    reason = db.Column(db.Text)
    details = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default='executed')  # executed, pending, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AdminAction {self.action_type} by {self.admin_id}>'


def mask_card_number(card_number):
    """Mask credit card number to format **** **** **** 1234"""
    if not card_number:
        return ""
    clean = str(card_number).replace(" ", "").replace("-", "").strip()
    if clean.startswith("****") or clean.startswith("••••"):
        return card_number
    if len(clean) < 4:
        return "**** **** **** ****"
    last4 = clean[-4:]
    return f"**** **** **** {last4}"


class CardEncryption:
    """Utility class for card encryption/decryption"""
    
    UNSAFE_KEYS = {
        'default-unsafe-key',
        'use_Fernet.generate_key()',
        'your_secret_key_here',
        'change_this_secret_key_in_production',
        'secret',
        'key',
        '123456',
        'password'
    }

    @staticmethod
    def validate_key():
        """Validate encryption key from environment. Raise ValueError if unsafe or missing."""
        key = os.getenv('CARD_ENCRYPTION_KEY', '').strip()
        if not key:
            raise ValueError("CARD_ENCRYPTION_KEY environment variable is missing.")
        if key in CardEncryption.UNSAFE_KEYS or len(key) < 16:
            raise ValueError("CARD_ENCRYPTION_KEY is unsafe, insecure, or using a default placeholder.")
        return key

    @staticmethod
    def get_cipher():
        """Get validated Fernet cipher instance"""
        validated_key = CardEncryption.validate_key()
        import base64
        try:
            key_bytes = validated_key.encode('utf-8')
            return Fernet(key_bytes)
        except Exception:
            import hashlib
            derived = base64.urlsafe_b64encode(hashlib.sha256(validated_key.encode('utf-8')).digest())
            return Fernet(derived)

    @staticmethod
    def encrypt_card_number(card_number):
        """Encrypt credit card number using Fernet key"""
        if not card_number:
            return card_number
        cipher = CardEncryption.get_cipher()
        return cipher.encrypt(str(card_number).encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_card_number(encrypted_card):
        """Decrypt credit card number using Fernet key"""
        if not encrypted_card:
            return encrypted_card
        cipher = CardEncryption.get_cipher()
        try:
            return cipher.decrypt(str(encrypted_card).encode('utf-8')).decode('utf-8')
        except Exception:
            return encrypted_card
