import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import os
import sqlite3
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.extensions import db, login_manager, cors, audit_logger, EventType
from errors import (
    APIError, format_error_response, is_json_request
)

class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider handling NumPy serialization."""
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


def handle_error_response(message, status_code=500, code="INTERNAL_SERVER_ERROR", details=None, title=None):
    """Return JSON for API requests or HTML page for web requests."""
    if is_json_request():
        resp_data = format_error_response(message, status_code=status_code, code=code, details=details)
        return jsonify(resp_data), status_code
    else:
        title_val = title or code.replace("_", " ").title()
        return render_template(
            "error.html",
            status_code=status_code,
            title=title_val,
            message=message
        ), status_code


def create_app(config_class=Config):
    """Application factory for Credit Card Fraud Detection System."""
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_folder = os.path.join(root_path, 'templates')
    static_folder = os.path.join(root_path, 'static')

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder
    )
    app.config.from_object(config_class)

    # Configure custom JSON provider
    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)

    # Setup reports storage directory
    reports_dir = os.path.abspath(os.path.join(app.instance_path, 'reports'))
    os.makedirs(reports_dir, exist_ok=True)
    app.config['REPORTS_DIR'] = reports_dir

    # Initialize extensions
    db.init_app(app)
    cors.init_app(app)
    audit_logger.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # User loader & unauthorized handler for login_manager
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        audit_logger.log_event(
            EventType.API_AUTH_FAILURE,
            user_id=None,
            status='failure',
            target_resource=request.path,
            details={'reason': 'Unauthenticated request to protected resource'}
        )
        if is_json_request():
            return jsonify(format_error_response('Authentication required', status_code=401, code='UNAUTHORIZED')), 401
        return redirect(url_for('auth.login', next=request.url))

    # Error handlers
    @app.errorhandler(APIError)
    def handle_api_error(e):
        app.logger.warning(f"APIError [{e.code}]: {e.message}")
        return handle_error_response(e.message, status_code=e.status_code, code=e.code, details=e.details)

    @app.errorhandler(400)
    def handle_bad_request(e):
        msg = getattr(e, 'description', 'Bad Request')
        return handle_error_response(msg, status_code=400, code="BAD_REQUEST")

    @app.errorhandler(401)
    def handle_unauthorized(e):
        msg = getattr(e, 'description', 'Authentication required')
        return handle_error_response(msg, status_code=401, code="UNAUTHORIZED")

    @app.errorhandler(403)
    def handle_forbidden(e):
        msg = getattr(e, 'description', 'Access forbidden')
        return handle_error_response(msg, status_code=403, code="FORBIDDEN")

    @app.errorhandler(404)
    def handle_not_found(e):
        msg = getattr(e, 'description', 'The requested resource or page was not found')
        return handle_error_response(msg, status_code=404, code="NOT_FOUND")

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        msg = getattr(e, 'description', 'HTTP method not allowed for this endpoint')
        return handle_error_response(msg, status_code=405, code="METHOD_NOT_ALLOWED")

    @app.errorhandler(409)
    def handle_conflict(e):
        msg = getattr(e, 'description', 'Resource conflict')
        return handle_error_response(msg, status_code=409, code="CONFLICT")

    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(e):
        return handle_error_response("Request payload exceeds maximum allowed size of 16MB", status_code=413, code="PAYLOAD_TOO_LARGE")

    @app.errorhandler(422)
    def handle_unprocessable_entity(e):
        msg = getattr(e, 'description', 'Unprocessable request parameters')
        return handle_error_response(msg, status_code=422, code="UNPROCESSABLE_ENTITY")

    @app.errorhandler(429)
    def handle_too_many_requests(e):
        msg = getattr(e, 'description', 'Too many requests. Please try again later.')
        return handle_error_response(msg, status_code=429, code="RATE_LIMIT_EXCEEDED")

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(e):
        db.session.rollback()
        app.logger.error(f"Database Exception: {str(e)}", exc_info=True)
        return handle_error_response("A database error occurred. Operation was rolled back.", status_code=500, code="DATABASE_ERROR")

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        app.logger.info(f"HTTPException [{e.code}]: {e.description}")
        return handle_error_response(e.description or str(e), status_code=e.code or 500, code=getattr(e, 'name', 'HTTP_ERROR').upper().replace(" ", "_"))

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        db.session.rollback()
        app.logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
        return handle_error_response("An internal server error occurred. Please try again later.", status_code=500, code="INTERNAL_SERVER_ERROR")

    @app.teardown_request
    def teardown_request(exception=None):
        if exception is not None:
            try:
                db.session.rollback()
            except Exception:
                pass

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.transactions import transactions_bp
    from app.routes.cards import cards_bp
    from app.routes.admin import admin_bp
    from app.routes.analytics import analytics_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)

    def handle_url_build_error(error, endpoint, values):
        if '.' not in endpoint:
            for bp_name in ['main', 'auth', 'transactions', 'cards', 'admin', 'analytics', 'reports']:
                try:
                    return url_for(f"{bp_name}.{endpoint}", **values)
                except Exception:
                    pass
        raise error

    app.url_build_error_handlers.append(handle_url_build_error)

    return app


# Create default singleton app instance
app = create_app()

def get_db():
    """Get SQLite connection for operations"""
    try:
        return db.engine.raw_connection()
    except Exception:
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///fraud_detection.db').replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def migrate_database_security():
    """Migrate existing plain text card numbers in DB to masked/encrypted representations"""
    from app.models.user import UserCard
    from app.models.encryption import CardEncryption, mask_card_number
    try:
        txns = db.session.execute(db.text("SELECT id, card_number FROM transactions")).fetchall()
        for t in txns:
            t_id, raw_card = t[0], str(t[1] or '')
            if raw_card and not raw_card.startswith('****') and not raw_card.startswith('••••'):
                masked = mask_card_number(raw_card)
                db.session.execute(db.text("UPDATE transactions SET card_number = :masked WHERE id = :id"), {'masked': masked, 'id': t_id})
        
        b_cards = db.session.execute(db.text("SELECT id, card_number FROM blocked_cards")).fetchall()
        for b in b_cards:
            b_id, raw_card = b[0], str(b[1] or '')
            if raw_card and not raw_card.startswith('gAAAAA'):
                enc = CardEncryption.encrypt_card_number(raw_card)
                db.session.execute(db.text("UPDATE blocked_cards SET card_number = :enc WHERE id = :id"), {'enc': enc, 'id': b_id})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
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


def migrate_audit_logs_table():
    """Ensure audit_logs table has all required columns in SQLite database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(audit_logs);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'event_type' not in columns:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN event_type VARCHAR(50);")
        if 'target_resource' not in columns:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN target_resource VARCHAR(255);")
        if 'user_agent' not in columns:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN user_agent VARCHAR(500);")
            
        conn.commit()
    except Exception as e:
        print(f"Audit log schema migration note: {e}")


