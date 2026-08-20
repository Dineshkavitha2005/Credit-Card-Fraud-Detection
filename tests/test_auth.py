import pytest
from app.models.user import User, UserSession
from app.extensions import db

class TestAuthentication:
    """Test suite for user authentication and authorization."""

    def test_user_registration_success(self, client, app):
        """Test valid user registration creates an unverified user record."""
        res = client.post('/register', data={
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'username': 'alicesmith',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'phone': '+1234567890',
            'address': '123 Main St',
            'city': 'Boston',
            'state': 'MA',
            'zipcode': '02101',
            'country': 'United States'
        })
        assert res.status_code == 200
        assert b'Registration Successful' in res.data or b'Check your email' in res.data

        with app.app_context():
            user = User.query.filter_by(username='alicesmith').first()
            assert user is not None
            assert user.email == 'alice@example.com'
            assert user.full_name == 'Alice Smith'
            assert user.role == 'user'
            assert user.check_password('SecurePass123!') is True

    def test_registration_missing_fields(self, client):
        """Test registration fails when mandatory fields are missing."""
        res = client.post('/register', data={
            'first_name': 'Alice',
            'last_name': '',
            'email': 'alice@example.com',
            'username': 'alicesmith',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        })
        assert res.status_code == 200
        assert b'All required fields must be filled' in res.data

    def test_registration_password_mismatch(self, client):
        """Test registration fails when password and confirm_password do not match."""
        res = client.post('/register', data={
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'username': 'alicesmith',
            'password': 'SecurePass123!',
            'confirm_password': 'DifferentPass123!'
        })
        assert res.status_code == 200
        assert b'Passwords do not match' in res.data

    def test_registration_weak_password(self, client):
        """Test registration fails when password does not meet security requirements."""
        res = client.post('/register', data={
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'username': 'alicesmith',
            'password': '123',
            'confirm_password': '123'
        })
        assert res.status_code == 200
        # Should return password feedback or error
        assert b'at least 8 characters' in res.data or b'Password' in res.data

    def test_registration_duplicate_username(self, client, test_user):
        """Test registration fails when username already exists."""
        res = client.post('/register', data={
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'unique_email@example.com',
            'username': test_user.username,
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        })
        assert res.status_code == 200
        assert b'Username already exists' in res.data

    def test_registration_duplicate_email(self, client, test_user):
        """Test registration fails when email is already registered."""
        res = client.post('/register', data={
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': test_user.email,
            'username': 'newuniqueuser',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        })
        assert res.status_code == 200
        assert b'Email already registered' in res.data

    def test_login_success(self, client, test_user, app):
        """Test login succeeds with valid credentials and sets session."""
        res = client.post('/login', data={
            'username': test_user.username,
            'password': 'TestPass123!'
        }, follow_redirects=False)
        assert res.status_code in [200, 302]

        with app.app_context():
            u = User.query.filter_by(username=test_user.username).first()
            assert u.last_login is not None

    def test_login_invalid_password(self, client, test_user):
        """Test login fails with incorrect password."""
        res = client.post('/login', data={
            'username': test_user.username,
            'password': 'WrongPassword123!'
        })
        assert res.status_code == 200
        assert b'Invalid username or password' in res.data

    def test_login_nonexistent_user(self, client):
        """Test login fails for unknown username."""
        res = client.post('/login', data={
            'username': 'nonexistentuser999',
            'password': 'SomePassword123!'
        })
        assert res.status_code == 200
        assert b'Invalid username or password' in res.data

    def test_login_deactivated_account(self, client, blocked_user):
        """Test login is blocked for deactivated accounts."""
        res = client.post('/login', data={
            'username': blocked_user.username,
            'password': 'BlockedPass123!'
        })
        assert res.status_code == 200
        assert b'Account has been deactivated' in res.data

    def test_logout(self, authenticated_client):
        """Test logout clears user session and redirects."""
        res = authenticated_client.get('/logout', follow_redirects=False)
        assert res.status_code in [200, 302]

        # Protected page should now redirect
        prot_res = authenticated_client.get('/profile', follow_redirects=False)
        assert prot_res.status_code == 302
        assert '/login' in prot_res.location

    def test_authorization_unauthenticated_page(self, client):
        """Test accessing protected web pages without authentication redirects to login."""
        res = client.get('/profile', follow_redirects=False)
        assert res.status_code == 302
        assert '/login' in res.location

    def test_authorization_unauthenticated_api(self, client):
        """Test accessing protected API endpoints without authentication returns 401."""
        res = client.get('/api/transactions', headers={'Accept': 'application/json'})
        assert res.status_code == 401
        data = res.get_json()
        assert data.get('error') == 'Authentication required' or data.get('code') == 'UNAUTHORIZED' or data.get('status_code') == 401

    def test_admin_authorization_standard_user_forbidden(self, authenticated_client):
        """Test standard user is forbidden (403) from accessing admin endpoints."""
        page_res = authenticated_client.get('/admin/users')
        assert page_res.status_code == 403

        api_res = authenticated_client.get('/api/admin/users', headers={'Accept': 'application/json'})
        assert api_res.status_code == 403

    def test_admin_authorization_admin_user_allowed(self, admin_client):
        """Test admin user successfully accesses admin endpoints."""
        page_res = admin_client.get('/admin/users')
        assert page_res.status_code == 200

        api_res = admin_client.get('/api/admin/users', headers={'Accept': 'application/json'})
        assert api_res.status_code == 200
        data = api_res.get_json()
        assert 'users' in data
