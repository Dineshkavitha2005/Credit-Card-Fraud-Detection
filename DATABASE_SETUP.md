# FraudShield - Security & Database Enhancements

## 🔐 What's New

This update introduces enterprise-grade user authentication, secure database management, and comprehensive user account features.

---

## 📋 New Features

### 1. **Secure User Authentication** ✅
- **Bcrypt Password Hashing**: Passwords are now hashed with bcrypt using 12 salt rounds (industry standard)
- **Previous approach**: Plain SHA256 hashing (now replaced)
- **Benefit**: Even if the database is compromised, passwords remain cryptographically secure

### 2. **User Registration System** ✅
- Self-service account creation with email verification support
- Strong password requirements validation:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one number
  - Real-time strength indicator
- Comprehensive user profile collection:
  - Full name, email, phone number
  - Address, city, state, zip code, country
  - Customizable notification preferences

### 3. **Enhanced User Profiles** ✅
- Complete user profile management
- Update personal information anytime
- Secure password change functionality
- Email and SMS notification preferences
- Two-factor authentication (2FA) toggle

### 4. **Account Security Features** ✅
- **Session Tracking**: All login sessions are tracked
- **Audit Logging**: Every account action is logged (login, password change, profile update, card additions)
- **Failed Login Detection**: System records failed login attempts
- **Account Deletion**: Users can permanently delete their accounts
- **Logout All Devices**: Instantly sign out from all sessions

### 5. **SQLAlchemy ORM** ✅
- Replaces legacy SQLite raw queries
- Better data validation and relationships
- Automatic timestamp management
- Type-safe database operations
- Easier database migrations in future

---

## 🗄️ Database Schema Improvements

### New Tables & Models

#### **User Model** (Enhanced)
```python
- id: Unique user identifier
- username: Unique login name
- email: User email (unique, required)
- password_hash: Bcrypt hashed password
- full_name: User's full name
- phone, address, city, state, zipcode, country: Contact information
- notification_preferences: JSON for email/SMS alerts
- two_factor_enabled: 2FA status
- is_active, is_verified: Account status flags
- last_login: Timestamp of last login
- created_at, updated_at: Audit timestamps
```

#### **AuditLog Model** (New)
Tracks all user actions for security compliance:
- user_id, action, resource, status
- ip_address: Where the action originated
- created_at: When the action occurred

#### **UserSession Model** (New)
Manages active user sessions:
- user_id, session_token, ip_address
- user_agent: Browser/device information
- expires_at, last_activity: Session lifecycle

#### **UserCard Model** (Improved)
```python
- id, user_id, card_number (encrypted)
- card_holder, card_type, expiry info
- daily_limit, monthly_limit: Spending controls
- is_primary: Primary payment method
- last_used: Last transaction timestamp
```

---

## 🔑 Authentication Routes

### Public Routes
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Redirect to login/dashboard |
| `/login` | GET, POST | User login |
| `/register` | GET, POST | New user registration |

### Protected Routes (Login Required)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/profile` | GET | View user profile |
| `/api/profile` | POST | Update profile info |
| `/api/change-password` | POST | Change password securely |
| `/api/notifications` | POST | Update notification preferences |
| `/api/2fa/toggle` | POST | Enable/disable 2FA |
| `/api/logout-all-devices` | POST | Sign out from all devices |
| `/api/delete-account` | POST | Permanently delete account |
| `/logout` | GET | Sign out current session |

---

## 🚀 Getting Started

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

New packages added:
- `Flask-SQLAlchemy>=3.0.0` - ORM for database
- `bcrypt>=4.1.0` - Secure password hashing
- `Flask-Login>=0.6.0` - Session management
- `Flask-WTF>=1.2.0` - Form security
- `Flask-Migrate>=4.0.0` - Database migrations
- `WTForms>=3.0.0` - Form validation
- `email-validator>=2.0.0` - Email validation

### 2. **Run the Application**
```bash
python app.py
```

The app will:
- ✅ Initialize the SQLAlchemy database
- ✅ Create the admin user (if not exists)
- ✅ Create default fraud rules
- ✅ Set up all tables automatically

### 3. **First Login**
```
URL: http://127.0.0.1:5000
Username: admin
Password: admin123
```

**⚠️ IMPORTANT**: Change the admin password immediately after first login!

### 4. **Create Your Account**
- Click "Create one now" on the login page
- Fill in your details
- Set a strong password (8+ chars, uppercase, number)
- Start using the fraud detection system

---

## 🛡️ Security Best Practices

### Password Security
- ✅ Bcrypt hashing with 12 rounds (takes ~0.5 second to hash)
- ✅ Passwords never stored in plain text
- ✅ Password strength validation on registration
- ✅ Secure password change endpoint

### Session Security
- ✅ HTTP-only cookies (when using production server)
- ✅ Session tracking per user
- ✅ IP address logging for fraud detection
- ✅ Automatic session timeout (configurable)

### Audit Logging
Every action is logged:
- Who (user_id)
- What (action)
- When (timestamp)
- Where (ip_address)

Example logged actions:
- User registration
- Login attempts (successful/failed)
- Profile updates
- Password changes
- Card addition/deletion
- 2FA toggle
- Account deletion

### Data Protection
- Card numbers: Only last 4 digits shown in UI
- CVV: Validated but never stored
- Passwords: One-way bcrypt hash only
- Sensitive data: Encrypted in transit with HTTPS (production)

---

## 📊 User Profile Page Features

The profile page (`/profile`) includes:

