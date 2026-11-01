"""
Google OAuth 2.0 / OpenID Connect Service for Sentinel
Enterprise-grade authorization-code flow with PKCE, state protection, and safe account linking.
"""

import os
import re
import base64
import hashlib
import secrets
from datetime import datetime
from urllib.parse import urlencode, urljoin
import requests
from flask import current_app, url_for

from app.extensions import db
from app.models.user import User, UserIdentity


class OAuthError(Exception):
    """Custom exception for OAuth protocol and communication errors"""
    def __init__(self, message, code="OAUTH_ERROR", status_code=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class GoogleOAuthService:
    """
    Service managing Google OAuth 2.0 / OpenID Connect authorization, token exchange,
    and user account provisioning / linking.
    """

    GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

    @property
    def client_id(self) -> str:
        """Google Client ID from app config or environment"""
        if current_app and 'GOOGLE_CLIENT_ID' in current_app.config:
            val = current_app.config.get('GOOGLE_CLIENT_ID')
            return str(val or '').strip()
        return os.getenv('GOOGLE_CLIENT_ID', '').strip()

    @property
    def client_secret(self) -> str:
        """Google Client Secret from app config or environment (Server-Side Only)"""
        if current_app and 'GOOGLE_CLIENT_SECRET' in current_app.config:
            val = current_app.config.get('GOOGLE_CLIENT_SECRET')
            return str(val or '').strip()
        return os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

    @property
    def configured_redirect_uri(self) -> str:
        """Explicit redirect URI from app config or environment"""
        if current_app and 'GOOGLE_REDIRECT_URI' in current_app.config:
            val = current_app.config.get('GOOGLE_REDIRECT_URI')
            return str(val or '').strip()
        return os.getenv('GOOGLE_REDIRECT_URI', '').strip()

    @property
    def allowed_domains(self) -> list:
        """List of allowed Google Workspace domains if restriction configured"""
        raw = ""
        if current_app and 'GOOGLE_ALLOWED_DOMAIN' in current_app.config:
            raw = current_app.config.get('GOOGLE_ALLOWED_DOMAIN') or ''
        elif os.getenv('GOOGLE_ALLOWED_DOMAIN'):
            raw = os.getenv('GOOGLE_ALLOWED_DOMAIN', '')
        if not raw:
            return []
        return [d.strip().lower() for d in str(raw).split(',') if d.strip()]

    def is_configured(self) -> bool:
        """Check if Google OAuth credentials are configured"""
        return bool(self.client_id and self.client_secret)

    def get_redirect_uri(self) -> str:
        """Get the effective OAuth callback redirect URI"""
        if self.configured_redirect_uri:
            return self.configured_redirect_uri
        try:
            return url_for('auth.google_callback', _external=True)
        except RuntimeError:
            return "http://localhost:5000/auth/google/callback"

    @staticmethod
    def generate_state() -> str:
        """Generate cryptographically secure OAuth state parameter"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_pkce() -> tuple:
        """
        Generate PKCE code_verifier and code_challenge using S256 method.
        Returns (code_verifier, code_challenge, code_challenge_method)
        """
        # Generate 64-byte high-entropy cryptographic random string (86 characters URL-safe)
        code_verifier = secrets.token_urlsafe(64)
        # Compute SHA-256 hash
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        # Base64URL-encode without padding
        code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        return code_verifier, code_challenge, "S256"

    def build_authorization_url(self, state: str, code_challenge: str = None) -> str:
        """
        Construct Google OAuth 2.0 Authorization URL requesting openid, email, and profile scopes.
        """
        if not self.is_configured():
            raise OAuthError("Google OAuth is not configured on this server.", code="OAUTH_NOT_CONFIGURED")

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.get_redirect_uri(),
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'access_type': 'online',
            'prompt': 'select_account'
        }

        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = 'S256'

        return f"{self.GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, code_verifier: str = None) -> dict:
        """
        Exchange OAuth authorization code for Google access token and id_token.
        Server-side only execution with strict timeout.
        """
        if not self.is_configured():
            raise OAuthError("Google OAuth client is not configured.", code="OAUTH_NOT_CONFIGURED")

        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.get_redirect_uri()
        }

        if code_verifier:
            payload['code_verifier'] = code_verifier

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Sentinel-Security-Auth/2.4'
        }

        try:
            response = requests.post(
                self.GOOGLE_TOKEN_ENDPOINT,
                data=payload,
                headers=headers,
                timeout=15
            )
        except requests.RequestException as e:
            raise OAuthError(f"Network failure connecting to Google OAuth service: {str(e)}", code="NETWORK_ERROR")

        if response.status_code != 200:
            err_data = {}
            try:
                err_data = response.json()
            except Exception:
                pass
            err_desc = err_data.get('error_description') or err_data.get('error') or f"HTTP {response.status_code}"
            raise OAuthError(f"Google token exchange failed: {err_desc}", code="TOKEN_EXCHANGE_FAILED")

        try:
            tokens = response.json()
            if 'access_token' not in tokens:
                raise OAuthError("Google response did not contain an access token.", code="INVALID_TOKEN_RESPONSE")
            return tokens
        except ValueError:
            raise OAuthError("Invalid JSON returned by Google token endpoint.", code="INVALID_JSON_RESPONSE")

    def fetch_user_info(self, access_token: str) -> dict:
        """
        Fetch and validate user identity claims from Google OpenID Connect UserInfo endpoint.
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'User-Agent': 'Sentinel-Security-Auth/2.4'
        }

        try:
            response = requests.get(
                self.GOOGLE_USERINFO_ENDPOINT,
                headers=headers,
                timeout=10
            )
        except requests.RequestException as e:
            raise OAuthError(f"Failed to fetch Google user profile: {str(e)}", code="NETWORK_ERROR")

        if response.status_code != 200:
            raise OAuthError("Failed to authenticate Google identity token.", code="USERINFO_FAILED")

        try:
            data = response.json()
        except ValueError:
            raise OAuthError("Invalid JSON from Google UserInfo endpoint.", code="INVALID_USERINFO")

        sub = data.get('sub')
        email = (data.get('email') or '').strip().lower()
        email_verified = bool(data.get('email_verified', False))

        if not sub:
            raise OAuthError("Missing verified subject identifier in Google identity response.", code="MISSING_SUBJECT")
        if not email:
            raise OAuthError("Missing email address in Google identity response.", code="MISSING_EMAIL")

        return {
            'sub': str(sub),
            'email': email,
            'email_verified': email_verified,
            'name': data.get('name') or data.get('given_name') or email.split('@')[0],
            'given_name': data.get('given_name', ''),
            'family_name': data.get('family_name', ''),
            'picture': data.get('picture', ''),
            'hd': data.get('hd', '')  # Google Workspace hosted domain
        }

    def validate_domain(self, user_info: dict) -> bool:
        """
        Validate whether the user's Google Workspace domain matches GOOGLE_ALLOWED_DOMAIN if set.
        """
        allowed = self.allowed_domains
        if not allowed:
            return True

        email = user_info.get('email', '')
        hd = (user_info.get('hd') or '').strip().lower()
        email_domain = email.split('@')[-1].lower() if '@' in email else ''

        return (hd in allowed) or (email_domain in allowed)

    @staticmethod
    def _generate_unique_username(base_name: str, email: str) -> str:
        """Generate a safe, unique username for a new OAuth user"""
        # Clean alphanumeric + underscore
        seed = base_name.lower().replace(' ', '_')
        seed = re.sub(r'[^a-z0-9_]', '', seed)
        if not seed:
            seed = email.split('@')[0]
            seed = re.sub(r'[^a-z0-9_]', '', seed)
        if not seed:
            seed = 'sentinel_user'

        seed = seed[:30]
        candidate = seed
        counter = 1

        while User.query.filter_by(username=candidate).first() is not None:
            suffix = f"_{counter}_{secrets.token_hex(2)}"
            candidate = f"{seed[:20]}{suffix}"
            counter += 1

        return candidate

    def resolve_or_create_user(self, user_info: dict, mode: str = 'login', linking_user: User = None) -> tuple:
        """
        Authenticate, link, or provision a Sentinel user from verified Google identity claims.
        Returns: (user: User, action: str, error_message: str)
        Actions: 'logged_in', 'created', 'linked', 'disabled', 'conflict', 'unauthorized'
        """
        sub = user_info['sub']
        email = user_info['email']
        email_verified = user_info.get('email_verified', False)
        name = user_info.get('name') or email.split('@')[0]
        picture = user_info.get('picture', '')

        # Domain restriction validation
        if not self.validate_domain(user_info):
            return None, 'unauthorized', 'Access restricted. Your Google Workspace domain is not authorized.'

        # ── Mode 1: Explicit Account Linking for Authenticated User ───────────
        if mode == 'link' and linking_user is not None:
            # Check if this Google sub is already associated with ANY other user
            existing_identity = UserIdentity.query.filter_by(
                provider='google', provider_subject=sub
            ).first()
            if existing_identity and existing_identity.user_id != linking_user.id:
                return None, 'conflict', 'This Google account is already associated with another Sentinel account.'

            existing_sub_user = User.query.filter_by(google_id=sub).first()
            if existing_sub_user and existing_sub_user.id != linking_user.id:
                return None, 'conflict', 'This Google account is already associated with another Sentinel account.'

            # Link identity
            if not existing_identity:
                new_identity = UserIdentity(
                    user_id=linking_user.id,
                    provider='google',
                    provider_subject=sub,
                    provider_email=email,
                    last_used_at=datetime.utcnow()
                )
                db.session.add(new_identity)
            else:
                existing_identity.last_used_at = datetime.utcnow()
                existing_identity.provider_email = email

            linking_user.google_id = sub
            linking_user.auth_provider = 'multiple' if linking_user.has_password else 'google'
            if picture and not linking_user.profile_picture:
                linking_user.profile_picture = picture

            db.session.commit()
            return linking_user, 'linked', None

        # ── Mode 2: Standard Login / Registration Flow ─────────────────────────

        # Step A: Check if Google subject is already directly linked via UserIdentity
        identity = UserIdentity.query.filter_by(
            provider='google', provider_subject=sub
        ).first()

        if identity:
            user = User.query.get(identity.user_id)
            if not user:
                # Orphaned identity, clean up
                db.session.delete(identity)
                db.session.commit()
            else:
                if not user.is_active:
                    return None, 'disabled', 'This account is currently disabled.'
                identity.last_used_at = datetime.utcnow()
                identity.provider_email = email
                user.google_id = sub
                db.session.commit()
                return user, 'logged_in', None

        # Step B: Check if User model has google_id directly
        user_by_google_id = User.query.filter_by(google_id=sub).first()
        if user_by_google_id:
            if not user_by_google_id.is_active:
                return None, 'disabled', 'This account is currently disabled.'
            # Create UserIdentity record if missing
            identity_record = UserIdentity(
                user_id=user_by_google_id.id,
                provider='google',
                provider_subject=sub,
                provider_email=email,
                last_used_at=datetime.utcnow()
            )
            db.session.add(identity_record)
            db.session.commit()
            return user_by_google_id, 'logged_in', None

        # Step C: Check if an existing Sentinel user matches Google's verified email
        if email_verified and email:
            existing_user_by_email = User.query.filter_by(email=email).first()
            if existing_user_by_email:
                # Check if this user is already linked to a different Google account
                if existing_user_by_email.google_id and existing_user_by_email.google_id != sub:
                    return None, 'conflict', 'This Google account is already associated with another Sentinel account.'

                if not existing_user_by_email.is_active:
                    return None, 'disabled', 'This account is currently disabled.'

                # Safe Account Linking: link Google subject to verified email account
                existing_user_by_email.google_id = sub
                existing_user_by_email.is_verified = True  # Verified by Google
                existing_user_by_email.auth_provider = 'multiple' if existing_user_by_email.has_password else 'google'
                if picture and not existing_user_by_email.profile_picture:
                    existing_user_by_email.profile_picture = picture

                identity_record = UserIdentity(
                    user_id=existing_user_by_email.id,
                    provider='google',
                    provider_subject=sub,
                    provider_email=email,
                    last_used_at=datetime.utcnow()
                )
                db.session.add(identity_record)
                db.session.commit()
                return existing_user_by_email, 'linked', None

        # Step D: Provision a New Sentinel User
        username = self._generate_unique_username(name, email)
        new_user = User(
            username=username,
            email=email,
            full_name=name,
            role='user',  # Security control: Always default 'user' role, never admin
            is_active=True,
            is_verified=True,  # Google verified email
            profile_picture=picture,
            google_id=sub,
            auth_provider='google',
            password_hash=None,  # No local password until user chooses to set one
            notification_preferences={'email': True, 'sms': False}
        )

        db.session.add(new_user)
        db.session.flush()

        identity_record = UserIdentity(
            user_id=new_user.id,
            provider='google',
            provider_subject=sub,
            provider_email=email,
            last_used_at=datetime.utcnow()
        )
        db.session.add(identity_record)
        db.session.commit()

        return new_user, 'created', None


# Global singleton instance
oauth_service = GoogleOAuthService()
