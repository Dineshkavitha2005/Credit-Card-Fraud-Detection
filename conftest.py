import os
from cryptography.fernet import Fernet

# Set deterministic test environment variables prior to any test execution
os.environ['TESTING'] = '1'
os.environ.setdefault('TEST_SECRET_KEY', 'deterministic-sentinel-test-secret-key-for-test-suite')
os.environ.setdefault('SECRET_KEY', 'deterministic-sentinel-test-secret-key-for-test-suite')
os.environ.setdefault('CARD_ENCRYPTION_KEY', Fernet.generate_key().decode('utf-8'))
