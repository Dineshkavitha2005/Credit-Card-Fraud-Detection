import os
import shutil
import tempfile
import pytest
from cryptography.fernet import Fernet

# Set test environment variables
os.environ['CARD_ENCRYPTION_KEY'] = Fernet.generate_key().decode('utf-8')

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.user import User, UserCard, UserSession
from app.models.rule import FraudRule
from app.models.transaction import Transaction, BlockedCard

@pytest.fixture(scope='session')
def temp_reports_dir():
    """Create a temporary directory for test report files and clean up after session."""
    temp_dir = tempfile.mkdtemp(prefix="fraud_test_reports_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def app(temp_reports_dir):
    """Create and configure a new Flask app instance for each test with isolated in-memory DB."""
    class CustomTestingConfig(TestingConfig):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        WTF_CSRF_ENABLED = False
        SECRET_KEY = 'test-secret-key-for-unit-testing'
        REPORTS_DIR = temp_reports_dir

    test_app = create_app(CustomTestingConfig)
    test_app.config['REPORTS_DIR'] = temp_reports_dir

    with test_app.app_context():
        db.create_all()
        # Seed default fraud rules for testing
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

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a standard verified active user for testing."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(
                username='testuser',
                email='testuser@example.com',
                full_name='Test Normal User',
                role='user',
                is_active=True,
                is_verified=True,
                phone='+1234567890',
                city='New York',
                state='NY',
                country='United States'
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
            user = User.query.filter_by(username='testuser').first()
        return user


@pytest.fixture
def admin_user(app):
    """Create a verified admin user for testing."""
    with app.app_context():
        admin = User.query.filter_by(username='adminuser').first()
        if not admin:
            admin = User(
                username='adminuser',
                email='adminuser@example.com',
                full_name='Test Admin User',
                role='admin',
                is_active=True,
                is_verified=True,
                phone='+1987654321',
                city='San Francisco',
                state='CA',
                country='United States'
            )
            admin.set_password('AdminPass123!')
            db.session.add(admin)
            db.session.commit()
            admin = User.query.filter_by(username='adminuser').first()
        return admin


@pytest.fixture
def blocked_user(app):
    """Create a deactivated/blocked user for testing."""
    with app.app_context():
        user = User.query.filter_by(username='blockeduser').first()
        if not user:
            user = User(
                username='blockeduser',
                email='blockeduser@example.com',
                full_name='Blocked User',
                role='user',
                is_active=False,
                is_verified=True
            )
            user.set_password('BlockedPass123!')
            db.session.add(user)
            db.session.commit()
            user = User.query.filter_by(username='blockeduser').first()
        return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Test client logged in as test_user."""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'TestPass123!'
    }, follow_redirects=True)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Test client logged in as admin_user."""
    client.post('/login', data={
        'username': 'adminuser',
        'password': 'AdminPass123!'
    }, follow_redirects=True)
    return client


@pytest.fixture
def sample_genuine_transaction():
    """Synthetic genuine transaction payload."""
    return {
        'amount': 45.50,
        'card_number': '4532759283741092',
        'merchant': 'Grocery Store',
        'category': 'Groceries',
        'location': 'New York, US',
        'device_type': 'Mobile'
    }


@pytest.fixture
def sample_fraud_transaction():
    """Synthetic high-risk fraud transaction payload."""
    return {
        'amount': 25000.00,
        'card_number': '4532759283749999',
        'merchant': 'Luxury Electronics Online',
        'category': 'Cryptocurrency',
        'location': 'Lagos, Nigeria',
        'device_type': 'Unknown',
        'velocity_score': 1.0
    }