def migrate_user_identities_table():
    """Ensure users table has OAuth columns and user_identities table exists in SQLite database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'google_id' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255);")
        if 'auth_provider' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local';")
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider VARCHAR(50) NOT NULL,
                provider_subject VARCHAR(255) NOT NULL,
                provider_email VARCHAR(120),
                created_at DATETIME,
                last_used_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT uq_user_identity_provider_subject UNIQUE (provider, provider_subject)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_identities_user_id ON user_identities (user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_identities_provider ON user_identities (provider);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_identities_provider_subject ON user_identities (provider_subject);")
        conn.commit()
    except Exception as e:
        print(f"User identity schema migration note: {e}")


def init_db():
    """Initialize database with all tables and perform security migrations"""
    from app.models.user import User
    from app.models.rule import FraudRule
    with app.app_context():
        db.create_all()
        migrate_database_security()
        migrate_audit_logs_table()
        migrate_user_identities_table()
        
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


# Backward-compatible re-exports
from app.services.fraud_detection import fraud_engine, sanitize_numpy_types
from app.models import (
    User, UserIdentity, UserCard, Transaction, Alert, FraudRule, BlockedCard, AuditLog,
    UserSession, LoginAttempt, IPAddress, UserActivity, EmailVerificationToken,
    PasswordResetToken, Notification, SecurityQuestion, RateLimitRecord, Report,
    SuspiciousActivity, AdminAction, CardEncryption, mask_card_number
)

reports_dir = app.config['REPORTS_DIR']