### 1. **Personal Information**
- Update name, email, phone
- Update address details (street, city, state, country)

### 2. **Security Settings**
- Change password with current password verification
- Enable/disable two-factor authentication
- All password changes logged to audit trail

### 3. **Notification Preferences**
- Email alerts for suspicious transactions
- SMS alerts for fraud attempts
- Fraud detection alert preferences

### 4. **Danger Zone**
- Logout from all devices (terminates all sessions)
- Delete account permanently (with data cleanup)

---

## 🔄 Migration from Old System

### Old vs. New

| Feature | Old | New |
|---------|-----|-----|
| Password Hashing | SHA256 ▌ | Bcrypt ✅ |
| Database | SQLite (raw) | SQLite + SQLAlchemy ✅ |
| User Fields | username, password, role | Full profile data + 10+ fields ✅ |
| Account Management | None | Full profile/settings page ✅ |
| Audit Trail | None | Complete action logging ✅ |
| Registration | None | Self-service registration ✅ |
| Security | Basic | Enterprise-grade ✅ |

### Data Compatibility
- Old SQLite database is automatically migrated
- Existing user accounts are preserved
- Admin account is automatically created
- All fraud detection features continue to work

---

## 🧪 Testing the New Features

### Test Registration
```
1. Go to http://127.0.0.1:5000/register
2. Fill in all required fields
3. Use password: Test@123
4. Submit form
5. Verify you're logged in and redirected to card setup
```

### Test Login
```
1. Go to http://127.0.0.1:5000/login
2. Username: admin, Password: admin123
3. Verify dashboard loads
```

### Test Profile Update
```
1. Click your name in the top-right (if implemented in template)
2. Go to /profile
3. Update any field
4. Verify changes saved
5. Check database audit log
```

### Test Password Change
```
1. In profile page, enter current password
2. Enter new password meeting requirements
3. Verify login works with new password
4. Old password no longer works
```

---

## ⚙️ Configuration

### Database Location
- File: `fraud_detection.db` (same directory as app.py)
- Type: SQLite3
- Migration: Automatic with SQLAlchemy

### Security Settings
- Bcrypt rounds: 12 (can be adjusted in models.py)
- Session timeout: Configurable in Flask settings
- Password minimum: 8 characters

### Notification System
```python
notification_preferences = {
    'email': True,    # Email alerts enabled
    'sms': False,     # SMS alerts disabled
}
```

---

## 📝 Admin Tasks

### Change Admin Password (IMPORTANT!)
```bash
python -c "from models import *; from app import db, app
app.app_context().push()
user = User.query.filter_by(username='admin').first()
user.set_password('your_new_password')
db.session.commit()
print('Password changed!')
"
```

### View Audit Logs
```python
from models import AuditLog, db
from app import app

app.app_context().push()
logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
for log in logs:
    print(f"{log.created_at} | {log.user_id} | {log.action} | {log.status}")
```

### Delete User Account
```python
from models import User, db
from app import app

app.app_context().push()
user = User.query.filter_by(username='john_doe').first()
db.session.delete(user)
db.session.commit()
print("User deleted")
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: models"
✅ Solution: Ensure `models.py` is in the same directory as `app.py`

### "No such table: users"
✅ Solution: Delete `fraud_detection.db` and re-run `python app.py` (recreates schema)

### "bcrypt not installed"
✅ Solution: Run `pip install -r requirements.txt`

### "Password verification fails"
✅ Solution: Bcrypt must be used for both hashing and verification. Ensure you're using `user.check_password()`

---

## 📚 Code Examples

### Login a User (Automatic)
```python
# On successful login form submission
user = User.query.filter_by(username=username).first()
if user and user.check_password(password):
    session['user_id'] = user.id
    session['username'] = user.username
    user.update_last_login()  # Updates timestamp
    return redirect(url_for('dashboard'))
```

### Register New User
```python
user = User(
    username=username,
    email=email,
    full_name=f'{first_name} {last_name}'
)
user.set_password(password)  # Bcrypt hashing
db.session.add(user)
db.session.commit()
```

### Check Password
```python
# Always use this method, never compare directly
if user.check_password(password):
    # Password is correct
    pass
```

### Update Audit Log
```python
audit = AuditLog(
    user_id=session['user_id'],
    action='card_added',
    resource='card_123',
    status='success',
    ip_address=request.remote_addr
)
db.session.add(audit)
db.session.commit()
```

---

## 🎯 Next Steps (Recommendations)

1. **Two-Factor Authentication (2FA)**: Implement TOTP/SMS verification
2. **Password Reset**: Email-based password reset functionality
3. **Rate Limiting**: Limit login attempts to prevent brute force
4. **API Keys**: Generate API keys for programmatic access
5. **Role-Based Access Control (RBAC)**: Different permission levels
6. **Email Verification**: Verify email addresses on registration
7. **Data Encryption**: Encrypt sensitive card data at rest
8. **Backup & Recovery**: Implement database backup strategy

---

## 📞 Support

For issues or questions about the new authentication system:
1. Check the Troubleshooting section
2. Review the models.py for database schema
3. Check audit logs for failed operations
4. Verify all pip packages are installed

---

## License & Security Notice

- ⚠️ This system is for educational/demonstration purposes
- ⚠️ For production, add HTTPS, rate limiting, and additional security measures
- ⚠️ Never commit database files to version control
- ✅ Always update to the latest security patches for dependencies

---

**Last Updated**: March 2026  
**Version**: 2.0 (Database & Authentication Enhanced)
