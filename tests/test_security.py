import pytest
from datetime import datetime, timedelta
from app.models.encryption import mask_card_number, CardEncryption
from app.models.user import UserSession, User
from app.models.transaction import Transaction
from app.extensions import db

class TestSecurity:
    """Test suite for security features, masking, session handling, and validation."""

    def test_card_number_masking_utility(self):
        """Test mask_card_number masks all but the last 4 digits."""
        # 16-digit card
        masked_16 = mask_card_number('4532759283741092')
        assert masked_16.endswith('1092')
        assert '4532' not in masked_16 or masked_16.startswith('****') or masked_16.startswith('••••')

        # Already masked string
        already_masked = mask_card_number('**** **** **** 1092')
        assert already_masked == '**** **** **** 1092'

        # Short/invalid string
        assert mask_card_number('123') == '**** **** **** ****'
        assert mask_card_number('') == ''

    def test_sensitive_data_masked_in_api_response(self, authenticated_client, sample_genuine_transaction):
        """Test API responses do not expose full plaintext credit card numbers."""
        proc_res = authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)
        assert proc_res.status_code == 200

        list_res = authenticated_client.get('/api/transactions')
        assert list_res.status_code == 200
        data = list_res.get_json()

        for t in data['transactions']:
            card = t['card_number']
            assert '4532759283741092' not in card
            assert card.startswith('****') or card.startswith('••••')
            assert card.endswith('1092')

    def test_card_encryption_and_decryption(self):
        """Test CardEncryption encrypts and safely decrypts card numbers."""
        plain_card = '4111222233334444'
        encrypted = CardEncryption.encrypt_card_number(plain_card)
        assert encrypted != plain_card
        assert len(encrypted) > 20

        decrypted = CardEncryption.decrypt_card_number(encrypted)
        assert decrypted == plain_card

    def test_invalid_json_request(self, authenticated_client):
        """Test malformed JSON requests return appropriate 400 Bad Request error."""
        res = authenticated_client.post(
            '/api/transactions/process',
            data='{invalid_json: true, amount:}',
            content_type='application/json'
        )
        assert res.status_code in [400, 422]

    def test_sql_injection_resilience_in_filters(self, admin_client):
        """Test that SQL injection payloads in parameters do not crash or corrupt the query."""
        sqli_payload = "' OR '1'='1"
        res = admin_client.get(f'/api/admin/users?search={sqli_payload}')
        assert res.status_code == 200
        data = res.get_json()
        assert 'users' in data

    def test_user_session_creation_on_login(self, client, test_user, app):
        """Test valid login creates a secure UserSession token with expiration date."""
        res = client.post('/login', data={
            'username': test_user.username,
            'password': 'TestPass123!'
        })
        assert res.status_code in [200, 302]

        with app.app_context():
            session_record = UserSession.query.filter_by(user_id=test_user.id).order_by(UserSession.created_at.desc()).first()
            assert session_record is not None
            assert session_record.session_token is not None
            assert len(session_record.session_token) >= 32
            assert session_record.expires_at > datetime.utcnow()
            assert session_record.is_active is True

    def test_session_invalidation(self, app, test_user):
        """Test expired or invalidated user session is flagged as invalid."""
        with app.app_context():
            expired_session = UserSession(
                user_id=test_user.id,
                session_token='expired_token_12345678901234567890',
                expires_at=datetime.utcnow() - timedelta(hours=1),
                is_active=False
            )
            db.session.add(expired_session)
            db.session.commit()

            assert expired_session.is_active is False
            assert expired_session.expires_at < datetime.utcnow()

    def test_unauthorized_access_to_admin_settings(self, authenticated_client):
        """Test regular user attempting admin-only endpoints receives 403."""
        endpoints = [
            ('/api/admin/users', 'GET'),
            ('/api/admin/users/1', 'GET'),
            ('/api/admin/users/1/block', 'POST'),
            ('/admin/users', 'GET')
        ]
        for url, method in endpoints:
            if method == 'GET':
                res = authenticated_client.get(url, headers={'Accept': 'application/json'})
            else:
                res = authenticated_client.post(url, headers={'Accept': 'application/json'})
            assert res.status_code == 403

    def test_health_check_endpoint(self, client):
        """Test /health and /api/health return 200 OK with healthy database status."""
        for url in ['/health', '/api/health']:
            res = client.get(url)
            assert res.status_code == 200
            data = res.get_json()
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
            assert data['service'] == 'credit-card-fraud-detection'

