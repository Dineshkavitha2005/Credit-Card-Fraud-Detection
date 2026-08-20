import secrets
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db, audit_logger, EventType
from app.models.user import (
    User, UserCard, UserSession, LoginAttempt, IPAddress, UserActivity,
    EmailVerificationToken, PasswordResetToken, SecurityQuestion, Notification
)
from utils import GeolocationService, SecurityHelper, EmailService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with email verification"""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zipcode = request.form.get('zipcode', '').strip()
        country = request.form.get('country', '').strip()
        
        if not all([first_name, last_name, email, username, password]):
            audit_logger.log_event(EventType.REGISTRATION, status='failure', details={'username': username, 'email': email, 'reason': 'Missing fields'})
            return render_template('register.html', error='All required fields must be filled')
        
        if password != confirm_password:
            audit_logger.log_event(EventType.REGISTRATION, status='failure', details={'username': username, 'email': email, 'reason': 'Passwords do not match'})
            return render_template('register.html', error='Passwords do not match')
        
        strength = SecurityHelper.check_password_strength(password)
        if not strength['is_valid']:
            audit_logger.log_event(EventType.REGISTRATION, status='failure', details={'username': username, 'email': email, 'reason': 'Weak password'})
            return render_template('register.html', error=', '.join(strength['feedback']))
        
        if User.query.filter_by(username=username).first():
            audit_logger.log_event(EventType.REGISTRATION, status='failure', details={'username': username, 'email': email, 'reason': 'Username exists'})
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            audit_logger.log_event(EventType.REGISTRATION, status='failure', details={'username': username, 'email': email, 'reason': 'Email exists'})
            return render_template('register.html', error='Email already registered')
        
        try:
            user = User(
                username=username,
                email=email,
                full_name=f'{first_name} {last_name}',
                phone=phone,
                address=address,
                city=city,
                state=state,
                zipcode=zipcode,
                country=country,
                role='user',
                is_verified=False,
                notification_preferences={'email': True, 'sms': False}
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()
            
            verification_token = EmailVerificationToken.generate_token()
            verification = EmailVerificationToken(
                user_id=user.id,
                token=verification_token,
                email=email
            )
            db.session.add(verification)
            db.session.commit()
            
            audit_logger.log_event(EventType.REGISTRATION, user_id=user.id, status='success', details={'username': username, 'email': email})
            
            activity = UserActivity(
                user_id=user.id,
                activity_type='user_registered',
                action_description='New user registration',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                status='success'
            )
            db.session.add(activity)
            db.session.commit()
            
            EmailService.send_verification_email(email, verification_token, f'{first_name} {last_name}')
            
            return render_template('message.html',
                                 title='Registration Successful',
                                 message='Check your email to verify your account. Verification link expires in 7 days.',
                                 type='success',
                                 action_link='/login')
        
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error=f'Registration failed: {str(e)}')
    
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Secure login with IP logging and suspicious activity detection"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr
        
        geo_data = GeolocationService.get_geo_data(ip_address)
        user = User.query.filter_by(username=username).first()
        
        login_attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            user_agent=request.user_agent.string,
            success=False,
            country=geo_data.get('country'),
            city=geo_data.get('city'),
            latitude=geo_data.get('latitude'),
            longitude=geo_data.get('longitude')
        )
        
        if SecurityHelper.is_rate_limited(ip_address, '/login', limit=5, window=300):
            login_attempt.failure_reason = 'rate_limited'
            db.session.add(login_attempt)
            db.session.commit()
            audit_logger.log_event(EventType.FAILED_LOGIN, status='failure', details={'username': username, 'reason': 'Rate limited'})
            return render_template('login.html', error='Too many login attempts. Please try again in 5 minutes.')
        
        if not user or not user.check_password(password):
            login_attempt.failure_reason = 'invalid_credentials'
            db.session.add(login_attempt)
            db.session.commit()
            audit_logger.log_event(EventType.FAILED_LOGIN, user_id=user.id if user else None, status='failure', details={'username': username, 'reason': 'Invalid credentials'})
            return render_template('login.html', error='Invalid username or password')
        
        if not user.is_active:
            login_attempt.failure_reason = 'account_disabled'
            db.session.add(login_attempt)
            db.session.commit()
            audit_logger.log_event(EventType.FAILED_LOGIN, user_id=user.id, status='failure', details={'username': username, 'reason': 'Account disabled'})
            return render_template('login.html', error='Account has been deactivated. Please contact support.')
        
        login_attempt.success = True
        user.update_last_login()
        db.session.add(login_attempt)
        
        login_user(user)
        session.permanent = True
        
        session_token = secrets.token_hex(32)
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=request.user_agent.string,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(user_session)
        
        known_ip = IPAddress.query.filter_by(ip_address=ip_address).first()
        if not known_ip:
            known_ip = IPAddress(
                ip_address=ip_address,
                user_id=user.id,
                country=geo_data.get('country'),
                city=geo_data.get('city'),
                latitude=geo_data.get('latitude'),
                longitude=geo_data.get('longitude')
            )
            db.session.add(known_ip)
        else:
            known_ip.last_seen = datetime.utcnow()
        
        db.session.commit()
        
        audit_logger.log_event(EventType.LOGIN, user_id=user.id, status='success', details={'username': username})
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """User logout"""
    if current_user.is_authenticated:
        audit_logger.log_event(EventType.LOGOUT, user_id=current_user.id, status='success', details={'username': current_user.username})
        logout_user()
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Render user profile page"""
    return render_template('profile.html', user=current_user)


