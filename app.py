"""
Credit Card Fraud Detection System - Main Application
Real-time fraud detection with admin analytics dashboard
Enhanced with secure user authentication and database
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from datetime import datetime, timedelta
from sqlalchemy import or_
import sqlite3
import json
import os
import random
import hashlib
import bcrypt
import secrets
import requests
import math
import numpy as np
import joblib
import pandas as pd
from functools import wraps
from preprocessor import TransactionPreprocessor
from flask.json.provider import DefaultJSONProvider
from models import (
    db, User, UserCard, Transaction, Alert, FraudRule, BlockedCard, AuditLog, UserSession,
    LoginAttempt, IPAddress, UserActivity, EmailVerificationToken, PasswordResetToken,
    Notification, SecurityQuestion, RateLimitRecord, Report, SuspiciousActivity, AdminAction,
    CardEncryption, mask_card_number
)

def sanitize_numpy_types(obj):
    """Recursively convert NumPy data types into native Python types for JSON serialization."""
    if obj is None:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [sanitize_numpy_types(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): sanitize_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_numpy_types(x) for x in obj]
    return obj

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

app = Flask(__name__)
app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)
secret_key_val = os.getenv('SECRET_KEY', '').strip()
if not secret_key_val or secret_key_val in {'your_secret_key_here', 'change_this_secret_key_in_production', 'fraud-detection-secret-key-2026', 'secret', 'default-unsafe-key'}:
    if os.getenv('FLASK_ENV') == 'production' and not os.getenv('TESTING'):
        raise ValueError("Insecure or default SECRET_KEY configured in environment.")
    secret_key_val = secrets.token_hex(32)
app.secret_key = secret_key_val
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fraud_detection.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secure report directory path inside instance folder
reports_dir = os.path.abspath(os.path.join(app.instance_path, 'reports'))
os.makedirs(reports_dir, exist_ok=True)
app.config['REPORTS_DIR'] = reports_dir

CORS(app)

# Initialize SQLAlchemy and LoginManager
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

@login_manager.unauthorized_handler
def unauthorized():
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.url))

DATABASE = os.path.join(app.instance_path, 'fraud_detection.db') if os.path.exists(os.path.join(app.instance_path, 'fraud_detection.db')) else 'fraud_detection.db'

# ─── Database Helpers ────────────────────────────────────────────────

def get_db():
    """Get SQLite connection for operations"""
    db_path = app.config.get('DATABASE', DATABASE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_database_security():
    """Migrate existing plain text card numbers in SQLite DB to masked/encrypted representations"""
    try:
        conn = get_db()
        # 1. Migrate transactions table
        txns = conn.execute('SELECT id, card_number FROM transactions').fetchall()
        for t in txns:
            raw_card = t['card_number']
            if raw_card and not raw_card.startswith('****') and not raw_card.startswith('••••'):
                masked = mask_card_number(raw_card)
                conn.execute('UPDATE transactions SET card_number = ? WHERE id = ?', (masked, t['id']))
        # 2. Migrate blocked_cards table
        b_cards = conn.execute('SELECT id, card_number FROM blocked_cards').fetchall()
        for b in b_cards:
            raw_card = b['card_number']
            if raw_card and not raw_card.startswith('gAAAAA'):
                enc = CardEncryption.encrypt_card_number(raw_card)
                conn.execute('UPDATE blocked_cards SET card_number = ? WHERE id = ?', (enc, b['id']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database security migration note: {e}")

    try:
        user_cards = UserCard.query.all()
        for card in user_cards:
            if card.card_number and not card.card_number.startswith('gAAAAA'):
                card.card_number = CardEncryption.encrypt_card_number(card.card_number)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"User cards migration note: {e}")


def init_db():
    """Initialize database with all tables and perform security migrations"""
    with app.app_context():
        # Create SQLAlchemy tables
        db.create_all()
        
        # Security migration of existing plain text numbers
        migrate_database_security()
        
        # Create default admin user if doesn't exist
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = User(
                username='admin',
                email='admin@fraudshield.com',
                full_name='System Admin',
                role='admin',
                is_verified=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created: admin / admin123")
        
        # Create default fraud rules
        if FraudRule.query.count() == 0:
            default_rules = [
                FraudRule(rule_name='High Amount Transaction', rule_type='amount_threshold', threshold=5000.0),
                FraudRule(rule_name='Rapid Successive Transactions', rule_type='velocity_check', threshold=3.0),
                FraudRule(rule_name='Foreign Transaction', rule_type='geo_anomaly', threshold=1.0),
                FraudRule(rule_name='Night Transaction (12AM-5AM)', rule_type='time_anomaly', threshold=1.0),
                FraudRule(rule_name='Multiple Card Usage', rule_type='card_velocity', threshold=5.0),
            ]
            for rule in default_rules:
                db.session.add(rule)
            db.session.commit()

# ─── Fraud Detection Engine ─────────────────────────────────────────

class FraudDetectionEngine:
    """ML-powered fraud detection engine with deterministic feature engineering, scoring, and explainability"""

    def __init__(self):
        self.weights = {
            'amount_score': 0.25,
            'velocity_score': 0.20,
            'geo_score': 0.15,
            'time_score': 0.10,
            'device_score': 0.10,
            'pattern_score': 0.20,
        }
        self.high_risk_countries = ['Nigeria', 'Russia', 'China', 'Romania', 'Brazil']
        self.high_risk_categories = ['Electronics', 'Gift Cards', 'Cryptocurrency', 'Wire Transfer']
        
        # Preprocessor instance
        self.preprocessor = TransactionPreprocessor.load_config('preprocessing_config.json')

        # Load ML model artifacts
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_version = 'v2.0.0'
        self.model_metadata = {}
        
        try:
            if os.path.exists('fraud_model.pkl') and os.path.exists('scaler.pkl'):
                self.model = joblib.load('fraud_model.pkl')
                self.scaler = joblib.load('scaler.pkl')
                if os.path.exists('features.pkl'):
                    self.feature_names = joblib.load('features.pkl')
                else:
                    self.feature_names = self.preprocessor.feature_names
                
                if os.path.exists('model_metadata.json'):
                    with open('model_metadata.json', 'r') as f:
                        self.model_metadata = json.load(f)
                        self.model_version = self.model_metadata.get('model_version', 'v2.0.0')

                print("✅ Machine Learning model v{} loaded successfully".format(self.model_version))
        except Exception as e:
            print("⚠️ Error loading ML model: {}".format(e))

    def analyze_transaction(self, transaction):
        """Analyze a transaction and return combined risk score, ML prob, rule score, and explainable risk factors."""
        risk_factors = []
        scores = {}
        
        # Create a working copy and populate velocity score if missing
        txn_copy = dict(transaction)
        if 'velocity_score' not in txn_copy:
            txn_copy['velocity_score'] = float(self._check_velocity(txn_copy))

        # ─── 1. ML Model Scoring (Deterministic Preprocessing) ───
        ml_score = 0.0
        ml_prob = 0.0
        if self.model and self.scaler:
            try:
                # Deterministic feature transformation (No random number generation)
                features_df = self.preprocessor.transform_dict(txn_copy)
                target_features = self.feature_names or self.preprocessor.feature_names
                features_aligned = features_df[target_features]
                features_scaled = self.scaler.transform(features_aligned)
                
                probabilities = self.model.predict_proba(features_scaled)
                if len(probabilities) > 0 and len(probabilities[0]) > 1:
                    ml_prob = float(probabilities[0][1])
                    ml_score = float(ml_prob * 100.0)
                
                if ml_prob >= 0.65 or ml_score >= 65.0:
                    risk_factors.append('ML Engine detects pattern deviation (Probability: {:.1f}%)'.format(ml_prob * 100.0))
            except Exception as e:
                print("ML Scoring Error: {}".format(e))
                ml_score = 0.0
                ml_prob = 0.0

        # ─── 2. Rule-Based Checks (Preserved & Enhanced Explainability) ───
        # A. Amount Analysis
        try:
            amount = float(transaction.get('amount', transaction.get('Amount', 0)))
        except (ValueError, TypeError):
            amount = 0.0

        if amount > 10000:
            scores['amount_score'] = 1.0
            risk_factors.append('Extremely high transaction amount (>${:,.0f})'.format(amount))
        elif amount > 5000:
            scores['amount_score'] = 0.8
            risk_factors.append('High transaction amount (>${:,.0f})'.format(amount))
        elif amount > 2000:
            scores['amount_score'] = 0.5
            risk_factors.append('Above average transaction amount')
        else:
            scores['amount_score'] = float(max(0.0, amount / 5000.0))

        # B. Velocity Check
        scores['velocity_score'] = float(self._check_velocity(transaction))
        if scores['velocity_score'] > 0.5:
            risk_factors.append('Multiple transactions in short time period')

        # C. Geographic Analysis
        location = str(transaction.get('location', ''))
        if any(country.lower() in location.lower() for country in self.high_risk_countries):
            scores['geo_score'] = 0.9
            risk_factors.append('Transaction from high-risk location: {}'.format(location))
        else:
            scores['geo_score'] = 0.1

        # D. Time Analysis
        try:
            timestamp = transaction.get('timestamp')
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
            else:
                hour = datetime.now().hour

            if 0 <= hour <= 5:
                scores['time_score'] = 0.7
                risk_factors.append('Transaction during unusual hours (12AM-5AM)')
            else:
                scores['time_score'] = 0.1
        except:
            scores['time_score'] = 0.1

        # E. Device Analysis
        device = str(transaction.get('device_type', 'unknown'))
        if any(d in device.lower() for d in ['vpn', 'tor', 'unknown']):
            scores['device_score'] = 0.8
            risk_factors.append('Suspicious device or connection type: {}'.format(device))
        else:
            scores['device_score'] = 0.1

        # F. Merchant Category Analysis
        category = str(transaction.get('category', ''))
        if any(c.lower() in category.lower() for c in self.high_risk_categories):
            scores['pattern_score'] = 0.7
            risk_factors.append('High-risk merchant category: {}'.format(category))
        else:
            scores['pattern_score'] = 0.15

        # Weighted Rule Score
        rule_score = sum(
            float(scores.get(key, 0.0)) * float(weight)
            for key, weight in self.weights.items()
        ) * 100.0

        # ─── 3. Model Score vs. Rule Score Comparison ───
        score_difference = round(float(ml_score) - float(rule_score), 2)
        if abs(score_difference) <= 15.0:
            primary_driver = 'concurrence'
        elif ml_score > rule_score:
            primary_driver = 'ml_engine'
        else:
            primary_driver = 'rule_engine'

        # ─── 4. Combined Risk Score & Decision ───
        if self.model:
            # Ensemble combination: 50% ML Engine, 50% Rule-Based Engine
            blend_score = (float(ml_score) * 0.50) + (float(rule_score) * 0.50)
            # High-risk preservation: ensure strong risk signals from either engine are not suppressed
            combined_score = max(blend_score, max(ml_score, rule_score))
        else:
            combined_score = float(rule_score)

        fraud_score = float(min(round(float(combined_score), 2), 100.0))

        raw_result = {
            'fraud_score': float(fraud_score),
            'is_fraud': bool(fraud_score >= 65.0),
            'risk_level': str(self._get_risk_level(fraud_score)),
            'ml_score': float(round(ml_score, 2)),
            'rule_score': float(round(rule_score, 2)),
            'ml_probability': float(round(ml_prob, 4)),
            'model_version': str(self.model_version),
            'score_difference': float(score_difference),
            'primary_driver': str(primary_driver),
            'risk_factors': [str(rf) for rf in risk_factors],
            'component_scores': {str(k): float(v) for k, v in scores.items()}
        }

        return sanitize_numpy_types(raw_result)

    def _check_velocity(self, transaction):
        """Check transaction velocity for the card"""
        try:
            raw_card = transaction.get('card_number', '')
            masked_card = mask_card_number(raw_card)
            conn = get_db()
            cursor = conn.cursor()
            five_min_ago = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'SELECT COUNT(*) as cnt FROM transactions WHERE (card_number = ? OR card_number = ?) AND timestamp >= ?',
                (masked_card, raw_card, five_min_ago)
            )
            result = cursor.fetchone()
            conn.close()
            count = result['cnt'] if result else 0
            return min(count / 5.0, 1.0)
        except:
            return 0.2

    def _get_risk_level(self, score):
        if score >= 80:
            return 'critical'
        elif score >= 65:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'


fraud_engine = FraudDetectionEngine()

# ─── Auth Decorator ──────────────────────────────────────────────────

def admin_required(f):
    """Decorator to enforce admin role access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))
        if current_user.role != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            return render_template('message.html',
                                 title='Access Denied',
                                 message='Admin privileges are required to access this page.',
                                 type='error'), 403
        return f(*args, **kwargs)
    return decorated_function

