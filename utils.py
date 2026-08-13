"""
Utility functions for security, email, and geolocation
"""

import smtplib
import os
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session

logger = logging.getLogger(__name__)

# ─── Email Service ──────────────────────────────────────────────────

class EmailService:
    """Handle email notifications"""
    
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply@fraudshield.com')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
    
    @classmethod
    def send_email(cls, recipient_email, subject, html_content, text_content=None):
        """Send email via SMTP"""
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = cls.SENDER_EMAIL
            message['To'] = recipient_email
            
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                message.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            message.attach(part2)
            
            with smtplib.SMTP(cls.SMTP_SERVER, cls.SMTP_PORT) as server:
                server.starttls()
                server.login(cls.SENDER_EMAIL, cls.SENDER_PASSWORD)
                server.send_message(message)
            
            logger.info(f"Email sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            return False
    
    @classmethod
    def send_verification_email(cls, user_email, verification_token, user_name):
        """Send email verification link"""
        link = f"http://localhost:5000/verify-email/{verification_token}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Welcome to FraudShield, {user_name}!</h2>
                <p>Please verify your email address to activate your account.</p>
                <p><a href="{link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Verify Email Address
                </a></p>
                <p>Or copy this link: <code>{link}</code></p>
                <p>This link expires in 7 days.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    If you didn't create this account, please ignore this email.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Verify Your FraudShield Account", html_content)
    
    @classmethod
    def send_password_reset_email(cls, user_email, reset_token, user_name):
        """Send password reset link"""
        link = f"http://localhost:5000/reset-password/{reset_token}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Reset Request</h2>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password. Click the link below to proceed:</p>
                <p><a href="{link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Reset Password
                </a></p>
                <p>Or copy this link: <code>{link}</code></p>
                <p>This link expires in 24 hours.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    If you didn't request this, please ignore this email and your password will remain unchanged.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Reset Your FraudShield Password", html_content)
    
    @classmethod
    def send_fraud_alert(cls, user_email, user_name, transaction_data, fraud_score):
        """Send fraud alert notification"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #d32f2f;">⚠️ Suspicious Transaction Alert</h2>
                <p>Hi {user_name},</p>
                <p>We detected a suspicious transaction on your account. Here are the details:</p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <p><strong>Merchant:</strong> {transaction_data.get('merchant', 'N/A')}</p>
                    <p><strong>Amount:</strong> ${transaction_data.get('amount', '0.00')}</p>
                    <p><strong>Location:</strong> {transaction_data.get('location', 'Unknown')}</p>
                    <p><strong>Risk Score:</strong> <span style="color: #d32f2f; font-weight: bold;">{fraud_score}%</span></p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <p><a href="http://localhost:5000/transactions" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Review Transaction
                </a></p>
                
                <p style="color: #999; font-size: 12px;">
                    If this was you, you can ignore this alert. If not, please contact our support team immediately.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, f"Suspicious Transaction Alert - Risk Score {fraud_score}%", html_content)
    
    @classmethod
    def send_login_alert(cls, user_email, user_name, ip_address, location, device):
        """Send login from new device/location alert"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>New Login Detected</h2>
                <p>Hi {user_name},</p>
                <p>Your account was accessed from a new device or location:</p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <p><strong>IP Address:</strong> {ip_address}</p>
                    <p><strong>Location:</strong> {location}</p>
                    <p><strong>Device:</strong> {device}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <p>If this was you, no action is needed. If you don't recognize this login, please change your password immediately.</p>
                
                <p><a href="http://localhost:5000/settings" style="background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Change Password
                </a></p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "New Login Detected on Your Account", html_content)
    
    @classmethod
    def send_password_changed_email(cls, user_email, user_name):
        """Send password change confirmation"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Changed</h2>
                <p style="color: #4CAF50;">✓ Your password has been successfully changed.</p>
                <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>If you didn't make this change, please contact us immediately.</p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Your FraudShield Password Has Been Changed", html_content)


# ─── Geolocation Service ────────────────────────────────────────────

class GeolocationService:
    """Get geolocation data from IP address"""
    
    @staticmethod
    def get_geo_data(ip_address):
        """Get geolocation info for IP address"""
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return {
                'ip': ip_address,
                'country': 'Local',
                'city': 'Local',
                'latitude': 0,
                'longitude': 0,
                'isp': 'Local'
            }
        
        try:
            # Using ip-api.com free service
            response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon,isp', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'ip': ip_address,
                        'country': data.get('country'),
                        'city': data.get('city'),
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'isp': data.get('isp'),
                        'is_vpn': False,
                        'is_proxy': False,
                        'is_tor': False
                    }
        except Exception as e:
            logger.error(f"Geolocation lookup failed: {str(e)}")
        
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'city': 'Unknown',
            'latitude': 0,
            'longitude': 0,
            'isp': 'Unknown'
        }


# ─── Security & Validation ────────────────────────────────────────

class SecurityHelper:
    """Security-related helper functions"""
    
    @staticmethod
    def is_suspicious_login(user, ip_address, current_location):
        """Check if login is suspicious based on location/IP"""
        from models import IPAddress, LoginAttempt
        
        # Check if IP is known to user
        known_ip = IPAddress.query.filter_by(user_id=user.id, ip_address=ip_address).first()
        
        # Check login history
        recent_logins = LoginAttempt.query.filter(
            LoginAttempt.username == user.username,
            LoginAttempt.success == True,
            LoginAttempt.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        # Determine suspicion score
        suspicion_score = 0
        reasons = []
        
        if not known_ip:
            suspicion_score += 30
            reasons.append("New IP address")
        
        if recent_logins:
            # Check distance between recent logins
            last_login = recent_logins[-1]
            if last_login.country and last_login.country != current_location.get('country'):
                suspicion_score += 40
                reasons.append("Geographic anomaly")
        
        is_suspicious = suspicion_score > 50
        
        return {
            'is_suspicious': is_suspicious,
            'suspicion_score': suspicion_score,
            'reasons': reasons
        }
    
    @staticmethod
    def check_password_strength(password):
        """Validate password strength"""
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password must be at least 8 characters")
        
        if len(password) >= 12:
            score += 1
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            feedback.append("Include uppercase letters")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            feedback.append("Include lowercase letters")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            feedback.append("Include numbers")
        
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            score += 1
        else:
            feedback.append("Include special characters")
        
        strength = 'weak' if score < 3 else 'fair' if score < 4 else 'good' if score < 5 else 'strong'
        
        return {
            'strength': strength,
            'score': score,
            'feedback': feedback,
            'is_valid': score >= 3
        }
    
    @staticmethod
    def is_rate_limited(identifier, endpoint, limit=5, window=60):
        """Check if identifier exceeded rate limit"""
        from flask import current_app
        if current_app and current_app.testing:
            return False

        from models import RateLimitRecord, db
        
        now = datetime.utcnow()
        record = RateLimitRecord.query.filter_by(
            identifier=identifier,
            endpoint=endpoint
        ).first()
        
        if not record:
            record = RateLimitRecord(identifier=identifier, endpoint=endpoint, request_count=1)
            db.session.add(record)
            db.session.commit()
            return False
        
        # Check if window expired
        if (now - record.first_request).seconds > window:
            record.request_count = 1
            record.first_request = now
            record.last_request = now
            record.is_limited = False
            db.session.commit()
            return False
        
        record.request_count += 1
        record.last_request = now
        record.is_limited = record.request_count > limit
        db.session.commit()
        
        return record.is_limited

    @staticmethod
    def reset_rate_limit(identifier, endpoint):
        """Reset rate limit record for identifier and endpoint"""
        from models import RateLimitRecord, db
        try:
            record = RateLimitRecord.query.filter_by(
                identifier=identifier,
                endpoint=endpoint
            ).first()
            if record:
                record.request_count = 0
                record.is_limited = False
                db.session.commit()
        except Exception:
            pass


# ─── Decorators ────────────────────────────────────────────────────

def require_email_verified(f):
    """Decorator to require email verification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        if not current_user.is_verified:
            return jsonify({'error': 'Email verification required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(limit=5, window=60):
    """Decorator for rate limiting API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            endpoint = request.endpoint
            
            if SecurityHelper.is_rate_limited(identifier, endpoint, limit, window):
                return jsonify({'error': 'Too many requests. Please try again later.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_activity(activity_type, resource_type=None, resource_id=None):
    """Decorator to log user activities"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from models import UserActivity, db
            
            try:
                result = f(*args, **kwargs)
                
                if current_user.is_authenticated:
                    activity = UserActivity(
                        user_id=current_user.id,
                        activity_type=activity_type,
                        action_description=f.__name__,
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        status='success'
                    )
                    db.session.add(activity)
                    db.session.commit()
                
                return result
            except Exception as e:
                if current_user.is_authenticated:
                    activity = UserActivity(
                        user_id=current_user.id,
                        activity_type=activity_type,
                        action_description=f.__name__,
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        status='failure',
                        error_message=str(e)
                    )
                    db.session.add(activity)
                    db.session.commit()
                raise
        
        return decorated_function
    return decorator