@auth_bp.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    """API: Update user profile"""
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    zipcode = data.get('zipcode', '').strip()
    country = data.get('country', '').strip()
    
    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    if address:
        current_user.address = address
    if city:
        current_user.city = city
    if state:
        current_user.state = state
    if zipcode:
        current_user.zipcode = zipcode
    if country:
        current_user.country = country
        
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})


@auth_bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """API: Change user password"""
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
        
    strength = SecurityHelper.check_password_strength(new_password)
    if not strength['is_valid']:
        return jsonify({'error': ', '.join(strength['feedback'])}), 400
        
    current_user.set_password(new_password)
    db.session.commit()
    
    audit_logger.log_event(EventType.PASSWORD_CHANGE, user_id=current_user.id, status='success', details={'username': current_user.username})
    return jsonify({'message': 'Password changed successfully'})


@auth_bp.route('/api/notifications', methods=['POST'])
@login_required
def update_notifications():
    """API: Update notification preferences"""
    data = request.get_json() or {}
    current_user.notification_preferences = data
    db.session.commit()
    return jsonify({'message': 'Preferences saved'})


@auth_bp.route('/api/2fa/toggle', methods=['POST'])
@login_required
def toggle_2fa():
    """API: Toggle 2FA"""
    data = request.get_json() or {}
    enabled = bool(data.get('enabled', False))
    current_user.two_factor_enabled = enabled
    db.session.commit()
    return jsonify({'message': f'2FA {"enabled" if enabled else "disabled"}'})


@auth_bp.route('/api/logout-all-devices', methods=['POST'])
@login_required
def logout_all_devices():
    """API: Revoke all active sessions"""
    UserSession.query.filter_by(user_id=current_user.id).update({'is_active': False})
    db.session.commit()
    return jsonify({'message': 'All devices logged out'})


@auth_bp.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    """API: Soft-delete user account"""
    current_user.is_active = False
    db.session.commit()
    logout_user()
    return jsonify({'message': 'Account deactivated'})


@auth_bp.route('/verify-email/<token>', methods=['GET', 'POST'])
def verify_email(token):
    """Verify user email address using token"""
    verify_record = EmailVerificationToken.query.filter_by(token=token).first()
    if not verify_record or not verify_record.is_valid():
        return render_template('message.html', title='Verification Failed', message='Invalid or expired verification link.', type='danger')

    user = User.query.get(verify_record.user_id)
    if user:
        user.is_verified = True
        verify_record.is_verified = True
        verify_record.verified_at = datetime.utcnow()
        db.session.commit()
        return render_template('message.html', title='Email Verified', message='Your email has been verified. You may now log in.', type='success', action_link='/login')

    return render_template('message.html', title='Verification Failed', message='User not found.', type='danger')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password request link"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        if user:
            reset_token = PasswordResetToken.generate_token()
            token_record = PasswordResetToken(user_id=user.id, token=reset_token)
            db.session.add(token_record)
            db.session.commit()
            EmailService.send_password_reset_email(email, reset_token, user.username)
        return render_template('message.html', title='Password Reset Sent', message='If an account matches that email, a password reset link has been sent.', type='info')
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using valid reset token"""
    token_record = PasswordResetToken.query.filter_by(token=token).first()
    if not token_record or not token_record.is_valid():
        return render_template('message.html', title='Reset Failed', message='Invalid or expired reset link.', type='danger')

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match')

        user = User.query.get(token_record.user_id)
        if user:
            user.set_password(password)
            token_record.is_used = True
            token_record.used_at = datetime.utcnow()
            db.session.commit()
            return render_template('message.html', title='Password Reset Complete', message='Password updated successfully. You can now log in.', type='success', action_link='/login')

    return render_template('reset_password.html')