# ─── Authentication Routes ───────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with email verification"""
    from models import EmailVerificationToken
    from utils import EmailService, SecurityHelper
    
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
        
        # Validation
        if not all([first_name, last_name, email, username, password]):
            return render_template('register.html', error='All required fields must be filled')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        # Check password strength
        strength = SecurityHelper.check_password_strength(password)
        if not strength['is_valid']:
            return render_template('register.html', error=', '.join(strength['feedback']))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        
        # Create new user (unverified)
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
            
            # Create email verification token
            verification_token = EmailVerificationToken.generate_token()
            verification = EmailVerificationToken(
                user_id=user.id,
                token=verification_token,
                email=email
            )
            db.session.add(verification)
            db.session.commit()
            
            # Log activity
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
            
            # Send verification email
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Secure login with IP logging and suspicious activity detection"""
    from utils import GeolocationService, SecurityHelper, EmailService
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr
        
        # Get geolocation data
        geo_data = GeolocationService.get_geo_data(ip_address)
        
        user = User.query.filter_by(username=username).first()
        
        # Log login attempt
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
        
        # Check rate limiting
        if SecurityHelper.is_rate_limited(ip_address, '/login', limit=5, window=300):
            login_attempt.failure_reason = 'rate_limited'
            db.session.add(login_attempt)
            db.session.commit()
            return render_template('login.html', error='Too many login attempts. Please try again later.')
        
        if user and user.check_password(password):
            if not user.is_active:
                login_attempt.failure_reason = 'account_locked'
                db.session.add(login_attempt)
                db.session.commit()
                return render_template('login.html', error='Account is disabled. Contact support.')
            
            # Reset rate limit on successful authentication
            SecurityHelper.reset_rate_limit(ip_address, '/login')
            
            # Check for suspicious login
            suspicion = SecurityHelper.is_suspicious_login(user, ip_address, geo_data)
            login_attempt.success = True
            login_attempt.is_suspicious = suspicion['is_suspicious']
            
            # Update/create IP record
            known_ip = IPAddress.query.filter_by(ip_address=ip_address).first()
            if not known_ip:
                known_ip = IPAddress(
                    ip_address=ip_address,
                    user_id=user.id,
                    country=geo_data.get('country'),
                    city=geo_data.get('city'),
                    latitude=geo_data.get('latitude'),
                    longitude=geo_data.get('longitude'),
                    isp=geo_data.get('isp')
                )
                db.session.add(known_ip)
            else:
                known_ip.last_seen = datetime.utcnow()
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Flask-Login: authenticate user
            login_user(user, remember=True)
            session['ip_address'] = ip_address
            
            # Create session record
            session_token = secrets.token_urlsafe(32)
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=request.user_agent.string,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.session.add(user_session)
            
            # Log activity
            activity = UserActivity(
                user_id=user.id,
                activity_type='login',
                action_description='User login',
                ip_address=ip_address,
                user_agent=request.user_agent.string,
                status='success'
            )
            db.session.add(activity)
            db.session.add(login_attempt)
            db.session.commit()
            
            # Send login alert if suspicious
            if suspicion['is_suspicious']:
                EmailService.send_login_alert(
                    user.email,
                    user.full_name or user.username,
                    ip_address,
                    f"{geo_data.get('city')}, {geo_data.get('country')}",
                    request.user_agent.string
                )
                
                # Create suspicious activity record
                susp_activity = SuspiciousActivity(
                    user_id=user.id,
                    activity_name='Suspicious Login',
                    severity='medium',
                    description=f"Login from new location: {geo_data.get('city')}, {geo_data.get('country')}",
                    ip_address=ip_address,
                    country=geo_data.get('country'),
                    risk_score=min(suspicion['suspicion_score'], 100)
                )
                db.session.add(susp_activity)
                db.session.commit()
            
            # Check if user has cards
            card_count = UserCard.query.filter_by(user_id=user.id).count()
            if card_count == 0:
                return redirect(url_for('cards_page', setup=1))
            
            return redirect(url_for('dashboard'))
        
        # Failed login
        login_attempt.failure_reason = 'invalid_credentials'
        if user:
            login_attempt.user_id = user.id
        
        activity = UserActivity(
            user_id=user.id if user else None,
            activity_type='login_failed',
            action_description='Failed login attempt',
            ip_address=ip_address,
            user_agent=request.user_agent.string,
            status='failure',
            error_message='Invalid credentials'
        )
        db.session.add(login_attempt)
        db.session.add(activity)
        db.session.commit()
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user and clear session"""
    if current_user.is_authenticated:
        audit = AuditLog(
            user_id=current_user.id,
            action='logout',
            status='success',
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
    
    logout_user()
    return redirect(url_for('login'))

# ─── User Profile & Settings Routes ─────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    """Display user profile"""
    return render_template('profile.html', user=current_user)

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    user = current_user
    
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    zipcode = request.form.get('zipcode', '').strip()
    country = request.form.get('country', '').strip()
    
    if email != user.email and User.query.filter_by(email=email).first():
        return render_template('profile.html', user=user, error='Email already in use')
    
    user.full_name = f'{first_name} {last_name}'
    user.email = email
    user.phone = phone
    user.address = address
    user.city = city
    user.state = state
    user.zipcode = zipcode
    user.country = country
    user.updated_at = datetime.utcnow()
    
    audit = AuditLog(
        user_id=user.id,
        action='profile_updated',
        status='success',
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return render_template('profile.html', user=user, success='Profile updated successfully')

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    user = current_user
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not user.check_password(current_password):
        return render_template('profile.html', user=user, error='Current password is incorrect')
    
    if new_password != confirm_password:
        return render_template('profile.html', user=user, error='New passwords do not match')
    
    if len(new_password) < 8:
        return render_template('profile.html', user=user, error='Password must be at least 8 characters')
    
    user.set_password(new_password)
    
    audit = AuditLog(
        user_id=user.id,
        action='password_changed',
        status='success',
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return render_template('profile.html', user=user, success='Password changed successfully')

@app.route('/api/notifications', methods=['POST'])
@login_required
def update_notifications():
    """Update notification preferences"""
    user = current_user
    
    email_notif = request.form.get('email_notif') == 'on'
    sms_notif = request.form.get('sms_notif') == 'on'
    
    user.notification_preferences = {
        'email': email_notif,
        'sms': sms_notif
    }
    
    db.session.commit()
    
    return render_template('profile.html', user=user, success='Notification preferences updated')

@app.route('/api/2fa/toggle', methods=['POST'])
@login_required
def toggle_2fa():
    """Toggle two-factor authentication"""
    user = current_user
    user.two_factor_enabled = not user.two_factor_enabled
    db.session.commit()
    
    status = 'enabled' if user.two_factor_enabled else 'disabled'
    return render_template('profile.html', user=user, success=f'Two-factor authentication {status}')

@app.route('/api/logout-all-devices', methods=['POST'])
@login_required
def logout_all_devices():
    """Logout from all devices"""
    # Clear all sessions for this user
    UserSession.query.filter_by(user_id=current_user.id, is_active=True).update({'is_active': False})
    db.session.commit()
    
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account"""
    user = current_user
    
    audit = AuditLog(
        user_id=user.id,
        action='account_deleted',
        status='success',
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    
    # Delete user and related data
    db.session.delete(user)
    db.session.commit()
    
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/transactions')
@login_required
def transactions_page():
    return render_template('transactions.html')

@app.route('/analytics')
@login_required
def analytics_page():
    return render_template('analytics.html')

@app.route('/alerts')
@login_required
def alerts_page():
    return render_template('alerts.html')

@app.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')

@app.route('/cards')
@login_required
def cards_page():
    setup_mode = request.args.get('setup', '0')
    return render_template('cards.html', setup_mode=setup_mode)

# ─── Card Management API ─────────────────────────────────────────────

@app.route('/api/cards', methods=['GET'])
@login_required
def get_user_cards():
    """Get user's registered cards"""
    cards = UserCard.query.filter_by(user_id=current_user.id, is_active=True).order_by(
        UserCard.is_primary.desc(), UserCard.added_at.desc()
    ).all()
    
    cards_data = []
    for card in cards:
        decrypted_num = CardEncryption.decrypt_card_number(card.card_number)
        cards_data.append({
            'id': card.id,
            'card_display': '•••• •••• •••• ' + (decrypted_num[-4:] if len(decrypted_num) >= 4 else '0000'),
            'last4': decrypted_num[-4:] if len(decrypted_num) >= 4 else '0000',
            'card_holder': card.card_holder,
            'card_type': card.card_type,
            'expiry_month': card.expiry_month,
            'expiry_year': card.expiry_year,
            'card_nickname': card.card_nickname,
            'is_primary': card.is_primary,
            'is_active': card.is_active,
            'added_at': card.added_at.isoformat()
        })
    
    return jsonify({'cards': cards_data})

@app.route('/api/cards', methods=['POST'])
@login_required
def add_user_card():
    """Add a new card to user's account"""
    data = request.json
    card_number = data.get('card_number', '').replace(' ', '').replace('-', '')
    card_holder = data.get('card_holder', '').strip()
    expiry_month = data.get('expiry_month', 0)
    expiry_year = data.get('expiry_year', 0)
    card_nickname = data.get('card_nickname', '').strip()
    cvv = data.get('cvv', '')  # validated but NOT stored

    # Validation
    if not card_number or len(card_number) < 13 or len(card_number) > 19:
        return jsonify({'error': 'Invalid card number'}), 400
    if not card_number.isdigit():
        return jsonify({'error': 'Card number must contain only digits'}), 400
    if not card_holder or len(card_holder) < 2:
        return jsonify({'error': 'Card holder name is required'}), 400
    if not (1 <= int(expiry_month) <= 12):
        return jsonify({'error': 'Invalid expiry month'}), 400
    if int(expiry_year) < 2026:
        return jsonify({'error': 'Card has expired'}), 400
    if not cvv or len(cvv) < 3 or len(cvv) > 4:
        return jsonify({'error': 'Invalid CVV'}), 400

    # Detect card type
    card_type = 'visa'
    if card_number.startswith('4'):
        card_type = 'visa'
    elif card_number.startswith(('51','52','53','54','55')) or card_number.startswith('2'):
        card_type = 'mastercard'
    elif card_number.startswith(('34','37')):
        card_type = 'amex'
    elif card_number.startswith('6'):
        card_type = 'discover'

    # Check if card already exists for this user
    user_cards = UserCard.query.filter_by(user_id=current_user.id).all()
    for existing_card in user_cards:
        decrypted_existing = CardEncryption.decrypt_card_number(existing_card.card_number)
        if decrypted_existing == card_number or existing_card.card_number == card_number:
            return jsonify({'error': 'This card is already registered'}), 400

    # If first card, make it primary
    card_count = len(user_cards)
    is_primary = card_count == 0

    encrypted_card_num = CardEncryption.encrypt_card_number(card_number)

    try:
        card = UserCard(
            user_id=current_user.id,
            card_number=encrypted_card_num,
            card_holder=card_holder,
            expiry_month=int(expiry_month),
            expiry_year=int(expiry_year),
            card_type=card_type,
            card_nickname=card_nickname or f'{card_type.title()} ending {card_number[-4:]}',
            is_primary=is_primary
        )
        
        db.session.add(card)
        db.session.commit()
        
        # Log audit event
        audit = AuditLog(
            user_id=current_user.id,
            action='card_added',
            resource=f'card_{card.id}',
            status='success',
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({'message': 'Card added successfully', 'card_type': card_type})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
@login_required
def delete_user_card(card_id):
    """Delete a user's card"""
    card = UserCard.query.filter_by(id=card_id, user_id=current_user.id).first()
    if not card:
        return jsonify({'error': 'Card not found'}), 404
    
    try:
        db.session.delete(card)
        
        audit = AuditLog(
            user_id=current_user.id,
            action='card_deleted',
            resource=f'card_{card_id}',
            status='success',
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({'message': 'Card removed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/cards/<int:card_id>/primary', methods=['POST'])
@login_required
def set_primary_card(card_id):
    """Set a card as primary"""
    card = UserCard.query.filter_by(id=card_id, user_id=current_user.id).first()
    if not card:
        return jsonify({'error': 'Card not found'}), 404
    
    try:
        # Unset all primary cards for this user
        UserCard.query.filter_by(user_id=current_user.id, is_primary=True).update({'is_primary': False})
        
        # Set this card as primary
        card.is_primary = True
        
        audit = AuditLog(
            user_id=current_user.id,
            action='primary_card_changed',
            resource=f'card_{card_id}',
            status='success',
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({'message': 'Primary card updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ─── API Routes ──────────────────────────────────────────────────────

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    total_transactions = conn.execute(
        'SELECT COUNT(*) as cnt FROM transactions WHERE DATE(timestamp) = ?', (today,)
    ).fetchone()['cnt']

    total_fraud = conn.execute(
        'SELECT COUNT(*) as cnt FROM transactions WHERE is_fraud = 1 AND DATE(timestamp) = ?', (today,)
    ).fetchone()['cnt']

    total_amount = conn.execute(
        'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE DATE(timestamp) = ?', (today,)
    ).fetchone()['total']

    fraud_amount = conn.execute(
        'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE is_fraud = 1 AND DATE(timestamp) = ?',
        (today,)
    ).fetchone()['total']

    blocked_cards = conn.execute('SELECT COUNT(*) as cnt FROM blocked_cards').fetchone()['cnt']

    unread_alerts = conn.execute(
        'SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0'
    ).fetchone()['cnt']

    # Weekly trend
    weekly_data = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_label = (datetime.now() - timedelta(days=i)).strftime('%a')
        day_total = conn.execute(
            'SELECT COUNT(*) as cnt FROM transactions WHERE DATE(timestamp) = ?', (day,)
        ).fetchone()['cnt']
        day_fraud = conn.execute(
            'SELECT COUNT(*) as cnt FROM transactions WHERE is_fraud = 1 AND DATE(timestamp) = ?', (day,)
        ).fetchone()['cnt']
        weekly_data.append({'day': day_label, 'total': day_total, 'fraud': day_fraud})

    conn.close()

    return jsonify({
        'total_transactions': total_transactions,
        'total_fraud': total_fraud,
        'fraud_rate': round((total_fraud / max(total_transactions, 1)) * 100, 2),
        'total_amount': round(total_amount, 2),
        'fraud_amount_saved': round(fraud_amount, 2),
        'blocked_cards': blocked_cards,
        'unread_alerts': unread_alerts,
        'weekly_trend': weekly_data
    })

@app.route('/api/dashboard/overview')
@login_required
def dashboard_overview():
    """Comprehensive dashboard overview with filtering and data visualization datasets"""
    db.session.commit()
    conn = get_db()
    user = current_user

    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    risk_level = request.args.get('risk_level', 'all').strip().lower()
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('search', '').strip()

    where_clauses = ['1=1']
    params = []

    # Scoping for non-admin users
    if user and hasattr(user, 'role') and user.role != 'admin':
        raw_card_nums = [CardEncryption.decrypt_card_number(card.card_number) for card in user.cards]
        masked_card_nums = [mask_card_number(num) for num in raw_card_nums]
        all_user_cards = list(set(raw_card_nums + masked_card_nums))
        if all_user_cards:
            placeholders = ','.join(['?' for _ in all_user_cards])
            where_clauses.append(f'card_number IN ({placeholders})')
            params.extend(all_user_cards)
        else:
            where_clauses.append('1=0')

    # Date range filter
    if start_date:
        where_clauses.append('DATE(timestamp) >= ?')
        params.append(start_date)
    if end_date:
        where_clauses.append('DATE(timestamp) <= ?')
        params.append(end_date)

    # Risk level filter
    if risk_level == 'low':
        where_clauses.append('fraud_score < 40')
    elif risk_level == 'medium':
        where_clauses.append('fraud_score >= 40 AND fraud_score < 70')
    elif risk_level == 'high':
        where_clauses.append('fraud_score >= 70 AND fraud_score < 90')
    elif risk_level == 'critical':
        where_clauses.append('fraud_score >= 90')

    # Status filter
    if status_filter == 'fraud':
        where_clauses.append('is_fraud = 1')
    elif status_filter == 'genuine':
        where_clauses.append('is_fraud = 0')
    elif status_filter in ['flagged', 'blocked', 'approved', 'pending']:
        where_clauses.append('status = ?')
        params.append(status_filter)

    # Search filter
    if search:
        where_clauses.append('(card_holder LIKE ? OR merchant LIKE ? OR transaction_id LIKE ? OR location LIKE ? OR category LIKE ?)')
        search_pattern = f'%{search}%'
        params.extend([search_pattern] * 5)

    where_sql = ' AND '.join(where_clauses)

    # 1. KPI Cards
    kpi_query = f'''
        SELECT
            COUNT(*) as total_transactions,
            COALESCE(SUM(amount), 0) as total_amount,
            SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraudulent_transactions,
            SUM(CASE WHEN fraud_score >= 70 THEN 1 ELSE 0 END) as high_risk_transactions,
            SUM(CASE WHEN status = 'blocked' OR is_fraud = 1 THEN 1 ELSE 0 END) as blocked_transactions,
            COALESCE(SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END), 0) as fraud_amount_saved
        FROM transactions WHERE {where_sql}
    '''
    kpi_res = conn.execute(kpi_query, params).fetchone()
    total_txns = kpi_res['total_transactions'] or 0
    total_amt = round(kpi_res['total_amount'] or 0, 2)
    fraud_txns = kpi_res['fraudulent_transactions'] or 0
    fraud_rate = round((fraud_txns / max(total_txns, 1)) * 100, 2)
    high_risk_txns = kpi_res['high_risk_transactions'] or 0
    blocked_txns = kpi_res['blocked_transactions'] or 0
    fraud_amount_saved = round(kpi_res['fraud_amount_saved'] or 0, 2)

    blocked_cards_count = conn.execute('SELECT COUNT(*) as cnt FROM blocked_cards').fetchone()['cnt']
    unread_alerts_count = conn.execute('SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0').fetchone()['cnt']

    # 2. Fraud vs Genuine
    genuine_count = max(0, total_txns - fraud_txns)
    fraud_vs_genuine = {
        'genuine_count': genuine_count,
        'fraud_count': fraud_txns,
        'genuine_rate': round((genuine_count / max(total_txns, 1)) * 100, 2),
        'fraud_rate': fraud_rate
    }

    # 3. Fraud Trends by Day
    day_trend_rows = conn.execute(f'''
        SELECT DATE(timestamp) as day_date,
               COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud,
               COALESCE(SUM(amount), 0) as total_amount
        FROM transactions WHERE {where_sql}
        GROUP BY day_date ORDER BY day_date ASC LIMIT 30
    ''', params).fetchall()
    trends_by_day = [
        {
            'day': r['day_date'],
            'total': r['total'],
            'fraud': r['fraud'],
            'amount': round(r['total_amount'], 2)
        } for r in day_trend_rows
    ]

    # 4. Fraud Trends by Month
    month_trend_rows = conn.execute(f'''
        SELECT strftime('%Y-%m', timestamp) as month_date,
               COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud,
               COALESCE(SUM(amount), 0) as total_amount,
               COALESCE(SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END), 0) as fraud_amount
        FROM transactions WHERE {where_sql}
        GROUP BY month_date ORDER BY month_date ASC LIMIT 12
    ''', params).fetchall()
    trends_by_month = [
        {
            'month': r['month_date'],
            'total': r['total'],
            'fraud': r['fraud'],
            'total_amount': round(r['total_amount'], 2),
            'fraud_amount': round(r['fraud_amount'], 2)
        } for r in month_trend_rows
    ]

    # 5. Risk Score Distribution
    risk_dist_rows = conn.execute(f'''
        SELECT
            CASE
                WHEN fraud_score < 20 THEN '0-20 (Very Low)'
                WHEN fraud_score < 40 THEN '20-40 (Low)'
                WHEN fraud_score < 60 THEN '40-60 (Medium)'
                WHEN fraud_score < 80 THEN '60-80 (High)'
                ELSE '80-100 (Critical)'
            END as score_range,
            COUNT(*) as count
        FROM transactions WHERE {where_sql}
        GROUP BY score_range ORDER BY score_range ASC
    ''', params).fetchall()
    
    risk_order = ['0-20 (Very Low)', '20-40 (Low)', '40-60 (Medium)', '60-80 (High)', '80-100 (Critical)']
    risk_dict = {r['score_range']: r['count'] for r in risk_dist_rows}
    risk_distribution = [{'range': r, 'count': risk_dict.get(r, 0)} for r in risk_order]

    # 6. Hourly Fraud Pattern (00 to 23)
    hourly_rows = conn.execute(f'''
        SELECT strftime('%H', timestamp) as hour,
               COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud
        FROM transactions WHERE {where_sql}
        GROUP BY hour ORDER BY hour ASC
    ''', params).fetchall()
    hourly_map = {r['hour']: {'total': r['total'], 'fraud': r['fraud']} for r in hourly_rows}
    hourly_pattern = [
        {
            'hour': f"{h:02d}:00",
            'total': hourly_map.get(f"{h:02d}", {}).get('total', 0),
            'fraud': hourly_map.get(f"{h:02d}", {}).get('fraud', 0)
        } for h in range(24)
    ]

    # 7. Transaction Amount Distribution
    amount_dist_rows = conn.execute(f'''
        SELECT
            CASE
                WHEN amount < 50 THEN '$0-$50'
                WHEN amount < 200 THEN '$50-$200'
                WHEN amount < 500 THEN '$200-$500'
                WHEN amount < 1000 THEN '$500-$1000'
                ELSE '$1000+'
            END as amount_range,
            COUNT(*) as count,
            SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count
        FROM transactions WHERE {where_sql}
        GROUP BY amount_range
    ''', params).fetchall()
    amount_order = ['$0-$50', '$50-$200', '$200-$500', '$500-$1000', '$1000+']
    amount_map = {r['amount_range']: {'count': r['count'], 'fraud': r['fraud_count']} for r in amount_dist_rows}
    amount_distribution = [
        {
            'range': r,
            'count': amount_map.get(r, {}).get('count', 0),
            'fraud_count': amount_map.get(r, {}).get('fraud', 0)
        } for r in amount_order
    ]

    # 8. Top Fraud Categories
    category_rows = conn.execute(f'''
        SELECT category,
               COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
               COALESCE(SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END), 0) as fraud_amount
        FROM transactions WHERE {where_sql}
        GROUP BY category ORDER BY fraud_count DESC, total DESC LIMIT 10
    ''', params).fetchall()
    top_categories = [
        {
            'category': r['category'] or 'Uncategorized',
            'total': r['total'],
            'fraud_count': r['fraud_count'],
            'fraud_amount': round(r['fraud_amount'], 2)
        } for r in category_rows
    ]

    # 9. High-Risk Locations
    location_rows = conn.execute(f'''
        SELECT location,
               COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
               COALESCE(AVG(fraud_score), 0) as avg_risk,
               COALESCE(SUM(amount), 0) as total_amount
        FROM transactions WHERE {where_sql}
        GROUP BY location ORDER BY fraud_count DESC, avg_risk DESC LIMIT 10
    ''', params).fetchall()
    high_risk_locations = [
        {
            'location': r['location'] or 'Unknown',
            'total': r['total'],
            'fraud_count': r['fraud_count'],
            'avg_risk': round(r['avg_risk'], 1),
            'total_amount': round(r['total_amount'], 2),
            'fraud_rate': round((r['fraud_count'] / max(r['total'], 1)) * 100, 1)
        } for r in location_rows
    ]

    # 10. Recent Transactions matching filter
    recent_txn_rows = conn.execute(f'''
        SELECT * FROM transactions WHERE {where_sql}
        ORDER BY timestamp DESC LIMIT 8
    ''', params).fetchall()
    recent_transactions = [dict(r) for r in recent_txn_rows]
    for t in recent_transactions:
        if t.get('timestamp'):
            if hasattr(t['timestamp'], 'isoformat'):
                t['timestamp'] = t['timestamp'].isoformat()

    # 11. Alerts
    alert_rows = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC LIMIT 5').fetchall()
    recent_alerts = [dict(r) for r in alert_rows]

    conn.close()

    return jsonify({
        'kpi': {
            'total_transactions': total_txns,
            'total_amount': total_amt,
            'fraudulent_transactions': fraud_txns,
            'fraud_rate': fraud_rate,
            'high_risk_transactions': high_risk_txns,
            'blocked_transactions': blocked_txns,
            'fraud_amount_saved': fraud_amount_saved,
            'blocked_cards': blocked_cards_count,
            'unread_alerts': unread_alerts_count
        },
        'charts': {
            'fraud_vs_genuine': fraud_vs_genuine,
            'trends_by_day': trends_by_day,
            'trends_by_month': trends_by_month,
            'risk_distribution': risk_distribution,
            'hourly_pattern': hourly_pattern,
            'amount_distribution': amount_distribution,
            'top_categories': top_categories,
            'high_risk_locations': high_risk_locations
        },
        'recent_transactions': recent_transactions,
        'recent_alerts': recent_alerts
    })


@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    conn = get_db()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    offset = (page - 1) * per_page

    query = 'SELECT * FROM transactions WHERE 1=1'
    params = []

    if status_filter:
        if status_filter == 'fraud':
            query += ' AND is_fraud = 1'
        elif status_filter == 'safe':
            query += ' AND is_fraud = 0'

    if search:
        query += ' AND (card_holder LIKE ? OR transaction_id LIKE ? OR merchant LIKE ?)'
        params.extend([f'%{search}%'] * 3)

    total = conn.execute(
        query.replace('SELECT *', 'SELECT COUNT(*) as cnt'), params
    ).fetchone()['cnt']

    query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    transactions = [dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()

    for t in transactions:
        t['card_number'] = mask_card_number(t.get('card_number', ''))
        if t.get('risk_factors'):
            try:
                t['risk_factors'] = json.loads(t['risk_factors'])
            except:
                t['risk_factors'] = []

    return jsonify({
        'transactions': transactions,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page)
    })

@app.route('/api/transactions/process', methods=['POST'])
@login_required
def process_transaction():
    """Process a new transaction through fraud detection"""
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({
                'error': 'Invalid or missing JSON payload in request body',
                'status': 'error'
            }), 400

        required = ['card_number', 'card_holder', 'amount', 'merchant', 'category', 'location']
        missing = [field for field in required if field not in data or data[field] is None or str(data[field]).strip() == '']
        if missing:
            return jsonify({
                'error': f'Missing required field(s): {", ".join(missing)}',
                'status': 'error'
            }), 400

        # Validate transaction amount
        try:
            amount = float(data['amount'])
            if amount < 0:
                return jsonify({
                    'error': 'Transaction amount cannot be negative',
                    'status': 'error'
                }), 400
            if math.isnan(amount) or math.isinf(amount):
                return jsonify({
                    'error': 'Transaction amount must be a finite number',
                    'status': 'error'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Transaction amount must be a valid number',
                'status': 'error'
            }), 400

        # Check if card is blocked
        raw_card = str(data['card_number']).strip()
        masked_card = mask_card_number(raw_card)
        conn = get_db()
        blocked_rows = conn.execute('SELECT card_number FROM blocked_cards').fetchall()
        is_blocked = False
        for row in blocked_rows:
            b_card = row['card_number']
            decrypted = CardEncryption.decrypt_card_number(b_card)
            if b_card == raw_card or b_card == masked_card or decrypted == raw_card or mask_card_number(decrypted) == masked_card:
                is_blocked = True
                break

        if is_blocked:
            conn.close()
            return jsonify(sanitize_numpy_types({
                'status': 'blocked',
                'message': 'This card has been blocked. Transaction denied.',
                'fraud_score': 100.0,
                'is_fraud': True,
                'risk_level': 'critical',
                'risk_factors': ['Card is on blocked list']
            })), 403

        # Run fraud detection with exception safety
        try:
            result = fraud_engine.analyze_transaction(data)
        except Exception as e:
            conn.close()
            print(f"Error during analyze_transaction: {e}")
            return jsonify({
                'error': 'Failed to process fraud detection on transaction',
                'details': str(e),
                'status': 'error'
            }), 500

        transaction_id = 'TXN' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))

        status = 'declined' if bool(result['is_fraud']) else 'approved'

        conn.execute('''
            INSERT INTO transactions
            (transaction_id, card_number, card_holder, amount, merchant, category,
             location, ip_address, device_type, is_fraud, fraud_score, status, risk_factors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            masked_card,
            str(data['card_holder']),
            float(amount),
            str(data['merchant']),
            str(data['category']),
            str(data['location']),
            str(data.get('ip_address', request.remote_addr or '127.0.0.1')),
            str(data.get('device_type', 'Web Browser')),
            1 if bool(result['is_fraud']) else 0,
            float(result['fraud_score']),
            status,
            json.dumps(result['risk_factors'])
        ))

        # Create alert if fraud detected
        if float(result['fraud_score']) >= 40:
            severity = 'critical' if float(result['fraud_score']) >= 80 else ('high' if float(result['fraud_score']) >= 65 else 'medium')
            conn.execute('''
                INSERT INTO alerts (transaction_id, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            ''', (
                transaction_id,
                'fraud_detection',
                severity,
                f"Suspicious transaction detected: ${amount:.2f} at {data['merchant']} "
                f"(Score: {result['fraud_score']}%)"
            ))

        conn.commit()
        conn.close()

        response_payload = sanitize_numpy_types({
            'transaction_id': transaction_id,
            'status': status,
            'fraud_score': float(result['fraud_score']),
            'risk_level': str(result['risk_level']),
            'ml_score': float(result.get('ml_score', 0.0)),
            'rule_score': float(result.get('rule_score', 0.0)),
            'ml_probability': float(result.get('ml_probability', 0.0)),
            'model_version': str(result.get('model_version', 'v2.0.0')),
            'score_difference': float(result.get('score_difference', 0.0)),
            'primary_driver': str(result.get('primary_driver', 'concurrence')),
            'risk_factors': result['risk_factors'],
            'component_scores': result.get('component_scores', {}),
            'is_fraud': bool(result['is_fraud']),
            'message': 'Transaction declined - Fraud detected!' if result['is_fraud'] else 'Transaction approved'
        })

        return jsonify(response_payload), 200

    except Exception as e:
        print(f"Error in process_transaction endpoint: {e}")
        return jsonify({
            'error': 'Internal server error processing transaction',
            'details': str(e),
            'status': 'error'
        }), 500

@app.route('/api/transactions/<transaction_id>/review', methods=['POST'])
@login_required
def review_transaction(transaction_id):
    data = request.get_json()
    action = data.get('action', '')

    conn = get_db()
    conn.execute('''
        UPDATE transactions SET status = ?, reviewed_by = ?, reviewed_at = ?
        WHERE transaction_id = ?
    ''', (action, current_user.username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), transaction_id))
    conn.commit()
    conn.close()

    return jsonify({'message': f'Transaction {action} successfully'})

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    conn = get_db()
    alerts = [dict(row) for row in conn.execute(
        'SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50'
    ).fetchall()]
    conn.close()
    return jsonify({'alerts': alerts})

@app.route('/api/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    conn = get_db()
    conn.execute('UPDATE alerts SET is_read = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Alert marked as read'})

@app.route('/api/analytics/overview')
@login_required
def analytics_overview():
    conn = get_db()

    # Fraud by category
    categories = conn.execute('''
        SELECT category, COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
               COALESCE(SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END), 0) as fraud_amount
        FROM transactions GROUP BY category ORDER BY fraud_count DESC
    ''').fetchall()

    # Fraud by location
    locations = conn.execute('''
        SELECT location, COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count
        FROM transactions GROUP BY location ORDER BY fraud_count DESC LIMIT 10
    ''').fetchall()

    # Hourly distribution
    hourly = conn.execute('''
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count
        FROM transactions GROUP BY hour ORDER BY hour
    ''').fetchall()

    # Monthly trend
    monthly = conn.execute('''
        SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as total,
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
               COALESCE(SUM(amount), 0) as total_amount,
               COALESCE(SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END), 0) as fraud_amount
        FROM transactions GROUP BY month ORDER BY month DESC LIMIT 12
    ''').fetchall()

    # Risk score distribution
    risk_dist = conn.execute('''
        SELECT
            CASE
                WHEN fraud_score < 20 THEN '0-20'
                WHEN fraud_score < 40 THEN '20-40'
                WHEN fraud_score < 60 THEN '40-60'
                WHEN fraud_score < 80 THEN '60-80'
                ELSE '80-100'
            END as score_range,
            COUNT(*) as count
        FROM transactions GROUP BY score_range ORDER BY score_range
    ''').fetchall()

    # Top fraudulent merchants
    top_merchants = conn.execute('''
        SELECT merchant, COUNT(*) as fraud_count,
               COALESCE(SUM(amount), 0) as total_fraud_amount
        FROM transactions WHERE is_fraud = 1
        GROUP BY merchant ORDER BY fraud_count DESC LIMIT 10
    ''').fetchall()

    conn.close()

    return jsonify({
        'categories': [dict(r) for r in categories],
        'locations': [dict(r) for r in locations],
        'hourly': [dict(r) for r in hourly],
        'monthly': [dict(r) for r in monthly],
        'risk_distribution': [dict(r) for r in risk_dist],
        'top_merchants': [dict(r) for r in top_merchants]
    })

@app.route('/api/cards/block', methods=['POST'])
@login_required
def block_card():
    data = request.get_json() or {}
    raw_card = str(data.get('card_number', '')).strip()
    reason = data.get('reason', 'Suspected fraud')
    if not raw_card:
        return jsonify({'error': 'Card number required'}), 400

    encrypted_card = CardEncryption.encrypt_card_number(raw_card)

    conn = get_db()
    try:
        conn.execute('INSERT INTO blocked_cards (card_number, reason, blocked_by) VALUES (?, ?, ?)',
                     (encrypted_card, reason, current_user.username))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Card blocked successfully'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Card is already blocked'}), 409

@app.route('/api/cards/unblock', methods=['POST'])
@login_required
def unblock_card():
    data = request.get_json() or {}
    target_card = str(data.get('card_number', '')).strip()
    if not target_card:
        return jsonify({'error': 'Card number required'}), 400

    conn = get_db()
    blocked_rows = conn.execute('SELECT id, card_number FROM blocked_cards').fetchall()
    deleted_any = False
    for row in blocked_rows:
        stored = row['card_number']
        decrypted = CardEncryption.decrypt_card_number(stored)
        if stored == target_card or decrypted == target_card or mask_card_number(stored) == target_card or mask_card_number(decrypted) == target_card:
            conn.execute('DELETE FROM blocked_cards WHERE id = ?', (row['id'],))
            deleted_any = True
    conn.commit()
    conn.close()
    if deleted_any:
        return jsonify({'message': 'Card unblocked successfully'})
    return jsonify({'message': 'Card was not found in block list'}), 404

@app.route('/api/blocked-cards')
@login_required
def get_blocked_cards():
    conn = get_db()
    rows = conn.execute('SELECT * FROM blocked_cards ORDER BY blocked_at DESC').fetchall()
    cards = []
    for row in rows:
        r_dict = dict(row)
        decrypted = CardEncryption.decrypt_card_number(r_dict['card_number'])
        r_dict['card_number'] = mask_card_number(decrypted)
        cards.append(r_dict)
    conn.close()
    return jsonify({'cards': cards})

@app.route('/api/simulate', methods=['POST'])
@login_required
def simulate_transactions():
    """Generate simulated transactions for demo purposes using dataset for realism"""
    count = int(request.json.get('count', 10))
    count = min(count, 100)

    # Use dataset for realistic simulation if available
    dataset_rows = None
    try:
        csv_path = r'c:\Users\Dinesh A\Downloads\credit card fraud\creditcard_2023.csv'
        if os.path.exists(csv_path):
            # Read a random chunk from the large CSV
            skip = random.randint(1, 50000)
            dataset_rows = pd.read_csv(csv_path, skiprows=range(1, skip), nrows=count)
    except Exception as e:
        print(f"Simulation Dataset Error: {e}")

    merchants = [
        ('Amazon', 'Online Shopping'), ('Walmart', 'Retail'), ('Shell Gas', 'Gas Station'),
        ('Starbucks', 'Restaurant'), ('Best Buy', 'Electronics'), ('Apple Store', 'Electronics'),
        ('Netflix', 'Subscription'), ('Uber', 'Transportation'), ('Delta Airlines', 'Travel'),
        ('Crypto Exchange', 'Cryptocurrency'), ('Gift Card Mall', 'Gift Cards'),
        ('Wire Transfer Co', 'Wire Transfer'), ('Local Grocery', 'Grocery'),
        ('Hotel Marriott', 'Travel'), ('Steam', 'Gaming')
    ]

    locations = [
        'New York, USA', 'Los Angeles, USA', 'Chicago, USA', 'Houston, USA',
        'London, UK', 'Lagos, Nigeria', 'Moscow, Russia', 'Tokyo, Japan',
        'Paris, France', 'Mumbai, India', 'Bucharest, Romania', 'São Paulo, Brazil',
        'Toronto, Canada', 'Sydney, Australia', 'Berlin, Germany'
    ]

    devices = ['Desktop Chrome', 'Mobile Safari', 'Mobile Android', 'Desktop Firefox', 'Unknown', 'VPN', 'Tablet']

    names = [
        'John Smith', 'Maria Garcia', 'David Johnson', 'Sarah Williams',
        'James Brown', 'Emily Davis', 'Michael Wilson', 'Olivia Taylor',
        'Robert Anderson', 'Emma Thomas'
    ]

    results = []
    
    for i in range(count):
        if dataset_rows is not None and i < len(dataset_rows):
            # Real dataset simulation
            row = dataset_rows.iloc[i]
            amount = float(row['Amount'])
            is_dataset_fraud = int(row['Class']) == 1
            
            # Create synthetic data to wrap the dataset features
            if is_dataset_fraud:
                merchant, category = random.choice([
                    ('Crypto Exchange', 'Cryptocurrency'),
                    ('Gift Card Mall', 'Gift Cards'),
                    ('Electronics Hub', 'Electronics')
                ])
                location = random.choice(['Lagos, Nigeria', 'Moscow, Russia', 'São Paulo, Brazil'])
                device = random.choice(['VPN', 'Unknown'])
            else:
                merchant, category = random.choice(merchants[:8])
                location = random.choice(locations[:8])
                device = random.choice(devices[:4])
                
            txn_data = {
                'card_number': f"****-****-****-{random.randint(1000, 9999)}",
                'card_holder': random.choice(names),
                'amount': amount,
                'merchant': merchant,
                'category': category,
                'location': location,
                'ip_address': f'{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}',
                'device_type': device
            }
            # Inject dataset PCA features for the ML model to pick up
            for col in dataset_rows.columns:
                if col.startswith('V'):
                    txn_data[col] = float(row[col])
        else:
            # Fallback simulator
            merchant, category = random.choice(merchants)
            is_suspicious = random.random() < 0.3
            if is_suspicious:
                amount = round(random.uniform(2000, 15000), 2)
                location = random.choice(['Lagos, Nigeria', 'Moscow, Russia', 'Bucharest, Romania'])
                device = 'VPN'
                merchant, category = ('Crypto Exchange', 'Cryptocurrency')
            else:
                amount = round(random.uniform(5, 500), 2)
                location = random.choice(locations[:5])
                device = 'Desktop Chrome'
            
            txn_data = {
                'card_number': f"****-****-****-{random.randint(1000, 9999)}",
                'card_holder': random.choice(names),
                'amount': amount,
                'merchant': merchant,
                'category': category,
                'location': location,
                'ip_address': '127.0.0.1',
                'device_type': device
            }

        # Process through fraud engine (now ML-powered)
        result = fraud_engine.analyze_transaction(txn_data)
        transaction_id = 'TXN' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10000, 99999))
        status = 'declined' if result['is_fraud'] else 'approved'

        conn = get_db()
        conn.execute('''
            INSERT INTO transactions
            (transaction_id, card_number, card_holder, amount, merchant, category,
             location, ip_address, device_type, is_fraud, fraud_score, status, risk_factors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id, txn_data['card_number'], txn_data['card_holder'], txn_data['amount'],
            merchant, category, location, txn_data['ip_address'], device,
            1 if result['is_fraud'] else 0, result['fraud_score'], status,
            json.dumps(result['risk_factors'])
        ))

        if result['fraud_score'] >= 40:
            severity = 'critical' if result['fraud_score'] >= 80 else ('high' if result['fraud_score'] >= 65 else 'medium')
            conn.execute('''
                INSERT INTO alerts (transaction_id, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            ''', (
                transaction_id, 'fraud_detection', severity,
                f"Suspicious activity: ${txn_data['amount']:.2f} at {merchant} (ML Score: {result['fraud_score']}%)"
            ))

        conn.commit()
        conn.close()

        results.append({
            'transaction_id': transaction_id,
            'status': status,
            'fraud_score': result['fraud_score'],
            'is_fraud': result['is_fraud']
        })

    return jsonify({
        'message': f'{count} transactions simulated using ML dataset',
        'results': results,
        'fraud_detected': sum(1 for r in results if r['is_fraud'])
    })

@app.route('/api/fraud-rules')
@login_required
def get_fraud_rules():
    conn = get_db()
    rules = [dict(row) for row in conn.execute('SELECT * FROM fraud_rules').fetchall()]
    conn.close()
    return jsonify({'rules': rules})

@app.route('/api/fraud-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_fraud_rule(rule_id):
    conn = get_db()
    rule = conn.execute('SELECT * FROM fraud_rules WHERE id = ?', (rule_id,)).fetchone()
    if rule:
        new_status = 0 if rule['is_active'] else 1
        conn.execute('UPDATE fraud_rules SET is_active = ? WHERE id = ?', (new_status, rule_id))
        conn.commit()
    conn.close()
    return jsonify({'message': 'Rule updated'})

# ─── Enhanced Transaction History Features ──────────────────────────

@app.route('/api/transactions/history')
@login_required
def get_transaction_history():
    """Get user's transaction history with advanced filtering"""
    conn = get_db()
    user = current_user
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    amount_min = request.args.get('amount_min', '')
    amount_max = request.args.get('amount_max', '')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'timestamp')
    sort_order = request.args.get('sort_order', 'DESC')
    
    offset = (page - 1) * per_page
    params = []
    
    query = 'SELECT * FROM transactions WHERE 1=1'
    
    # Only show transactions for user's own cards
    if user and user.role != 'admin':
        raw_card_nums = [CardEncryption.decrypt_card_number(card.card_number) for card in user.cards]
        masked_card_nums = [mask_card_number(num) for num in raw_card_nums]
        all_user_cards = list(set(raw_card_nums + masked_card_nums))
        if all_user_cards:
            placeholders = ','.join(['?' for _ in all_user_cards])
            query += f' AND card_number IN ({placeholders})'
            params.extend(all_user_cards)
        else:
            return jsonify({'transactions': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0})
    
    # Date range filter
    if date_from:
        query += ' AND DATE(timestamp) >= ?'
        params.append(date_from)
    if date_to:
        query += ' AND DATE(timestamp) <= ?'
        params.append(date_to)
    
    # Status filter (fraud/safe/approved/declined)
    if status_filter:
        if status_filter == 'fraud':
            query += ' AND is_fraud = 1'
        elif status_filter == 'safe':
            query += ' AND is_fraud = 0'
        elif status_filter in ['approved', 'declined']:
            query += ' AND status = ?'
            params.append(status_filter)
    
    # Category filter
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    
    # Amount range filter
    if amount_min:
        query += ' AND amount >= ?'
        params.append(float(amount_min))
    if amount_max:
        query += ' AND amount <= ?'
        params.append(float(amount_max))
    
    # Search filter (merchant, card holder, ID)
    if search:
        query += ' AND (merchant LIKE ? OR card_holder LIKE ? OR transaction_id LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    # Get total count
    count_query = query.replace('SELECT *', 'SELECT COUNT(*) as cnt')
    total = conn.execute(count_query, params).fetchone()['cnt']
    
    # Add sorting and pagination
    valid_sort_by = ['timestamp', 'amount', 'fraud_score', 'status']
    if sort_by not in valid_sort_by:
        sort_by = 'timestamp'
    if sort_order not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    query += f' ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    transactions = [dict(row) for row in conn.execute(query, params).fetchall()]
    
    # Parse risk factors JSON and mask card numbers
    for t in transactions:
        t['card_number'] = mask_card_number(t.get('card_number', ''))
        if t.get('risk_factors'):
            try:
                t['risk_factors'] = json.loads(t['risk_factors'])
            except:
                t['risk_factors'] = []
    
    conn.close()
    
    return jsonify({
        'transactions': transactions,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page)
    })

@app.route('/api/transactions/<transaction_id>/details')
@login_required
def get_transaction_details(transaction_id):
    """Get detailed information about a specific transaction"""
    conn = get_db()
    
    transaction = conn.execute(
        'SELECT * FROM transactions WHERE transaction_id = ?',
        (transaction_id,)
    ).fetchone()
    
    if not transaction:
        conn.close()
        return jsonify({'error': 'Transaction not found'}), 404
    
    t_dict = dict(transaction)
    t_dict['card_number'] = mask_card_number(t_dict.get('card_number', ''))
    if t_dict.get('risk_factors'):
        try:
            t_dict['risk_factors'] = json.loads(t_dict['risk_factors'])
        except:
            t_dict['risk_factors'] = []
    
    # Get related alerts
    alerts = [dict(row) for row in conn.execute(
        'SELECT * FROM alerts WHERE transaction_id = ?',
        (transaction_id,)
    ).fetchall()]
    
    conn.close()
    
    return jsonify({
        'transaction': t_dict,
        'alerts': alerts
    })

@app.route('/api/transactions/statistics')
@login_required
def get_transaction_statistics():
    """Get transaction statistics and summary"""
    conn = get_db()
    user = current_user
    
    # Filter by user's cards if not admin
    base_query = 'FROM transactions WHERE 1=1'
    params = []
    
    if user and user.role != 'admin':
        raw_card_nums = [CardEncryption.decrypt_card_number(card.card_number) for card in user.cards]
        masked_card_nums = [mask_card_number(num) for num in raw_card_nums]
        all_user_cards = list(set(raw_card_nums + masked_card_nums))
        if all_user_cards:
            placeholders = ','.join(['?' for _ in all_user_cards])
            base_query += f' AND card_number IN ({placeholders})'
            params.extend(all_user_cards)
        else:
            return jsonify({
                'total_transactions': 0,
                'total_amount': 0,
                'fraud_count': 0,
                'fraud_amount': 0,
                'fraud_rate': 0
            })
    
    # Total transactions
    total = conn.execute(f'SELECT COUNT(*) as cnt {base_query}', params).fetchone()['cnt']
    
    # Total amount
    total_amount = conn.execute(f'SELECT COALESCE(SUM(amount), 0) as amt {base_query}', params).fetchone()['amt']
    
    # Fraud statistics
    fraud_count = conn.execute(
        f'SELECT COUNT(*) as cnt {base_query} AND is_fraud = 1', 
        params
    ).fetchone()['cnt']
    
    fraud_amount = conn.execute(
        f'SELECT COALESCE(SUM(amount), 0) as amt {base_query} AND is_fraud = 1',
        params
    ).fetchone()['amt']
    
    fraud_rate = round((fraud_count / max(total, 1)) * 100, 2)
    
    # Average transaction amount
    avg_amount = conn.execute(
        f'SELECT COALESCE(AVG(amount), 0) as avg {base_query}',
        params
    ).fetchone()['avg']
    
    # Transactions by category
    category_stats = [dict(row) for row in conn.execute(f'''
        SELECT category, COUNT(*) as count, 
               SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
               COALESCE(SUM(amount), 0) as total_amount
        {base_query}
        GROUP BY category ORDER BY count DESC LIMIT 10
    ''', params).fetchall()]
    
    # Transactions by status
    status_stats = [dict(row) for row in conn.execute(f'''
        SELECT status, COUNT(*) as count, COALESCE(SUM(amount), 0) as total_amount
        {base_query}
        GROUP BY status
    ''', params).fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_transactions': total,
        'total_amount': round(total_amount, 2),
        'fraud_count': fraud_count,
        'fraud_amount': round(fraud_amount, 2),
        'fraud_rate': fraud_rate,
        'average_amount': round(avg_amount, 2),
        'by_category': category_stats,
        'by_status': status_stats
    })

def query_filtered_transactions_data(filters, user):
    """Query transactions applying security & multi-dimensional filters"""
    query = Transaction.query

    # Authorization Check: Non-admin users ONLY see their own transactions
    if user.role != 'admin':
        raw_card_nums = [CardEncryption.decrypt_card_number(card.card_number) for card in user.cards]
        masked_card_nums = [mask_card_number(num) for num in raw_card_nums]
        user_cards = list(set([c for c in (raw_card_nums + masked_card_nums) if c]))
        
        if user_cards:
            query = query.filter(
                or_(
                    Transaction.user_id == user.id,
                    Transaction.card_number.in_(user_cards)
                )
            )
        else:
            query = query.filter(Transaction.user_id == user.id)
    else:
        # Admin can filter by specific user if provided
        target_user = filters.get('user_id') or filters.get('user')
        if target_user and str(target_user).strip() not in ('all', ''):
            try:
                query = query.filter(Transaction.user_id == int(target_user))
            except (ValueError, TypeError):
                target_u = User.query.filter((User.username == str(target_user)) | (User.email == str(target_user))).first()
                if target_u:
                    query = query.filter(Transaction.user_id == target_u.id)

    # Filter: Date Range
    date_from = filters.get('date_from') or filters.get('start_date')
    if date_from and str(date_from).strip():
        try:
            df = datetime.fromisoformat(str(date_from).replace('Z', ''))
            query = query.filter(Transaction.timestamp >= df)
        except Exception:
            try:
                df = datetime.strptime(str(date_from)[:10], '%Y-%m-%d')
                query = query.filter(Transaction.timestamp >= df)
            except Exception:
                pass

    date_to = filters.get('date_to') or filters.get('end_date')
    if date_to and str(date_to).strip():
        try:
            dt = datetime.fromisoformat(str(date_to).replace('Z', ''))
            if len(str(date_to)) <= 10:
                dt = dt + timedelta(days=1) - timedelta(microseconds=1)
            query = query.filter(Transaction.timestamp <= dt)
        except Exception:
            try:
                dt = datetime.strptime(str(date_to)[:10], '%Y-%m-%d') + timedelta(days=1) - timedelta(microseconds=1)
                query = query.filter(Transaction.timestamp <= dt)
            except Exception:
                pass

    # Filter: Fraud Status
    fraud_status = filters.get('fraud_status') or filters.get('status')
    if fraud_status and str(fraud_status).strip() not in ('all', ''):
        f_stat = str(fraud_status).lower()
        if f_stat in ('genuine', 'safe'):
            query = query.filter(Transaction.is_fraud == False, Transaction.fraud_score < 0.7)
        elif f_stat in ('fraud', 'fraudulent'):
            query = query.filter(or_(Transaction.is_fraud == True, Transaction.fraud_score >= 0.7))
        else:
            query = query.filter(Transaction.status == f_stat)

    # Filter: Risk Level
    risk_level = filters.get('risk_level')
    if risk_level and str(risk_level).strip() not in ('all', ''):
        rl = str(risk_level).lower()
        if rl == 'low':
            query = query.filter(Transaction.fraud_score <= 0.3)
        elif rl == 'medium':
            query = query.filter(Transaction.fraud_score > 0.3, Transaction.fraud_score <= 0.7)
        elif rl == 'high':
            query = query.filter(Transaction.fraud_score >= 0.7)
        elif rl == 'critical':
            query = query.filter(Transaction.fraud_score >= 0.9)

    # Filter: Amount Range
    min_amount = filters.get('min_amount')
    if min_amount is not None and str(min_amount).strip() != '':
        try:
            query = query.filter(Transaction.amount >= float(min_amount))
        except (ValueError, TypeError):
            pass

    max_amount = filters.get('max_amount')
    if max_amount is not None and str(max_amount).strip() != '':
        try:
            query = query.filter(Transaction.amount <= float(max_amount))
        except (ValueError, TypeError):
            pass

    db_txns = query.order_by(Transaction.timestamp.desc()).all()

    txns = []
    for t in db_txns:
        txns.append({
            'id': t.id,
            'transaction_id': t.transaction_id,
            'user_id': t.user_id,
            'card_number': mask_card_number(t.card_number),
            'card_holder': t.card_holder,
            'amount': t.amount,
            'merchant': t.merchant,
            'category': t.category,
            'location': t.location,
            'ip_address': t.ip_address,
            'device_type': t.device_type,
            'is_fraud': t.is_fraud,
            'fraud_score': t.fraud_score,
            'status': t.status,
            'timestamp': t.timestamp
        })
    return txns


@app.route('/api/transactions/export', methods=['GET'])
@login_required
def export_transactions():
    """Export transactions directly as CSV or PDF download stream"""
    from utils import ReportGenerator
    from flask import Response

    file_format = request.args.get('format', 'csv').lower()
    if file_format not in ('csv', 'pdf'):
        file_format = 'csv'

    filters = {
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'fraud_status': request.args.get('status', '') or request.args.get('fraud_status', ''),
        'risk_level': request.args.get('risk_level', ''),
        'min_amount': request.args.get('min_amount', ''),
        'max_amount': request.args.get('max_amount', ''),
        'user_id': request.args.get('user_id', '')
    }

    transactions = query_filtered_transactions_data(filters, current_user)
    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_format}"

    if file_format == 'csv':
        csv_data = ReportGenerator.generate_csv(transactions)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    else:
        pdf_bytes = ReportGenerator.generate_pdf('pdf_transaction_report', 'Transaction Detail Report', transactions, filters=filters)
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )


# ─── Email Verification & Authentication ───────────────────────────

@app.route('/verify-email/<token>', methods=['GET', 'POST'])
def verify_email(token):
    """Verify email address"""
    from models import EmailVerificationToken
    from utils import EmailService
    
    verification = EmailVerificationToken.query.filter_by(token=token).first()
    
    if not verification or not verification.is_valid():
        return render_template('message.html', 
                             title='Verification Failed',
                             message='Invalid or expired verification link',
                             type='error')
    
    verification.is_verified = True
    verification.verified_at = datetime.utcnow()
    verification.user.is_verified = True
    verification.user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return render_template('message.html',
                         title='Email Verified!',
                         message='Your email has been successfully verified. You can now login.',
                         type='success',
                         action_link='/login')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    from models import PasswordResetToken, User
    from utils import EmailService
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists
            return render_template('forgot_password.html', message='Check your email for password reset link')
        
        # Create reset token
        token = PasswordResetToken.generate_token()
        reset = PasswordResetToken(user_id=user.id, token=token)
        db.session.add(reset)
        db.session.commit()
        
        # Send reset email
        EmailService.send_password_reset_email(user.email, token, user.full_name or user.username)
        
        return render_template('forgot_password.html', message='Check your email for password reset link', success=True)
    
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    from models import PasswordResetToken
    from utils import SecurityHelper, EmailService
    
    reset = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset or not reset.is_valid():
        return render_template('message.html',
                             title='Reset Failed',
                             message='Invalid or expired reset link',
                             type='error')
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validate password
        strength = SecurityHelper.check_password_strength(password)
        if not strength['is_valid']:
            return render_template('reset_password.html',
                                 token=token,
                                 errors=strength['feedback'])
        
        if password != password_confirm:
            return render_template('reset_password.html',
                                 token=token,
                                 errors=['Passwords do not match'])
        
        # Update password
        user = reset.user
        user.set_password(password)
        user.updated_at = datetime.utcnow()
        reset.is_used = True
        reset.used_at = datetime.utcnow()
        
        # Log activity
        activity = UserActivity(
            user_id=user.id,
            activity_type='password_reset',
            action_description='Password reset via email link',
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(activity)
        db.session.commit()
        
        # Send confirmation email
        EmailService.send_password_changed_email(user.email, user.full_name or user.username)
        
        return render_template('message.html',
                             title='Password Reset Successful',
                             message='Your password has been reset. You can now login.',
                             type='success',
                             action_link='/login')
    
    return render_template('reset_password.html', token=token)


# ─── Session & Security Management ──────────────────────────────────

@app.route('/api/login-attempts', methods=['GET'])
@login_required
def get_login_attempts():
    """Get user's recent login attempts"""
    from models import LoginAttempt
    
    attempts = LoginAttempt.query.filter_by(username=current_user.username).order_by(
        LoginAttempt.created_at.desc()
    ).limit(20).all()
    
    return jsonify({
        'attempts': [{
            'ip_address': a.ip_address,
            'success': a.success,
            'country': a.country,
            'city': a.city,
            'timestamp': a.created_at.isoformat(),
            'is_suspicious': a.is_suspicious
        } for a in attempts]
    })


@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get active sessions"""
    sessions =  UserSession.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    return jsonify({
        'sessions': [{
            'id': s.id,
            'ip_address': s.ip_address,
            'user_agent': s.user_agent,
            'created_at': s.created_at.isoformat(),
            'last_activity': s.last_activity.isoformat()
        } for s in sessions]
    })


@app.route('/api/sessions/<int:session_id>/revoke', methods=['POST'])
@login_required
def revoke_session(session_id):
    """Revoke specific session"""
    user_session = UserSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not user_session:
        return jsonify({'error': 'Session not found'}), 404
    
    user_session.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Session revoked'})


# ─── IP Address & Geolocation ──────────────────────────────────────

@app.route('/api/trusted-ips', methods=['GET', 'POST'])
@login_required
def manage_trusted_ips():
    """Manage trusted IP addresses"""
    if request.method == 'GET':
        ips = IPAddress.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'ips': [{
                'id': ip.id,
                'ip_address': ip.ip_address,
                'country': ip.country,
                'city': ip.city,
                'first_seen': ip.first_seen.isoformat(),
                'last_seen': ip.last_seen.isoformat()
            } for ip in ips]
        })
    
    if request.method == 'POST':
        data = request.get_json()
        ip_obj = IPAddress(
            ip_address=data.get('ip_address'),
            user_id=current_user.id,
            country=data.get('country'),
            city=data.get('city')
        )
        db.session.add(ip_obj)
        db.session.commit()
        return jsonify({'message': 'IP address added'})


# ─── User Activity & Audit Logs ────────────────────────────────────

@app.route('/api/activity-log', methods=['GET'])
@login_required
def get_activity_log():
    """Get user's activity log"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    activities = UserActivity.query.filter_by(user_id=current_user.id).order_by(
        UserActivity.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'activities': [{
            'id': a.id,
            'activity_type': a.activity_type,
            'action_description': a.action_description,
            'ip_address': a.ip_address,
            'status': a.status,
            'created_at': a.created_at.isoformat()
        } for a in activities.items],
        'total': activities.total,
        'pages': activities.pages
    })


# ─── Admin User Management ──────────────────────────────────────────

def serialize_admin_user(user):
    """Serialize a user for admin API responses."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'phone': user.phone,
        'address': user.address,
        'city': user.city,
        'state': user.state,
        'zipcode': user.zipcode,
        'country': user.country,
        'role': user.role,
        'is_active': bool(user.is_active),
        'is_blocked': not bool(user.is_active),
        'is_verified': bool(user.is_verified),
        'is_current_user': user.id == current_user.id,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
    }


def prevent_self_admin_change(user, action_description):
    """Guard against accidental self-admin modifications."""
    if user and user.id == current_user.id and user.role == 'admin':
        return jsonify({'error': f'You cannot {action_description} your own admin account.'}), 400
    return None


@app.route('/admin/users', methods=['GET'])
@admin_required
def admin_users():
    """Admin user management page"""
    return render_template('admin_users.html')


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users_api():
    """Admin API to list users with search, filter, and pagination."""
    search = (request.args.get('search') or '').strip()
    role = (request.args.get('role') or 'all').lower()
    status = (request.args.get('status') or 'all').lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    per_page = min(per_page, 100)

    query = User.query
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )
    if role and role != 'all':
        query = query.filter(User.role == role)
    if status and status != 'all':
        if status == 'active':
            query = query.filter(User.is_active.is_(True))
        elif status == 'blocked':
            query = query.filter(User.is_active.is_(False))
        elif status == 'verified':
            query = query.filter(User.is_verified.is_(True))
        elif status == 'unverified':
            query = query.filter(User.is_verified.is_(False))

    users_page = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [serialize_admin_user(u) for u in users_page.items],
        'total': users_page.total,
        'page': users_page.page,
        'pages': users_page.pages,
        'per_page': users_page.per_page,
        'has_next': users_page.has_next,
        'has_prev': users_page.has_prev,
    })


@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_user_detail(user_id):
    """Admin API to get specific user detail."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(serialize_admin_user(user))


@app.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
@admin_required
def admin_update_user(user_id):
    """Admin API to update a user record."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': 'No update data provided'}), 400

    if 'role' in data:
        new_role = str(data['role']).strip().lower()
        if new_role not in {'user', 'admin'}:
            return jsonify({'error': 'Role must be either user or admin'}), 400
        if user.id == current_user.id and user.role == 'admin' and new_role != 'admin':
            return jsonify({'error': 'You cannot demote your own admin account.'}), 400
        user.role = new_role

    if 'is_active' in data:
        self_guard = prevent_self_admin_change(user, 'deactivate')
        if self_guard is not None:
            return self_guard
        user.is_active = bool(data['is_active'])

    if 'full_name' in data:
        user.full_name = (data.get('full_name') or '').strip() or user.full_name
    if 'email' in data:
        email = (data.get('email') or '').strip()
        if email and User.query.filter(User.email == email, User.id != user.id).first():
            return jsonify({'error': 'A user with this email already exists'}), 400
        user.email = email
    if 'username' in data:
        username = (data.get('username') or '').strip()
        if username and User.query.filter(User.username == username, User.id != user.id).first():
            return jsonify({'error': 'A user with this username already exists'}), 400
        user.username = username

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_update',
        target_user_id=user.id,
        reason=data.get('reason', 'Admin updated user profile'),
        details={'changes': {k: v for k, v in data.items() if k not in {'password'}}},
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({'message': 'User updated successfully', 'user': serialize_admin_user(user)})


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Admin API to deactivate a user account without deleting the record."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    self_guard = prevent_self_admin_change(user, 'delete or deactivate')
    if self_guard is not None:
        return self_guard

    user.is_active = False
    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_deactivate',
        target_user_id=user.id,
        reason='Admin deactivated user account',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({'message': f'User {user.username} deactivated successfully', 'user': serialize_admin_user(user)})


@app.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
@admin_required
def admin_block_user(user_id):
    """Admin: Block user account."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    self_guard = prevent_self_admin_change(user, 'block')
    if self_guard is not None:
        return self_guard

    data = request.get_json(silent=True) or {}
    user.is_active = False

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_block',
        target_user_id=user_id,
        reason=data.get('reason', 'Admin blocked user account'),
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({'message': f'User {user.username} blocked', 'user': serialize_admin_user(user)})


@app.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def admin_unblock_user(user_id):
    """Admin: Unblock user account."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_active = True

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_unblock',
        target_user_id=user_id,
        reason='Admin unblocked user account',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({'message': f'User {user.username} unblocked', 'user': serialize_admin_user(user)})


@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_user_password(user_id):
    """Admin: Force password reset for user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    temp_password = secrets.token_urlsafe(16)
    user.set_password(temp_password)

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='password_reset',
        target_user_id=user_id,
        reason='Admin requested password reset',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({
        'message': 'Password reset',
        'temporary_password': temp_password,
        'note': 'User should change this immediately'
    })


# ─── Notifications & Alerts ────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get user notifications"""
    notifications = Notification.query.filter_by(user_id=current_user.id, is_sent=True).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'channel': n.channel,
            'subject': n.subject,
            'message': n.message,
            'sent_at': n.sent_at.isoformat() if n.sent_at else None,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    })


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_sent = True
    db.session.commit()
    
    return jsonify({'message': 'Notification marked as read'})


