import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / '.env'
print(f"DEBUG: env_path={env_path}, exists={env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True)

print("DEBUG: os.getenv GOOGLE_CLIENT_ID =", repr(os.getenv('GOOGLE_CLIENT_ID')))
print("DEBUG: os.getenv GOOGLE_CLIENT_SECRET =", repr(os.getenv('GOOGLE_CLIENT_SECRET')))

from app import create_app
from app.services.oauth_service import oauth_service

app = create_app()

with app.app_context():
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = app.config.get('GOOGLE_REDIRECT_URI')
    is_conf = oauth_service.is_configured()

    print(f"Loaded Client ID: {client_id[:15]}...{client_id[-20:] if client_id else 'None'}")
    print(f"Loaded Secret: {'Set (' + str(len(client_secret)) + ' chars)' if client_secret else 'Missing'}")
    print(f"Redirect URI: {redirect_uri}")
    print(f"OAuth Service Configured: {is_conf}")

    if is_conf:
        state = oauth_service.generate_state()
        verifier, challenge, method = oauth_service.generate_pkce()
        auth_url = oauth_service.build_authorization_url(state=state, code_challenge=challenge)
        print(f"Auth URL successfully generated:\n{auth_url}\n")
        assert "accounts.google.com" in auth_url
        assert client_id in auth_url
        assert "code_challenge=" in auth_url
        print("==================================================================")
        print("✅ Google OAuth 2.0 Client ID and Secret are loaded & READY!")
        print("==================================================================")
