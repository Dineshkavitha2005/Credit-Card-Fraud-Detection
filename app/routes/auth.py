import secrets
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db, audit_logger, EventType
from app.models.user import (
    User, UserIdentity, UserCard, UserSession, LoginAttempt, IPAddress, UserActivity,
    EmailVerificationToken, PasswordResetToken, SecurityQuestion, Notification
)
from app.services.oauth_service import oauth_service, OAuthError
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
@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """API & Web Form: Update user profile"""
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    full_name = data.get('full_name', '').strip()
    if not full_name and (data.get('first_name') or data.get('last_name')):
        full_name = f"{data.get('first_name', '').strip()} {data.get('last_name', '').strip()}".strip()

    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    zipcode = data.get('zipcode', '').strip()
    country = data.get('country', '').strip()

    if email and email != current_user.email:
        if User.query.filter(User.email == email, User.id != current_user.id).first():
            if not request.is_json and request.form:
                flash('A user with this email already exists', 'danger')
                return redirect(url_for('auth.profile'))
            return jsonify({'error': 'A user with this email already exists'}), 400
        current_user.email = email

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

    if not request.is_json and request.form:
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))

    return jsonify({'message': 'Profile updated successfully'})


@auth_bp.route('/api/change-password', methods=['POST'])
@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """API & Web Form: Change user password"""
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if confirm_password and new_password != confirm_password:
        msg = 'Passwords do not match'
        if not request.is_json and request.form:
            flash(msg, 'danger')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    if not current_user.check_password(current_password):
        msg = 'Current password is incorrect'
        if not request.is_json and request.form:
            flash(msg, 'danger')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    strength = SecurityHelper.check_password_strength(new_password)
    if not strength['is_valid']:
        msg = ', '.join(strength['feedback'])
        if not request.is_json and request.form:
            flash(msg, 'danger')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    current_user.set_password(new_password)
    db.session.commit()

    audit_logger.log_event(EventType.PASSWORD_CHANGE, user_id=current_user.id, status='success', details={'username': current_user.username})

    if not request.is_json and request.form:
        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))

    return jsonify({'message': 'Password changed successfully'})


@auth_bp.route('/api/notifications', methods=['POST'])
@login_required
def update_notifications():
    """API & Web Form: Update notification preferences"""
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = {
            'email': 'email_notif' in request.form,
            'sms': 'sms_notif' in request.form,
            'fraud_alerts': 'fraud_alerts' in request.form
        }
    current_user.notification_preferences = data
    db.session.commit()

    if not request.is_json and request.form:
        flash('Preferences saved', 'success')
        return redirect(url_for('auth.profile'))

    return jsonify({'message': 'Preferences saved'})


@auth_bp.route('/api/2fa/toggle', methods=['POST'])
@login_required
def toggle_2fa():
    """API & Web Form: Toggle 2FA"""
    if request.is_json:
        data = request.get_json() or {}
        enabled = bool(data.get('enabled', not current_user.two_factor_enabled))
    elif request.form and 'enabled' in request.form:
        enabled = request.form.get('enabled') in ('true', '1', 'on')
    else:
        enabled = not current_user.two_factor_enabled

    current_user.two_factor_enabled = enabled
    db.session.commit()

    msg = f'2FA {"enabled" if enabled else "disabled"}'
    if not request.is_json and request.form:
        flash(msg, 'success')
        return redirect(url_for('auth.profile'))

    return jsonify({'message': msg})


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
            return render_template('reset_password.html', error='Passwords do not match', token=token)

        strength = SecurityHelper.check_password_strength(password)
        if not strength['is_valid']:
            return render_template('reset_password.html', error=', '.join(strength['feedback']), token=token)

        user = User.query.get(token_record.user_id)
        if user:
            user.set_password(password)
            token_record.is_used = True
            token_record.used_at = datetime.utcnow()
            db.session.commit()
            audit_logger.log_event(EventType.PASSWORD_CHANGE, user_id=user.id, status='success', details={'username': user.username, 'action': 'password_reset_completed'})
            return render_template('message.html', title='Password Reset Complete', message='Password updated successfully. You can now log in.', type='success', action_link='/login')

    return render_template('reset_password.html', token=token)


# ═════════════════════════════════════════════════════════════════════════════
# Google OAuth 2.0 / OpenID Connect Authentication Flow
# ═════════════════════════════════════════════════════════════════════════════

