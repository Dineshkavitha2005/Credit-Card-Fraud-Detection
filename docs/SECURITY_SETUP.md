
# Security Features Setup Guide

This document outlines the comprehensive security and fraud detection features implemented in the Credit Card Fraud Detection System.

## Table of Contents
1. [New Security Features](#new-security-features)
2. [Environment Setup](#environment-setup)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Configuration](#configuration)
6. [Testing](#testing)

---

## New Security Features

### 1. Email Verification & Confirmation
**Feature:** Users must verify their email address after registration before accessing certain features.

**Flow:**
- User registers → Registration handler generates `EmailVerificationToken` (7-day expiry)
- User receives verification email with token link
- User clicks verification link → Email verified, `is_verified` flag set to `True`
- Unverified users see verification warning on dashboard

**Endpoints:**
- `POST /register` - User registration with email verification token generation
- `GET/POST /verify-email/<token>` - Validate token and verify email address

**Implementation File:** `app.py` - register and verify_email routes

**Database Model:** `EmailVerificationToken` (models.py)

---

### 2. Password Reset Functionality
**Feature:** Secure password reset with email-based token authentication.

**Flow:**
- User requests password reset at `/forgot-password`
- System generates `PasswordResetToken` (24-hour expiry)
- Reset link sent to email
- User clicks link, enters new password at `/reset-password/<token>`
- Password updated, token invalidated

**Security:**
- Tokens are single-use and expire after 24 hours
- New password must meet strength requirements
- Old password is not needed (but email must be accessible)
- Email notification sent when password is reset

**Endpoints:**
- `GET/POST /forgot-password` - Request password reset
- `GET/POST /reset-password/<token>` - Reset password with token

**Implementation File:** `app.py` - forgot_password and reset_password routes

**Database Model:** `PasswordResetToken` (models.py)

---

### 3. Session Management
**Feature:** Track all user sessions, detect concurrent logins, enable session revocation.

**Capabilities:**
- View all active sessions with IP and device info
- Revoke specific sessions remotely
- Automatic session expiration (24-hour default)
- Session tokens are cryptographically secure

**Endpoints:**
- `GET /api/login-attempts` - Get user's recent login history
- `GET /api/sessions` - List active sessions
- `POST /api/sessions/<id>/revoke` - Revoke specific session

**Implementation File:** `app.py` - session management routes

**Database Models:** `UserSession`, `LoginAttempt` (models.py)

---

### 4. IP Logging & Geolocation Tracking
**Feature:** Log all login attempts with geographic origin to detect suspicious activity.

**Capabilities:**
- Records IP address for every login attempt
- Resolves IP to geographic location (city, country, ISP)
- Detects VPN/proxy usage
- Flags logins from unusual locations

**Data Captured:**
- IP Address
- Country, City, Latitude, Longitude
- ISP name
- VPN/Proxy detection indicator
- Login success/failure status
- Timestamp

**Service:** `GeolocationService` in `utils.py`
- Uses free ip-api.com API
- Graceful fallback for localhost and private IPs
- Handles API failures gracefully

**Database Models:** `LoginAttempt`, `IPAddress` (models.py)

**Configuration:** Update geolocation service endpoint for commercial APIs

---

### 5. Rate Limiting
**Feature:** Prevent brute force attacks with per-IP rate limiting.

**Implementation:**
- API Rate Limiting: 100 requests per minute per IP
- Login Rate Limiting: 5 failed attempts per 5 minutes per IP
- Configurable limits per endpoint
- Automatic unlock after window expires

**Components:**
- `RateLimitRecord` model tracks attempts
- `@rate_limit` decorator on endpoints
- `SecurityHelper.is_rate_limited()` check method

**Configuration:**
```python
# In app.py or config file
RATE_LIMIT_CONFIG = {
    '/login': {'limit': 5, 'window': 300},
    '/api': {'limit': 100, 'window': 60},
    '/register': {'limit': 10, 'window': 3600}
}
```

**Database Model:** `RateLimitRecord` (models.py)

---

### 6. Card Encryption
**Feature:** Encrypt credit card numbers using Fernet symmetric encryption.

**Implementation:**
- Uses Python `cryptography` library (Fernet)
- 256-bit encryption with timestamp
- Automatic encryption on card save
- Automatic decryption on card retrieval

**Utility Class:** `CardEncryption` in `models.py`
```python
encrypted = CardEncryption.encrypt_card_number("4111111111111111")
decrypted = CardEncryption.decrypt_card_number(encrypted)
```

**Environment Variable:**
```
CARD_ENCRYPTION_KEY=your_32_byte_key_here
```

**Security Note:** Store encryption key in secure environment variable, never in code.

---

### 7. Comprehensive Audit Logging
**Feature:** Track all user activities and administrative actions.

**User Activity Logging:**
- Login/Logout
- Profile updates
- Card additions/deletions
- Password changes
- Email verification
- Report generation
- Settings changes

**Administrative Action Logging:**
- User blocking/unblocking
- Forced password resets
- Suspicious activity reviews
- Account recovery actions
- Data exports

**Components:**
- `UserActivity` model - User activity tracking
- `AdminAction` model - Admin action tracking
- `@log_activity` decorator - Automatic logging

**Database Models:** `UserActivity`, `AdminAction` (models.py)

**Implementation File:** `app.py` and `utils.py`

---

### 8. Email Notifications
**Feature:** Alert users about important security events.

**Notification Types:**
- Email verification confirmation
- Password reset requests
- Suspicious login alerts
- Password change confirmations
- Account recovery initiated
- Fraud alerts

**Service:** `EmailService` class in `utils.py`
- SMTP-based email sending
- HTML email templates
- Retry logic for failed sends
- Notification queue with status tracking

**Methods:**
- `send_verification_email()` - Email verification link
- `send_password_reset_email()` - Password reset token
- `send_fraud_alert()` - Fraud detection notification
- `send_login_alert()` - Suspicious login notification
- `send_password_change_confirmation()` - Password change confirmation

**Environment Variables:**
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=noreply@yourdomain.com
SENDER_PASSWORD=app_specific_password
```

**For Gmail:**
1. Enable 2FA in Google Account
2. Generate App Password
3. Use App Password as `SENDER_PASSWORD`

**Database Model:** `Notification` (models.py)

---

### 9. SMS Notifications (Framework)
**Feature:** Send SMS alerts for critical security events.

**Framework Ready:** Notification model supports SMS channel
- `notification.channel = 'sms'`
- Retry logic implemented
- Provider agnostic

**To Enable:**
1. Install Twilio: `pip install twilio`
2. Add Twilio credentials to environment
3. Extend `EmailService.send_sms()` method

**Environment Variables (Twilio):**
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

---

### 10. Data Export & Reporting
**Feature:** Generate transaction and activity reports in CSV and PDF formats.

**Report Types:**
- Transaction History (CSV/PDF)
- Activity Log (CSV/PDF)
- Custom Date Range
- Filtered by category/merchant

**Endpoints:**
- `POST /api/reports/generate` - Create new report
- `GET /api/reports/<id>` - Check report status
- `GET /api/reports/<id>/download` - Download generated report

**Report Formats:**
- CSV: Lightweight, Excel-compatible
- PDF: Formatted, professional appearance

**Framework:** `ReportLab` integration ready
- PDF generation with ReportLab
- CSV generation with pandas
- Reports expire after 7 days
- Download tracking in database

**Database Model:** `Report` (models.py)

**Implementation File:** `app.py` - report generation routes

---

### 11. Suspicious Activity Detection & Reporting
**Feature:** Identify and flag suspicious transactions and login patterns.

**Detection Triggers:**
- Geographic anomalies (impossible travel)
- Unusual transaction amounts
- Frequent small transactions
- Multiple failed login attempts
- Logins from new locations
- Transactions during unusual hours

**Admin Review Process:**
- Review suspicious activities with details
- Mark as reviewed/resolved
- Add notes about investigation
- Create follow-up actions

**Endpoints:**
- `GET /api/suspicious-activities` - List suspicious activities
- `POST /api/admin/suspicious-activities/<id>/review` - Mark as reviewed

**Database Models:** `SuspiciousActivity` (models.py)

**Implementation File:** `app.py` - suspicious activity routes

---

### 12. User Activity & Admin Management
**Feature:** Comprehensive user and admin management with audit trails.

**Admin Capabilities:**
- View all user accounts
- Block/unblock users
- Force password reset
- View user activity history
- Manage role assignments

**User Management Endpoints:**
- `GET /admin/users` - User management dashboard
- `POST /api/admin/users/<id>/block` - Block user
- `POST /api/admin/users/<id>/unblock` - Unblock user
- `POST /api/admin/users/<id>/reset-password` - Force password reset

**Admin Action Tracking:**
- All admin actions logged with timestamp
- Reason for action logged
- Used for compliance audits

**Database Models:** `AdminAction` (models.py)

**Implementation File:** `app.py` - admin management routes

---

### 13. Role-Based Access Control (RBAC)
**Feature:** Implement role-based authorization for endpoints.

**Roles:**
- `admin` - Full system access, user management
- `user` - Standard user with fraud detection services
- `moderator` - Limited admin capabilities (future)

**Implementation:**
- User.role field stores role
- `@login_required` decorator on protected routes
- Admin-only routes check `current_user.role == 'admin'`

**Example:**
```python
@app.route('/admin/users')
def admin_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    # ...
```

---

### 14. Account Recovery Options
**Feature:** Multiple account recovery methods.

**Recovery Methods:**
1. Email-based token (PasswordResetToken)
2. Security Questions answering

**Security Questions:**
- User sets up during setup
- Used if email is inaccessible
- Questions and hashed answers stored
- Used for recovery verification

**Endpoints:**
- `GET/POST /api/security-questions` - Manage security questions

**Database Model:** `SecurityQuestion` (models.py)

---

### 15. Suspicious Login Detection
**Feature:** Real-time detection of suspicious login attempts.

**Detection Algorithms:**
- Geographic anomalies (impossible travel)
- New device/browser detection
- IP address changes
- Unusual login times

**Response:**
- Email alert sent to user
- LoginAttempt logged with 'suspicious' flag
- SuspiciousActivity record created
- Can optionally require 2FA confirmation

**Implementation:** `SecurityHelper.is_suspicious_login()` in `utils.py`

---

## Environment Setup

Create a `.env` file in project root:

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=your_super_secret_key_here

# Email Configuration (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=noreply@yourcompany.com
SENDER_PASSWORD=your_app_password

# Card Encryption
CARD_ENCRYPTION_KEY=your_32_byte_base64_encoded_key

# Geolocation (Optional - uses free ip-api.com by default)
GEOLOCATION_API_KEY=

# SMS Configuration (Optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Database
DATABASE_URL=sqlite:///creditcard_fraud.db

# Session Configuration
SESSION_TIMEOUT=86400  # 24 hours
```

### Generate Encryption Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this as CARD_ENCRYPTION_KEY
```

---

## Database Models

### New Models Added:

1. **EmailVerificationToken**
   - Stores email verification tokens
   - Expires after 7 days
   - Used for email confirmation on signup

2. **PasswordResetToken**
   - Stores password reset tokens
   - Expires after 24 hours
   - Single-use tokens

3. **LoginAttempt**
   - Records all login attempts
   - Includes success/failure status
   - Geographic information (IP, location)

4. **IPAddress**
   - User IP history
   - Geolocation data
   - VPN/proxy detection

5. **UserActivity**
   - Comprehensive activity audit log
   - Tracks: logins, logouts, profile changes, etc.
   - Indexed by user and timestamp

6. **Notification**
   - Email/SMS notification queue
   - Retry logic (up to 3 attempts)
   - Status tracking

7. **SecurityQuestion**
   - User security questions for recovery
   - Hashed answers
   - Multiple questions per user

8. **RateLimitRecord**
   - Rate limiting tracking
   - Per-IP, per-endpoint
   - Automatic cleanup

9. **Report**
   - Generated reports (CSV/PDF)
   - File path and format
   - Expiration tracking

10. **SuspiciousActivity**
    - Flagged suspicious activities
    - Risk/severity scoring
    - Admin review status

11. **AdminAction**
    - Administrative action audit trail
    - Action type and details
    - Timestamp and reason

---

## API Endpoints Summary

### Authentication & Verification
- `POST /register` - User registration with email verification
- `GET/POST /verify-email/<token>` - Email verification
- `GET/POST /forgot-password` - Password reset request
- `GET/POST /reset-password/<token>` - Password reset

### Session Management
- `GET /api/login-attempts` - Recent login history
- `GET /api/sessions` - Active sessions
- `POST /api/sessions/<id>/revoke` - Revoke session
- `GET /api/trusted-ips` - Trusted IP list
- `POST /api/trusted-ips` - Add trusted IP

### Activity & Notifications
- `GET /api/activity-log` - User activity audit log
- `GET /api/notifications` - User notifications
- `POST /api/notifications/<id>/read` - Mark notification as read

### Admin Management
- `GET /admin/users` - User management dashboard
- `POST /api/admin/users/<id>/block` - Block user
- `POST /api/admin/users/<id>/unblock` - Unblock user
- `POST /api/admin/users/<id>/reset-password` - Force password reset

### Suspicious Activity
- `GET /api/suspicious-activities` - List suspicious activities
- `POST /api/admin/suspicious-activities/<id>/review` - Review activity

### Security Questions
- `GET /api/security-questions` - Get security questions
- `POST /api/security-questions` - Set security questions

### Reports
- `POST /api/reports/generate` - Generate report
- `GET /api/reports/<id>` - Report status
- `GET /api/reports/<id>/download` - Download report

---

## Configuration

### Rate Limiting Configuration

Edit rate limits in `app.py`:

```python
RATE_LIMIT_CONFIG = {
    '/login': {'limit': 5, 'window': 300},        # 5 attempts per 5 minutes
    '/register': {'limit': 10, 'window': 3600},   # 10 per hour
    '/forgot-password': {'limit': 5, 'window': 3600},  # 5 per hour
    '/api': {'limit': 100, 'window': 60}           # 100 per minute
}
```

### Email Template Customization

Modify email templates in `EmailService` class (`utils.py`):
- Subject lines
- HTML content
- Footer information
- Support links

### Session Timeout

Set in `.env` or `config.py`:
```python
SESSION_TIMEOUT = 86400  # 24 hours in seconds
```

---

## Testing

### Manual Testing Checklist

```
[ ] Email Verification Flow
    [ ] User registers with valid email
    [ ] Verification email received
    [ ] Token link works
    [ ] Email marked as verified
    [ ] Unverified user warning displays

[ ] Password Reset Flow
    [ ] Request password reset
    [ ] Email received with reset link
    [ ] Token validation works
    [ ] New password requirements enforced
    [ ] Old password no longer works

[ ] IP & Geolocation Tracking
    [ ] IP logged on login
    [ ] Geographic location resolved
    [ ] VPN detection (if applicable)
    [ ] View login history shows locations

[ ] Rate Limiting
    [ ] 5th login attempt blocked
    [ ] Error message displayed
    [ ] Automatic unlock after 5 minutes
    [ ] Database records created

[ ] Suspicious Login Detection
    [ ] Impossible travel detected
    [ ] Email alert sent
    [ ] Activity logged as suspicious
    [ ] Admin can review activity

[ ] Admin User Management
    [ ] Block/unblock works
    [ ] User cannot login when blocked
    [ ] Password reset emails sent
    [ ] Actions logged in audit trail

[ ] Email Notifications
    [ ] Verification email sent
    [ ] Reset email sent
    [ ] Fraud alert sent
    [ ] Login alert sent
    [ ] Mark as read works

[ ] Activity Audit Logging
    [ ] Login/logout logged
    [ ] Profile changes logged
    [ ] API requests logged
    [ ] Admin actions logged
    [ ] Timestamps accurate

[ ] Card Data Security
    [ ] Card numbers encrypted
    [ ] Decryption returns original
    [ ] Partial masking works
    [ ] Cannot read raw DB values
```

### Automated Testing Example

```python
import pytest
from app import app, db
from models import User, EmailVerificationToken

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_email_verification(client):
    # Register user
    response = client.post('/register', data={
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'username': 'johndoe',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    
    # Get verification token
    token = db.session.query(EmailVerificationToken).first()
    assert token is not None
    
    # Verify email
    response = client.get(f'/verify-email/{token.token}')
    assert response.status_code == 302  # Redirect
    
    # Check user is verified
    user = db.session.query(User).filter_by(email='john@example.com').first()
    assert user.is_verified == True
```

---

## Troubleshooting

### Email Not Sending

1. Check SMTP credentials in `.env`
2. Verify SMTP server is accessible: `telnet smtp.gmail.com 587`
3. Check email application password (not Google account password)
4. Look for failed Notification records in database

### Geolocation API Issues

- Free API limited to 45 requests/minute
- For production, migrate to MaxMind GeoIP2
- Check API status at `ip-api.com`

### Rate Limiting Not Working

- Verify `RateLimitRecord` table exists in database
- Check logs for decorator errors
- Ensure `@rate_limit` decorator applied to routes

### Card Encryption Errors

- Verify `CARD_ENCRYPTION_KEY` is set and 44 characters long
- Regenerate key if corrupted: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"`

---

## Security Best Practices

1. **Always use HTTPS** in production
2. **Environment Variables** - Never hardcode secrets
3. **Token Expiration** - Always set short expiry times
4. **Rate Limiting** - Enable on all public endpoints
5. **Audit Logging** - Keep detailed logs of all actions
6. **Input Validation** - Sanitize all user inputs
7. **CSRF Protection** - Enable CSRF tokens in forms
8. **Password Requirements** - Enforce strong passwords
9. **Email Verification** - Verify email before access
10. **Regular Backups** - Backup encryption keys separately

---

## Support

For issues or questions:
1. Check logs: `tail -f app.log`
2. Review database: `sqlite3 instance/creditcard_fraud.db`
3. Test SMTP: `python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587)"`

---

**Last Updated:** 2024
**Version:** 1.0
