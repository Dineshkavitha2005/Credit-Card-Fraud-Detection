from datetime import datetime, timedelta
import secrets
from flask import request
from app.extensions import db, audit_logger, EventType
from app.models.user import (
    User, UserSession, LoginAttempt, EmailVerificationToken, PasswordResetToken,
    SecurityQuestion, UserActivity
)
from utils import EmailService

class AuthService:
    """Authentication and User Account management service."""

    @staticmethod
    def register_user(username, email, password, full_name=None, phone=None, address=None, city=None, state=None, zipcode=None, country=None, role='user'):
        """Register a new user account."""
        if User.query.filter_by(username=username).first():
            return None, "Username already exists"
        if User.query.filter_by(email=email).first():
            return None, "Email already registered"

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone,
            address=address,
            city=city,
            state=state,
            zipcode=zipcode,
            country=country,
            role=role,
            is_active=True,
            is_verified=False
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Generate email verification token
        token_str = EmailVerificationToken.generate_token()
        token = EmailVerificationToken(user_id=user.id, token=token_str, email=user.email)
        db.session.add(token)
        db.session.commit()

        # Send verification email asynchronously / silently
        try:
            EmailService.send_verification_email(user.email, token_str, user.username)
        except Exception:
            pass

        audit_logger.log_event(
            EventType.REGISTRATION,
            user_id=user.id,
            status='success',
            target_resource=f"User:{user.id}",
            details={'username': user.username, 'email': user.email}
        )

        return user, None

    @staticmethod
    def authenticate_user(username, password, ip_address=None, user_agent=None):
        """Authenticate user credentials and log login attempt."""
        user = User.query.filter((User.username == username) | (User.email == username)).first()

        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address or '127.0.0.1',
            user_agent=user_agent or 'unknown',
            created_at=datetime.utcnow()
        )

        if not user or not user.check_password(password):
            attempt.success = False
            attempt.failure_reason = 'invalid_credentials'
            db.session.add(attempt)
            db.session.commit()

            audit_logger.log_event(
                EventType.FAILED_LOGIN,
                user_id=user.id if user else None,
                status='failure',
                target_resource=f"User:{username}",
                details={'reason': 'invalid_credentials'}
            )
            return None, "Invalid username or password"

        if not user.is_active:
            attempt.success = False
            attempt.failure_reason = 'account_disabled'
            db.session.add(attempt)
            db.session.commit()

            audit_logger.log_event(
                EventType.FAILED_LOGIN,
                user_id=user.id,
                status='failure',
                target_resource=f"User:{user.id}",
                details={'reason': 'account_disabled'}
            )
            return None, "Account has been deactivated. Please contact support."

        attempt.success = True
        user.update_last_login()
        db.session.add(attempt)

        # Create session record
        session_token = secrets.token_hex(32)
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(user_session)
        db.session.commit()

        audit_logger.log_event(
            EventType.LOGIN,
            user_id=user.id,
            status='success',
            target_resource=f"User:{user.id}",
            details={'username': user.username}
        )

        return user, None
