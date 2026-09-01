import os
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

UNSAFE_SECRET_KEYS = {
    'your_secret_key_here',
    'change_this_secret_key_in_production',
    'change_this_to_a_secure_random_64_character_hex_string',
    'fraud-detection-secret-key-2026',
    'secret',
    'secret_key',
    'default-unsafe-key',
    'password',
    '12345',
    '123456',
    'test',
    'admin'
}


def is_unsafe_secret(key: str) -> bool:
    """Check if a secret key is empty, unsafe, a default placeholder, or too short (< 16 chars)."""
    if not key or not isinstance(key, str):
        return True
    cleaned = key.strip()
    return (
        not cleaned
        or cleaned.lower() in {s.lower() for s in UNSAFE_SECRET_KEYS}
        or len(cleaned) < 16
    )


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', '').strip()
        
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///fraud_detection.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
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

    @classmethod
    def validate(cls):
        """Validate configuration settings. Reject missing, default, or unsafe secrets."""
        if 'SECRET_KEY' in cls.__dict__ and cls.__dict__['SECRET_KEY'] is not None:
            secret = cls.SECRET_KEY
        else:
            secret = os.getenv('SECRET_KEY', '').strip() or cls.SECRET_KEY
        if is_unsafe_secret(secret):
            raise ValueError("Insecure, default, or missing SECRET_KEY configured in environment.")


class DevelopmentConfig(Config):
    """Development configuration: SQLite is acceptable for local development."""
    DEBUG = True
    SECRET_KEY = os.getenv('DEV_SECRET_KEY', '').strip() or os.getenv('SECRET_KEY', '').strip()
    SQLALCHEMY_DATABASE_URI = (
        os.getenv('DEV_DATABASE_URL', '').strip()
        or os.getenv('DATABASE_URL', '').strip()
        or 'sqlite:///fraud_detection.db'
    )

    @classmethod
    def validate(cls):
        if 'SECRET_KEY' in cls.__dict__ and cls.__dict__['SECRET_KEY'] is not None:
            secret = cls.SECRET_KEY
        else:
            secret = os.getenv('DEV_SECRET_KEY', '').strip() or os.getenv('SECRET_KEY', '').strip() or cls.SECRET_KEY
        if is_unsafe_secret(secret):
            raise ValueError(
                "Development configuration requires an explicit SECRET_KEY or DEV_SECRET_KEY "
                "configured in your environment or .env file."
            )


class ProductionConfig(Config):
    """Production configuration strictly requiring PostgreSQL and rejecting missing/SQLite databases."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SECRET_KEY = os.getenv('SECRET_KEY', '').strip()
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', '').strip()

    # Enterprise PostgreSQL Connection Pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '1800')),
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
    }

    @classmethod
    def validate(cls):
        if 'SECRET_KEY' in cls.__dict__ and cls.__dict__['SECRET_KEY'] is not None:
            secret = cls.SECRET_KEY
        else:
            secret = os.getenv('SECRET_KEY', '').strip() or cls.SECRET_KEY
        if is_unsafe_secret(secret):
            raise ValueError(
                "Production configuration requires a strong, explicit SECRET_KEY configured in environment."
            )

        if 'SQLALCHEMY_DATABASE_URI' in cls.__dict__ and cls.__dict__['SQLALCHEMY_DATABASE_URI'] is not None:
            db_uri = cls.SQLALCHEMY_DATABASE_URI
        else:
            db_uri = os.getenv('DATABASE_URL', '').strip() or cls.SQLALCHEMY_DATABASE_URI

        if not db_uri:
            raise ValueError(
                "Production configuration requires a PostgreSQL database. "
                "DATABASE_URL is missing or not configured in the environment."
            )

        db_uri_lower = db_uri.lower()
        if db_uri_lower.startswith('sqlite:') or 'sqlite' in db_uri_lower:
            raise ValueError(
                "Production configuration refuses to start with SQLite. "
                "PostgreSQL is strictly required in production."
            )

        if not (
            db_uri_lower.startswith('postgresql://')
            or db_uri_lower.startswith('postgres://')
            or db_uri_lower.startswith('postgresql+')
        ):
            raise ValueError(
                "Production configuration requires a PostgreSQL database URI (postgresql://...)."
            )


class TestingConfig(Config):
    """Testing configuration: SQLite in-memory or dedicated test database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', '').strip() or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = os.getenv('TEST_SECRET_KEY', '').strip() or os.getenv('SECRET_KEY', '').strip()

    @classmethod
    def validate(cls):
        if 'SECRET_KEY' in cls.__dict__ and cls.__dict__['SECRET_KEY'] is not None:
            secret = cls.SECRET_KEY
        else:
            secret = os.getenv('TEST_SECRET_KEY', '').strip() or os.getenv('SECRET_KEY', '').strip() or cls.SECRET_KEY
        if is_unsafe_secret(secret):
            raise ValueError(
                "Testing configuration requires an explicit TEST_SECRET_KEY or SECRET_KEY "
                "supplied by the test environment."
            )




