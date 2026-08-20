import os
import secrets

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

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
