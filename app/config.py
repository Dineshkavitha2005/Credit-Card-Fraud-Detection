import os
import secrets
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=True)
    except Exception:
        # Zero-dependency manual .env reader fallback
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', '').strip()
    if not SECRET_KEY or SECRET_KEY in {
        'your_secret_key_here',
        'change_this_secret_key_in_production',
        'fraud-detection-secret-key-2026',
        'secret',
        'default-unsafe-key'
    }:
        if os.getenv('FLASK_ENV') == 'production' and not os.getenv('TESTING'):
            raise ValueError("Insecure or default SECRET_KEY configured in environment.")
        SECRET_KEY = secrets.token_hex(32)
        
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///fraud_detection.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max payload limit

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = (os.getenv('FLASK_ENV') == 'production')

    # Google OAuth 2.0 / OpenID Connect Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', '').strip()
    GOOGLE_ALLOWED_DOMAIN = os.getenv('GOOGLE_ALLOWED_DOMAIN', '').strip()

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