@auth_bp.route('/auth/google', methods=['GET'])
@auth_bp.route('/login/google', methods=['GET'])
def google_login():
    """
    Initiate Google OAuth 2.0 / OpenID Connect authorization code flow with PKCE
    and cryptographic state CSRF protection.
    """
    ip_address = request.remote_addr or '127.0.0.1'

    # Rate limiting protection
    if SecurityHelper.is_rate_limited(ip_address, '/auth/google', limit=15, window=60):
        audit_logger.log_event(
            EventType.FAILED_LOGIN,
            status='failure',
            details={'reason': 'Rate limited on /auth/google'}
        )
        flash("Too many authentication requests. Please wait a moment and try again.", "warning")
        return redirect(url_for('auth.login'))

    if not oauth_service.is_configured():
        flash("Google sign-in is not configured on this server.", "warning")
        return redirect(url_for('auth.login'))

    # Generate state & PKCE parameters
    state = oauth_service.generate_state()
    code_verifier, code_challenge, _ = oauth_service.generate_pkce()

    # Store state and PKCE in session
    session['oauth_state'] = state
    session['oauth_code_verifier'] = code_verifier
    session['oauth_state_time'] = datetime.utcnow().timestamp()
    session['oauth_next'] = request.args.get('next')
    session['oauth_mode'] = 'link' if (current_user.is_authenticated and request.args.get('mode') == 'link') else 'login'

    auth_url = oauth_service.build_authorization_url(state, code_challenge=code_challenge)
    return redirect(auth_url)


@auth_bp.route('/auth/google/callback', methods=['GET'])
def google_callback():
    """
    Handle Google OAuth 2.0 callback:
    - Validate cryptographic state to prevent CSRF / replay attacks
    - Exchange authorization code for tokens using PKCE verifier
    - Fetch verified identity from OpenID Connect UserInfo
    - Provision new user or link existing account safely
    - Establish standard Flask-Login authenticated session
    """
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    ip_address = ip_address or request.remote_addr or '127.0.0.1'

    # Rate limiting
    if SecurityHelper.is_rate_limited(ip_address, '/auth/google/callback', limit=20, window=60):
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            status='failure',
            details={'reason': 'Rate limited on OAuth callback'}
        )
        flash("Too many callback requests. Please try again later.", "warning")
        return redirect(url_for('auth.login'))

    # Handle error responses from Google authorization endpoint
    error = request.args.get('error')
    if error:
        if error in ('access_denied', 'user_cancelled_authorize', 'consent_denied'):
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_CANCELLED,
                user_id=None,
                status='failure',
                details={'error': error}
            )
            flash("Google sign-in cancelled", "warning")
            return redirect(url_for('auth.login'))
        else:
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_FAILURE,
                user_id=None,
                status='failure',
                details={'error': error}
            )
            flash("Unable to sign in with Google. Please try again.", "danger")
            return redirect(url_for('auth.login'))

    # Validate OAuth state (CSRF / Replay Protection)
    expected_state = session.pop('oauth_state', None)
    state_time = session.pop('oauth_state_time', None)
    code_verifier = session.pop('oauth_code_verifier', None)
    oauth_next = session.pop('oauth_next', None)
    oauth_mode = session.pop('oauth_mode', 'login')
    received_state = request.args.get('state')

    if not expected_state or not received_state or expected_state != received_state:
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            user_id=None,
            status='failure',
            details={'reason': 'OAuth state CSRF validation failed'}
        )
        flash("Unable to sign in with Google. Please try again.", "danger")
        return redirect(url_for('auth.login'))

    # Validate state freshness (10-minute expiry)
    if state_time and (datetime.utcnow().timestamp() - state_time > 600):
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            user_id=None,
            status='failure',
            details={'reason': 'OAuth state expired (> 10 minutes)'}
        )
        flash("Google sign-in session expired. Please try again.", "warning")
        return redirect(url_for('auth.login'))

    # Validate authorization code
    code = request.args.get('code')
    if not code:
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            user_id=None,
            status='failure',
            details={'reason': 'Missing authorization code'}
        )
        flash("Unable to sign in with Google. Please try again.", "danger")
        return redirect(url_for('auth.login'))

    # Exchange code for tokens & fetch verified OpenID Connect profile
    try:
        tokens = oauth_service.exchange_code_for_tokens(code, code_verifier=code_verifier)
        user_info = oauth_service.fetch_user_info(tokens['access_token'])
    except OAuthError as e:
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            user_id=None,
            status='failure',
            details={'reason': str(e.message), 'error_code': getattr(e, 'code', 'OAUTH_ERROR')}
        )
        flash("Unable to sign in with Google. Please try again.", "danger")
        return redirect(url_for('auth.login'))
    except Exception as e:
        audit_logger.log_event(
            EventType.GOOGLE_LOGIN_FAILURE,
            user_id=None,
            status='failure',
            details={'reason': f'Unexpected callback error: {str(e)}'}
        )
        flash("Unable to sign in with Google. Please try again.", "danger")
        return redirect(url_for('auth.login'))

    # Resolve or create Sentinel user account
    linking_user = current_user if (oauth_mode == 'link' and current_user.is_authenticated) else None
    user, action, err_msg = oauth_service.resolve_or_create_user(
        user_info, mode=oauth_mode, linking_user=linking_user
    )

    if not user:
        if action == 'disabled':
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_FAILURE,
                user_id=None,
                status='failure',
                details={'reason': 'Account disabled', 'email': user_info.get('email')}
            )
            flash("This account is currently disabled.", "danger")
            return redirect(url_for('auth.login'))
        elif action == 'conflict':
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_FAILURE,
                user_id=None,
                status='failure',
                details={'reason': 'Account conflict', 'email': user_info.get('email')}
            )
            flash("This Google account is already associated with another Sentinel account.", "danger")
            return redirect(url_for('auth.profile' if oauth_mode == 'link' else 'auth.login'))
        elif action == 'unauthorized':
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_FAILURE,
                user_id=None,
                status='failure',
                details={'reason': 'Domain unauthorized', 'email': user_info.get('email')}
            )
            flash("Access restricted. Your Google Workspace domain is not authorized.", "danger")
            return redirect(url_for('auth.login'))
        else:
            audit_logger.log_event(
                EventType.GOOGLE_LOGIN_FAILURE,
                user_id=None,
                status='failure',
                details={'reason': err_msg or 'User resolution failed'}
            )
            flash(err_msg or "Unable to sign in with Google. Please try again.", "danger")
            return redirect(url_for('auth.login'))

    if oauth_mode == 'link' and action == 'linked':
        audit_logger.log_event(
            EventType.GOOGLE_ACCOUNT_LINKED,
            user_id=user.id,
            status='success',
            details={'email': user_info.get('email'), 'provider': 'google'}
        )
        flash("Google account connected successfully!", "success")
        return redirect(url_for('auth.profile'))

    # Establish authenticated Sentinel session
    login_user(user)
    session.permanent = True
    user.update_last_login()

    geo_data = GeolocationService.get_geo_data(ip_address)
    session_token = secrets.token_hex(32)
    user_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=request.user_agent.string[:255] if request.user_agent else 'system',
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

    login_attempt = LoginAttempt(
        username=user.username,
        ip_address=ip_address,
        user_agent=request.user_agent.string[:255] if request.user_agent else 'system',
        success=True,
        country=geo_data.get('country'),
        city=geo_data.get('city'),
        latitude=geo_data.get('latitude'),
        longitude=geo_data.get('longitude')
    )
    db.session.add(login_attempt)
    db.session.commit()

    # Record appropriate audit events
    if action == 'created':
        audit_logger.log_event(
            EventType.GOOGLE_ACCOUNT_CREATED,
            user_id=user.id,
            status='success',
            details={'username': user.username, 'email': user.email}
        )
    elif action == 'linked':
        audit_logger.log_event(
            EventType.GOOGLE_ACCOUNT_LINKED,
            user_id=user.id,
            status='success',
            details={'username': user.username, 'email': user.email}
        )

    audit_logger.log_event(
        EventType.GOOGLE_LOGIN_SUCCESS,
        user_id=user.id,
        status='success',
        details={'username': user.username, 'email': user.email, 'action': action}
    )

    next_page = oauth_next
    if next_page and (next_page.startswith('/') and not next_page.startswith('//')):
        return redirect(next_page)
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/auth/google/disconnect', methods=['POST'])
@login_required
def google_disconnect():
    """
    Securely disconnect Google identity from current user account.
    Enforces security invariant: User MUST retain at least one login method (password).
    """
    if not current_user.has_password:
        msg = "Cannot disconnect Google authentication. You must set a password first to avoid losing access to your account."
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': msg}), 400
        flash(msg, "danger")
        return redirect(url_for('auth.profile'))

    # Revoke local Google identity association
    UserIdentity.query.filter_by(user_id=current_user.id, provider='google').delete()
    current_user.google_id = None
    current_user.auth_provider = 'local'
    db.session.commit()

    audit_logger.log_event(
        EventType.GOOGLE_ACCOUNT_UNLINKED,
        user_id=current_user.id,
        status='success',
        details={'username': current_user.username}
    )

    if request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({'message': 'Google account disconnected successfully.'})

    flash("Google account disconnected successfully.", "success")
    return redirect(url_for('auth.profile'))


