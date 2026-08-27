"""
Integration and Unit Test Suite for Google OAuth 2.0 / OpenID Connect Authentication
Mocks external Google endpoints to thoroughly validate PKCE, State CSRF protection,
account provisioning, safe linking, domain enforcement, and RBAC isolation.
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from flask import session
from app.extensions import db, audit_logger, EventType
from app.models.user import User, UserIdentity, UserSession
from app.models.audit import AuditLog


MOCK_GOOGLE_SUB = "google_sub_109283746501928374"
MOCK_GOOGLE_EMAIL = "google_test_user@example.com"
MOCK_GOOGLE_NAME = "Google Test User"
MOCK_GOOGLE_PICTURE = "https://lh3.googleusercontent.com/a/default-user-pic"


def mock_google_token_and_userinfo(sub=MOCK_GOOGLE_SUB, email=MOCK_GOOGLE_EMAIL, name=MOCK_GOOGLE_NAME, email_verified=True, hd=""):
    """Helper to mock Google OAuth token and UserInfo endpoints"""
    tokens = {
        'access_token': 'mock_google_access_token_xyz123',
        'id_token': 'mock_google_id_token_abc456',
        'token_type': 'Bearer',
        'expires_in': 3600
    }
    userinfo = {
        'sub': sub,
        'email': email,
        'email_verified': email_verified,
        'name': name,
        'given_name': name.split()[0] if name else '',
        'family_name': name.split()[-1] if name else '',
        'picture': MOCK_GOOGLE_PICTURE,
        'hd': hd
    }
    return tokens, userinfo


class TestGoogleOAuthAuthentication:
    """Test suite covering Google OAuth 2.0 authentication in Sentinel"""

    def test_google_login_redirect_generates_state_and_pkce(self, client, app):
        """Verify /auth/google generates state, code_verifier in session and redirects to Google"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-google-client-id.apps.googleusercontent.com'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-google-client-secret-12345'
        app.config['GOOGLE_REDIRECT_URI'] = 'http://localhost:5000/auth/google/callback'

        res = client.get('/auth/google?next=/transactions', follow_redirects=False)

        assert res.status_code == 302
        redirect_url = res.headers['Location']
        assert 'accounts.google.com/o/oauth2/v2/auth' in redirect_url
        assert 'client_id=mock-google-client-id.apps.googleusercontent.com' in redirect_url
        assert 'response_type=code' in redirect_url
        assert 'code_challenge=' in redirect_url
        assert 'code_challenge_method=S256' in redirect_url
        assert 'state=' in redirect_url

        with client.session_transaction() as sess:
            assert 'oauth_state' in sess
            assert 'oauth_code_verifier' in sess
            assert sess['oauth_next'] == '/transactions'

    def test_google_login_not_configured_graceful_redirect(self, client, app):
        """Verify unconfigured Google OAuth gracefully redirects to login with flash"""
        app.config['GOOGLE_CLIENT_ID'] = ''
        app.config['GOOGLE_CLIENT_SECRET'] = ''

        res = client.get('/auth/google', follow_redirects=True)
        assert res.status_code == 200
        assert b"Google sign-in is not configured" in res.data or b"Authenticate" in res.data

    def test_google_oauth_callback_new_user_creation(self, client, app):
        """Verify a new Google user is provisioned with default role 'user' and logged in"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        # Initiate login to set session state and PKCE
        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="new_google_sub_9999",
            email="new_google_user@sentinel.io",
            name="New Sentinel Analyst"
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            res = client.get(f'/auth/google/callback?code=mock_valid_auth_code&state={state}', follow_redirects=True)
            assert res.status_code == 200

            with app.app_context():
                user = User.query.filter_by(email="new_google_user@sentinel.io").first()
                assert user is not None
                assert user.role == 'user'  # Must be regular user, not admin
                assert user.is_active is True
                assert user.is_verified is True
                assert user.google_id == "new_google_sub_9999"
                assert user.auth_provider == 'google'
                assert user.password_hash is None

                # Check UserIdentity record
                ident = UserIdentity.query.filter_by(provider='google', provider_subject="new_google_sub_9999").first()
                assert ident is not None
                assert ident.user_id == user.id

    def test_google_oauth_callback_existing_linked_user(self, client, app, test_user):
        """Verify returning Google user with linked identity is authenticated"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        with app.app_context():
            user = User.query.get(test_user.id)
            user.google_id = "linked_sub_12345"
            ident = UserIdentity(
                user_id=user.id,
                provider='google',
                provider_subject="linked_sub_12345",
                provider_email=user.email
            )
            db.session.add(ident)
            db.session.commit()

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="linked_sub_12345",
            email=test_user.email,
            name=test_user.full_name
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            res = client.get(f'/auth/google/callback?code=valid_code&state={state}', follow_redirects=False)
            assert res.status_code == 302
            assert res.headers['Location'].endswith('/dashboard') or '/dashboard' in res.headers['Location']

            # Verify session is authenticated
            profile_res = client.get('/profile')
            assert profile_res.status_code == 200
            assert test_user.username.encode('utf-8') in profile_res.data

    def test_google_oauth_callback_existing_email_linking(self, client, app, test_user):
        """Verify existing password user with matching verified email is linked without creating duplicate accounts"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        # Ensure test_user has no google_id initially
        with app.app_context():
            user = User.query.get(test_user.id)
            user.google_id = None
            db.session.commit()

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="newly_linked_sub_7777",
            email=test_user.email,
            name="Test Normal User",
            email_verified=True
        )

        initial_user_count = User.query.count()

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            res = client.get(f'/auth/google/callback?code=valid_code&state={state}', follow_redirects=False)
            assert res.status_code == 302

            with app.app_context():
                # User count must not increase (no duplicate accounts!)
                assert User.query.count() == initial_user_count
                linked_user = User.query.get(test_user.id)
                assert linked_user.google_id == "newly_linked_sub_7777"
                assert linked_user.auth_provider == 'multiple'  # Has password + Google
                assert linked_user.has_password is True
                assert linked_user.has_google_linked is True

    def test_google_oauth_callback_domain_restriction(self, client, app):
        """Verify GOOGLE_ALLOWED_DOMAIN restricts unauthorized Google Workspace domains"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'
        app.config['GOOGLE_ALLOWED_DOMAIN'] = 'sentinel-enterprise.com'

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="unauthorized_sub_001",
            email="hacker@unauthorized-domain.com",
            hd="unauthorized-domain.com"
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            res = client.get(f'/auth/google/callback?code=valid_code&state={state}', follow_redirects=True)
            assert res.status_code == 200
            assert b"domain is not authorized" in res.data or b"Access restricted" in res.data

            with app.app_context():
                assert User.query.filter_by(email="hacker@unauthorized-domain.com").first() is None

    def test_google_oauth_callback_state_mismatch_rejected(self, client, app):
        """Verify CSRF attack with mismatched OAuth state parameter is rejected"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        client.get('/auth/google')

        res = client.get('/auth/google/callback?code=mock_code&state=forged_state_value_xyz', follow_redirects=True)
        assert res.status_code == 200
        assert b"Unable to sign in with Google" in res.data

    def test_google_oauth_callback_missing_state_rejected(self, client, app):
        """Verify missing OAuth state parameter is rejected"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        res = client.get('/auth/google/callback?code=mock_code', follow_redirects=True)
        assert res.status_code == 200
        assert b"Unable to sign in with Google" in res.data

    def test_google_oauth_callback_missing_code_rejected(self, client, app):
        """Verify missing authorization code is rejected"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        res = client.get(f'/auth/google/callback?state={state}', follow_redirects=True)
        assert res.status_code == 200
        assert b"Unable to sign in with Google" in res.data

    def test_google_oauth_callback_user_cancelled(self, client, app):
        """Verify user cancellation (error=access_denied) displays friendly warning"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        res = client.get(f'/auth/google/callback?error=access_denied&state={state}', follow_redirects=True)
        assert res.status_code == 200
        assert b"Google sign-in cancelled" in res.data

    def test_google_oauth_callback_blocked_user_rejected(self, client, app, blocked_user):
        """Verify deactivated/blocked user cannot log in via Google"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        with app.app_context():
            user = User.query.get(blocked_user.id)
            user.google_id = "blocked_google_sub_888"
            ident = UserIdentity(
                user_id=user.id,
                provider='google',
                provider_subject="blocked_google_sub_888",
                provider_email=user.email
            )
            db.session.add(ident)
            db.session.commit()

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="blocked_google_sub_888",
            email=blocked_user.email
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            res = client.get(f'/auth/google/callback?code=mock_code&state={state}', follow_redirects=True)
            assert res.status_code == 200
            assert b"account is currently disabled" in res.data

            # Verify user session is not authenticated
            dash_res = client.get('/dashboard')
            assert dash_res.status_code in (302, 401)

    def test_google_oauth_disconnect_with_password(self, client, app, test_user):
        """Verify user who has a password can safely disconnect their Google account"""
        with app.app_context():
            user = User.query.get(test_user.id)
            user.google_id = "sub_to_disconnect"
            ident = UserIdentity(
                user_id=user.id,
                provider='google',
                provider_subject="sub_to_disconnect",
                provider_email=user.email
            )
            db.session.add(ident)
            db.session.commit()

        # Login with password
        client.post('/login', data={'username': test_user.username, 'password': 'TestPass123!'}, follow_redirects=True)

        res = client.post('/auth/google/disconnect', follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            updated_user = User.query.get(test_user.id)
            assert updated_user.google_id is None
            assert updated_user.has_google_linked is False
            assert UserIdentity.query.filter_by(user_id=test_user.id, provider='google').first() is None

    def test_google_oauth_disconnect_prevented_without_password(self, client, app):
        """Verify user without a password cannot disconnect Google (prevents account lockout)"""
        with app.app_context():
            oauth_user = User(
                username='oauth_only_user',
                email='oauth_only@sentinel.io',
                full_name='OAuth Only User',
                role='user',
                is_active=True,
                is_verified=True,
                password_hash=None,
                google_id="oauth_only_sub_123"
            )
            db.session.add(oauth_user)
            db.session.flush()
            ident = UserIdentity(
                user_id=oauth_user.id,
                provider='google',
                provider_subject="oauth_only_sub_123",
                provider_email=oauth_user.email
            )
            db.session.add(ident)
            db.session.commit()
            uid = oauth_user.id

        # Authenticate session directly
        with client.session_transaction() as sess:
            sess['_user_id'] = str(uid)
            sess['_fresh'] = True

        res = client.post('/auth/google/disconnect', follow_redirects=True)
        assert res.status_code == 200
        assert b"set a password first" in res.data

        with app.app_context():
            user = User.query.get(uid)
            assert user.google_id == "oauth_only_sub_123"
            assert user.has_google_linked is True

    def test_set_initial_password_for_oauth_user(self, client, app):
        """Verify an OAuth user can configure their initial password"""
        with app.app_context():
            oauth_user = User(
                username='oauth_user_pass_setup',
                email='pass_setup@sentinel.io',
                full_name='Password Setup User',
                role='user',
                is_active=True,
                is_verified=True,
                password_hash=None,
                google_id="sub_pass_setup"
            )
            db.session.add(oauth_user)
            db.session.commit()
            uid = oauth_user.id

        with client.session_transaction() as sess:
            sess['_user_id'] = str(uid)
            sess['_fresh'] = True

        # Set initial password
        res = client.post('/api/set-password', json={
            'new_password': 'BrandNewPass123!',
            'confirm_password': 'BrandNewPass123!'
        })
        assert res.status_code == 200

        with app.app_context():
            user = User.query.get(uid)
            assert user.has_password is True
            assert user.check_password('BrandNewPass123!') is True
            assert user.auth_provider == 'multiple'

    def test_google_oauth_new_user_cannot_access_admin_routes(self, client, app):
        """Verify newly created Google user receives 'user' role and cannot access admin routes (RBAC check)"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="rbac_test_sub_333",
            email="rbac_user@sentinel.io",
            name="RBAC Normal User"
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            client.get(f'/auth/google/callback?code=mock_code&state={state}', follow_redirects=True)

            # Attempt to access admin routes
            admin_page_res = client.get('/admin/users')
            assert admin_page_res.status_code == 403

            admin_api_res = client.get('/api/admin/users')
            assert admin_api_res.status_code == 403

    def test_google_client_secret_never_in_page_source(self, client, app):
        """Verify GOOGLE_CLIENT_SECRET is never rendered in HTML page sources or API responses"""
        secret_token = "SUPER_SECRET_GOOGLE_KEY_98765_DO_NOT_EXPOSE"
        app.config['GOOGLE_CLIENT_ID'] = 'public-client-id.apps.googleusercontent.com'
        app.config['GOOGLE_CLIENT_SECRET'] = secret_token

        for route in ['/login', '/register', '/profile', '/settings']:
            res = client.get(route)
            assert secret_token.encode('utf-8') not in res.data, f"Client secret exposed in {route}"

    def test_google_oauth_audit_logs_recorded(self, client, app):
        """Verify OAuth login and creation events are recorded in audit logs without leaking secrets"""
        app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

        client.get('/auth/google')
        with client.session_transaction() as sess:
            state = sess['oauth_state']

        tokens, userinfo = mock_google_token_and_userinfo(
            sub="audit_test_sub_555",
            email="audit_user@sentinel.io",
            name="Audit Test User"
        )

        with patch('app.services.oauth_service.GoogleOAuthService.exchange_code_for_tokens', return_value=tokens), \
             patch('app.services.oauth_service.GoogleOAuthService.fetch_user_info', return_value=userinfo):

            client.get(f'/auth/google/callback?code=mock_code&state={state}', follow_redirects=True)

            with app.app_context():
                user = User.query.filter_by(email="audit_user@sentinel.io").first()
                assert user is not None

                logs = AuditLog.query.filter_by(user_id=user.id).all()
                event_types = [l.get_event_type for l in logs]
                assert EventType.GOOGLE_LOGIN_SUCCESS in event_types
                assert EventType.GOOGLE_ACCOUNT_CREATED in event_types

                # Verify tokens and secrets are never in details
                for l in logs:
                    details_str = str(l.details)
                    assert 'mock_google_access_token' not in details_str
                    assert 'mock_google_id_token' not in details_str
                    assert 'mock-client-secret' not in details_str