# ─── Suspicious Activity Reporting ─────────────────────────────────

@app.route('/api/suspicious-activities', methods=['GET'])
@login_required
def get_suspicious_activities():
    """Get suspicious activities"""
    if current_user.role != 'admin':
        # Users only see their own
        activities = SuspiciousActivity.query.filter_by(user_id=current_user.id).order_by(
            SuspiciousActivity.created_at.desc()
        ).limit(20).all()
    else:
        # Admin sees all
        activities = SuspiciousActivity.query.order_by(
            SuspiciousActivity.created_at.desc()
        ).limit(100).all()
    
    return jsonify({
        'activities': [{
            'id': a.id,
            'activity_name': a.activity_name,
            'severity': a.severity,
            'description': a.description,
            'risk_score': a.risk_score,
            'country': a.country,
            'is_reviewed': a.is_reviewed,
            'is_threat': a.is_threat,
            'created_at': a.created_at.isoformat()
        } for a in activities]
    })


@app.route('/api/admin/suspicious-activities/<int:activity_id>/review', methods=['POST'])
@admin_required
def review_suspicious_activity(activity_id):
    """Admin: Review suspicious activity"""
    activity = SuspiciousActivity.query.get(activity_id)
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    data = request.get_json() or {}
    activity.is_reviewed = True
    activity.is_threat = data.get('is_threat', False)
    activity.reviewed_by = current_user.id
    activity.review_notes = data.get('notes', '')
    activity.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Activity reviewed'})


