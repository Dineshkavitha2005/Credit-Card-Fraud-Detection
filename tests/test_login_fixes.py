import pytest

def test_login_page_fixes(client):
    """Verify logo visibility, Google button color, and removal of demo access."""
    res = client.get('/login')
    assert res.status_code == 200
    html = res.data.decode('utf-8')

    # 1. Verify demo access is completely removed
    assert 'Demo access' not in html
    assert 'demo-pill' not in html
    assert 'admin123' not in html

    # 2. Verify logo is styled with text-inverted for high contrast in all themes
    assert '.auth-brand-logo {' in html
    assert 'color: var(--text-inverted);' in html
    assert 'data-lucide="shield"' in html

    # 3. Verify Google sign-in button text is visible and styled with text-primary
    assert '.btn-google {' in html
    assert 'color: var(--text-primary);' in html
    assert 'Continue with Google' in html

def test_register_page_fixes(client):
    """Verify logo and Google button visibility on register page."""
    res = client.get('/register')
    assert res.status_code == 200
    html = res.data.decode('utf-8')

    assert '.auth-brand-logo {' in html
    assert 'color: var(--text-inverted);' in html
    assert '.btn-google {' in html
    assert 'color: var(--text-primary);' in html
    assert 'Continue with Google' in html