@auth_bp.route('/api/set-password', methods=['POST'])
@auth_bp.route('/profile/set-password', methods=['POST'])
@login_required
def set_initial_password():
    """
    API & Web Form: Set initial password for OAuth users who do not have a password configured yet.
    """
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if current_user.has_password:
        msg = 'Password already configured. Use Change Password instead.'
        if not request.is_json and request.form:
            flash(msg, 'warning')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    if not new_password or new_password != confirm_password:
        msg = 'Passwords do not match'
        if not request.is_json and request.form:
            flash(msg, 'danger')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    strength = SecurityHelper.check_password_strength(new_password)
    if not strength['is_valid']:
        msg = ', '.join(strength['feedback'])
        if not request.is_json and request.form:
            flash(msg, 'danger')
            return redirect(url_for('auth.profile'))
        return jsonify({'error': msg}), 400

    current_user.set_password(new_password)
    current_user.auth_provider = 'multiple' if current_user.has_google_linked else 'local'
    db.session.commit()

    audit_logger.log_event(
        EventType.PASSWORD_CHANGE,
        user_id=current_user.id,
        status='success',
        details={'username': current_user.username, 'action': 'initial_password_set'}
    )

    if not request.is_json and request.form:
        flash('Password configured successfully. You can now use either password or Google authentication.', 'success')
        return redirect(url_for('auth.profile'))

    return jsonify({'message': 'Password configured successfully. You can now use either password or Google authentication.'})