# ─── Security Questions (Account Recovery) ────────────────────────

@app.route('/api/security-questions', methods=['GET', 'POST'])
@login_required
def manage_security_questions():
    """Manage security questions"""
    if request.method == 'GET':
        questions = SecurityQuestion.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'questions': [{
                'id': q.id,
                'question': q.question,
                'created_at': q.created_at.isoformat()
            } for q in questions]
        })
    
    if request.method == 'POST':
        data = request.get_json()
        question = SecurityQuestion(
            user_id=current_user.id,
            question=data.get('question')
        )
        question.set_answer(data.get('answer'))
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({'message': 'Security question added', 'id': question.id})


# ─── Data Export & Reports ────────────────────────────────────────

@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate actual PDF or CSV report and save to secure directory"""
    import uuid
    from utils import ReportGenerator

    try:
        data = request.get_json() or {}
        report_type = data.get('report_type', 'transaction_report')
        file_format = (data.get('format') or data.get('file_format') or 'pdf').lower()
        if file_format not in ('csv', 'pdf'):
            file_format = 'pdf'
            
        filters = data.get('filters', {})
        if not isinstance(filters, dict):
            filters = {}

        # Enforce non-admin restriction
        if current_user.role != 'admin':
            filters['user_id'] = current_user.id

        # Query matching transactions
        transactions = query_filtered_transactions_data(filters, current_user)

        # Title formatting
        title_map = {
            'csv_transaction_report': 'CSV Transaction Detail Report',
            'pdf_transaction_report': 'PDF Transaction Detail Report',
            'transaction_report': f"{file_format.upper()} Transaction Detail Report",
            'fraud_analysis_report': 'Fraud Analysis & Vulnerability Report',
            'dashboard_summary_report': 'Dashboard Executive Summary Report',
            'dashboard_summary': 'Dashboard Executive Summary Report'
        }
        report_title = data.get('title') or title_map.get(report_type, f"{report_type.replace('_', ' ').title()}")

        # Generate unique random filename (do NOT expose real internal paths)
        file_ext = 'pdf' if file_format == 'pdf' else 'csv'
        unique_filename = f"report_{current_user.id}_{uuid.uuid4().hex[:12]}.{file_ext}"
        reports_dir = app.config['REPORTS_DIR']
        output_filepath = os.path.abspath(os.path.join(reports_dir, unique_filename))

        # Create physical report file
        if file_format == 'csv':
            ReportGenerator.generate_csv(transactions, output_path=output_filepath)
        else:
            ReportGenerator.generate_pdf(report_type, report_title, transactions, filters=filters, output_path=output_filepath)

        file_size = os.path.getsize(output_filepath) if os.path.exists(output_filepath) else 0

        # Create database record
        report = Report(
            user_id=current_user.id,
            report_type=report_type,
            title=report_title,
            description=f"Generated {file_format.upper()} report with {len(transactions)} transaction records",
            file_path=unique_filename,
            file_format=file_format,
            file_size=file_size,
            filters=filters,
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()

        return jsonify({
            'message': 'Report generated successfully',
            'report_id': report.id,
            'title': report.title,
            'file_format': report.file_format,
            'file_size': report.file_size,
            'status': 'completed'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Failed to generate report: {str(e)}"}), 500


@app.route('/api/reports', methods=['GET'])
@login_required
def list_reports():
    """List generated reports for current user (or all if admin)"""
    if current_user.role == 'admin':
        reports = Report.query.order_by(Report.created_at.desc()).limit(100).all()
    else:
        reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(50).all()

    result = []
    for r in reports:
        result.append({
            'id': r.id,
            'user_id': r.user_id,
            'report_type': r.report_type,
            'title': r.title,
            'file_format': r.file_format,
            'file_size': r.file_size or 0,
            'status': r.status,
            'download_count': r.download_count or 0,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
            'filters': r.filters or {}
        })

    return jsonify({'reports': result})


@app.route('/api/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report_status(report_id):
    """Get report details & status"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    return jsonify({
        'id': report.id,
        'user_id': report.user_id,
        'status': report.status,
        'title': report.title,
        'report_type': report.report_type,
        'file_format': report.file_format,
        'file_size': report.file_size,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'completed_at': report.completed_at.isoformat() if report.completed_at else None,
        'download_count': report.download_count,
        'filters': report.filters or {}
    })


