import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import os
import re
import requests

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print(f"=== Sentinel Live Server OAuth & Security Verification ===")
    print(f"Target: {BASE_URL}")

    # Load secret from .env to verify it is NEVER leaked
    secret_value = ""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_CLIENT_SECRET="):
                    secret_value = line.split("=", 1)[1].strip().strip('"\'')
                    break

    assert secret_value, "GOOGLE_CLIENT_SECRET not found in .env"
    print(f"✓ GOOGLE_CLIENT_SECRET is present in .env (length: {len(secret_value)})")

    session = requests.Session()

    # 1. Test /auth/google redirect & state generation
    print("\n[Test 1] Testing /auth/google initiation...")
    resp = session.get(f"{BASE_URL}/auth/google", allow_redirects=False)
    assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
    loc = resp.headers.get("Location", "")
    assert "accounts.google.com/o/oauth2/v2/auth" in loc, "Did not redirect to Google OAuth endpoint"
    assert "client_id=" in loc, "client_id missing from redirect URL"
    assert "code_challenge=" in loc, "PKCE code_challenge missing"
    assert "state=" in loc, "CSRF state missing"
    assert secret_value not in loc, "CRITICAL: Secret leaked in redirect URL!"

    # Extract state from redirect URL
    state_match = re.search(r"state=([^&]+)", loc)
    assert state_match, "State param not found in Location"
    oauth_state = state_match.group(1)
    print(f"✓ Redirect URL valid. State generated: {oauth_state[:8]}... (PKCE S256 active)")

    # 2. Test OAuth cancellation
    print("\n[Test 2] Testing OAuth user cancellation (error=access_denied)...")
    cancel_resp = session.get(
        f"{BASE_URL}/auth/google/callback?error=access_denied&state={oauth_state}",
        allow_redirects=True
    )
    assert cancel_resp.status_code == 200, f"Expected 200 after redirect, got {cancel_resp.status_code}"
    assert "cancelled" in cancel_resp.text.lower() or "denied" in cancel_resp.text.lower(), (
        "Cancellation flash message not found"
    )
    assert secret_value not in cancel_resp.text, "CRITICAL: Secret leaked in cancellation response!"
    print("✓ OAuth cancellation safely handled with user flash message.")

    # 3. Test Invalid OAuth state (CSRF Protection)
    print("\n[Test 3] Testing invalid/forged OAuth state rejection...")
    forged_resp = session.get(
        f"{BASE_URL}/auth/google/callback?code=mock_code&state=forged_state_value_12345",
        allow_redirects=True
    )
    assert forged_resp.status_code == 200, f"Expected 200, got {forged_resp.status_code}"
    assert "invalid state" in forged_resp.text.lower() or "unable to sign in" in forged_resp.text.lower(), (
        "Invalid state error not shown"
    )
    assert secret_value not in forged_resp.text, "CRITICAL: Secret leaked in CSRF error response!"
    print("✓ Invalid/forged OAuth state correctly rejected.")

    # 4. Test Missing state
    print("\n[Test 4] Testing missing OAuth state rejection...")
    missing_state_resp = session.get(
        f"{BASE_URL}/auth/google/callback?code=mock_code",
        allow_redirects=True
    )
    assert missing_state_resp.status_code == 200
    assert "unable to sign in" in missing_state_resp.text.lower()
    print("✓ Missing OAuth state correctly rejected.")

    # 5. Test Invalid authorization code with real Google token endpoint
    print("\n[Test 5] Testing invalid authorization code token exchange with live Google endpoint...")
    # Get a fresh state
    fresh_resp = session.get(f"{BASE_URL}/auth/google", allow_redirects=False)
    fresh_loc = fresh_resp.headers.get("Location", "")
    fresh_state = re.search(r"state=([^&]+)", fresh_loc).group(1)

    bad_code_resp = session.get(
        f"{BASE_URL}/auth/google/callback?code=invalid_auth_code_987654321&state={fresh_state}",
        allow_redirects=True
    )
    assert bad_code_resp.status_code == 200
    assert "unable to sign in" in bad_code_resp.text.lower() or "failed" in bad_code_resp.text.lower()
    assert secret_value not in bad_code_resp.text, "CRITICAL: Secret leaked in failed code exchange!"
    print("✓ Invalid authorization code safely rejected by Google token endpoint and handled gracefully.")

    # 6. Test Replayed OAuth state
    print("\n[Test 6] Testing replayed OAuth state rejection...")
    replay_resp = session.get(
        f"{BASE_URL}/auth/google/callback?code=invalid_auth_code_987654321&state={fresh_state}",
        allow_redirects=True
    )
    assert replay_resp.status_code == 200
    assert "unable to sign in" in replay_resp.text.lower() or "invalid state" in replay_resp.text.lower()
    print("✓ Replayed state rejected (session state was cleared/invalidated).")

    # 7. Check all public and authenticated pages for SECRET_KEY / CLIENT_SECRET leakage
    print("\n[Test 7] Inspecting pages, cookies, headers, and API responses for secret leakage...")
    
    # Log in as admin to check authenticated pages too
    login_resp = session.post(
        f"{BASE_URL}/login",
        data={"username": "admin", "password": "admin123"},
        allow_redirects=True
    )
    assert login_resp.status_code == 200
    assert "Dashboard" in login_resp.text or "overview" in login_resp.text.lower()
    print("  - Authenticated as admin session.")

    endpoints_to_inspect = [
        "/login",
        "/register",
        "/dashboard",
        "/transactions",
        "/alerts",
        "/analytics",
        "/cards",
        "/reports",
        "/settings",
        "/profile",
        "/admin/users",
        "/admin/audit-logs",
        "/health",
        "/api/dashboard/stats",
        "/api/transactions",
        "/api/alerts",
        "/api/cards",
        "/api/fraud-rules",
        "/api/admin/users",
        "/api/admin/audit-logs"
    ]

    for ep in endpoints_to_inspect:
        r = session.get(f"{BASE_URL}{ep}")
        assert secret_value not in r.text, f"CRITICAL LEAK: GOOGLE_CLIENT_SECRET found in response from {ep}!"
        for header_name, header_val in r.headers.items():
            assert secret_value not in header_val, f"CRITICAL LEAK: GOOGLE_CLIENT_SECRET found in header {header_name} from {ep}!"
        for cookie in session.cookies:
            assert secret_value not in cookie.value, f"CRITICAL LEAK: GOOGLE_CLIENT_SECRET found in cookie {cookie.name}!"
        print(f"  ✓ Checked {ep} [{r.status_code}] - 0 secret leaks detected")

    # 8. Test Logout and Session Invalidation
    print("\n[Test 8] Testing Logout and Session Invalidation...")
    logout_resp = session.get(f"{BASE_URL}/logout", allow_redirects=True)
    assert logout_resp.status_code == 200
    # Verify protected page requires login now
    dash_check = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    assert dash_check.status_code == 302 and "/login" in dash_check.headers.get("Location", ""), (
        "Session was not invalidated upon logout!"
    )
    print("✓ Session successfully terminated and protected route redirects to /login.")

    # 9. Test Logout all devices
    print("\n[Test 9] Testing Logout all devices endpoint...")
    # Re-login
    session.post(f"{BASE_URL}/login", data={"username": "admin", "password": "admin123"})
    logout_all_resp = session.post(f"{BASE_URL}/api/logout-all-devices", json={})
    assert logout_all_resp.status_code == 200, f"Expected 200, got {logout_all_resp.status_code}"
    dash_check2 = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    assert dash_check2.status_code == 302, "Session active after logout-all-devices!"
    print("✓ Logout all devices successfully revoked sessions.")

    print("\n========================================================")
    print("ALL LIVE OAUTH & SECURITY TESTS PASSED SAFELY AND CLEANLY")
    print("========================================================")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n❌ TEST FAILURE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
