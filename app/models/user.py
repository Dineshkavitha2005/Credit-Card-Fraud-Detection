from datetime import datetime, timedelta
import bcrypt
import secrets
from flask_login import UserMixin
from app.extensions import db

class User(UserMixin, db.Model):
    """User model with secure password management and OAuth identity linking"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
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
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    auth_provider = db.Column(db.String(50), default='local')
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cards = db.relationship('UserCard', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, foreign_keys='Transaction.user_id')
    identities = db.relationship('UserIdentity', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash password using bcrypt"""
        if not password:
            self.password_hash = None
            return
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against hash. Safely returns False if user has no password set."""
        if not self.password_hash or not password or self.password_hash.startswith('!'):
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False

    @property
    def has_password(self):
        """Check if user has a valid local password configured"""
        return bool(self.password_hash and not self.password_hash.startswith('!'))

    @property
    def has_google_linked(self):
        """Check if user has a linked Google account"""
        if self.google_id:
            return True
        return any(ident.provider == 'google' for ident in (self.identities or []))

    @property
    def google_email(self):
        """Return email associated with linked Google account if available"""
        for ident in (self.identities or []):
            if ident.provider == 'google' and ident.provider_email:
                return ident.provider_email
        return self.email if self.has_google_linked else None
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserIdentity(db.Model):
    """Federated / OAuth User Identity mappings (e.g. Google)"""
    __tablename__ = 'user_identities'
    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_subject', name='uq_user_identity_provider_subject'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, default='google', index=True)
    provider_subject = db.Column(db.String(255), nullable=False, index=True)  # e.g. Google 'sub' claim
    provider_email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserIdentity {self.provider}:{self.provider_subject} -> User {self.user_id}>'


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
    failure_reason = db.Column(db.String(100))
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
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    action_description = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='success')
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
    notification_type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
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