@app.route('/api/reports/<int:report_id>/download', methods=['GET'])
@login_required
def download_report(report_id):
    """Download generated report with strict authorization check & path validation"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report or report.status != 'completed' or not report.file_path:
        return jsonify({'error': 'Report not found or not available for download'}), 404

    # Security: Ensure file stays strictly within REPORTS_DIR
    reports_dir = app.config['REPORTS_DIR']
    file_path = os.path.abspath(os.path.join(reports_dir, report.file_path))

    if not file_path.startswith(reports_dir) or not os.path.exists(file_path):
        return jsonify({'error': 'Report file missing from secure storage'}), 404

    report.download_count = (report.download_count or 0) + 1
    db.session.commit()

    mimetype = 'application/pdf' if report.file_format == 'pdf' else 'text/csv'
    safe_download_name = f"{report.title.replace(' ', '_')}.{report.file_format}"

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=safe_download_name
    )


@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """Safely delete report record and physical file"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if report.file_path:
        reports_dir = app.config['REPORTS_DIR']
        file_path = os.path.abspath(os.path.join(reports_dir, report.file_path))
        if file_path.startswith(reports_dir) and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    db.session.delete(report)
    db.session.commit()
    return jsonify({'message': 'Report deleted successfully'})


# ─── Initialize and Run ─────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("\n🔒 Credit Card Fraud Detection System")
    print("=" * 45)
    print("🌐 Server: http://127.0.0.1:5000")
    print("👤 Login:  admin / admin123")
    print("=" * 45 + "\n")
    app.run(debug=True, port=5000)
