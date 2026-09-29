"""
Pytest Test Suite for Sentinel System-Aware Theme System
Validates:
1. Early theme initialization script in <head> across public and private pages (FOUC prevention)
2. Unified Navigation Theme Selector present in base.html and public_base.html
3. Settings page Appearance section with System, Light, Dark segmented controls
4. Public marketing and SEO pages support theme selection
5. Auth pages (login, register, forgot-password, reset-password) include FOUC prevention
6. CSS stylesheets (sentinel.css, landing.css) declare light and dark tokens and reduced-motion rules
7. Admin pages inherit the unified theme controls
"""

import pytest


class TestThemeSystemIntegration:
    """Test suite for Sentinel system-aware theme implementation."""

    def test_landing_page_theme_controls_and_early_init(self, client):
        """Verify landing page contains early init script and theme selector."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Early initialization script in <head>
        assert 'sentinel_theme' in html
        assert 'data-theme' in html
        assert 'prefers-color-scheme: dark' in html

        # Theme selector in header
        assert 'theme-selector-wrapper' in html
        assert 'theme-toggle-btn' in html
        assert 'theme-dropdown-menu' in html
        assert 'data-theme-choice="system"' in html
        assert 'data-theme-choice="light"' in html
        assert 'data-theme-choice="dark"' in html

    def test_public_subpages_have_theme_controls(self, client):
        """Verify all public marketing/SEO pages contain the theme selector."""
        for path in ['/features', '/how-it-works', '/fraud-detection', '/security', '/about', '/faq', '/contact']:
            res = client.get(path, follow_redirects=False)
            assert res.status_code == 200, f"Failed on path {path}"
            html = res.data.decode('utf-8')
            assert 'theme-toggle-btn' in html, f"Missing theme-toggle-btn on {path}"
            assert 'sentinel_theme' in html, f"Missing early init script on {path}"
            assert 'data-theme-choice="system"' in html, f"Missing system theme option on {path}"

    def test_base_template_early_init_and_topbar_selector(self, client, authenticated_client):
        """Verify authenticated dashboard page has early init and topbar theme dropdown."""
        res = authenticated_client.get('/dashboard')
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Early theme initialization
        assert 'sentinel_theme' in html
        assert 'data-theme-preference' in html

        # Topbar theme selector
        assert 'theme-selector-wrapper' in html
        assert 'id="theme-toggle-btn"' in html
        assert 'id="theme-dropdown"' in html
        assert 'data-theme-choice="system"' in html
        assert 'data-theme-choice="light"' in html
        assert 'data-theme-choice="dark"' in html
        assert 'aria-haspopup="menu"' in html

    def test_settings_page_appearance_section(self, client, authenticated_client):
        """Verify settings page contains the Appearance card with System, Light, Dark controls."""
        res = authenticated_client.get('/settings')
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Appearance' in html
        assert 'Automatically follows your device preference.' in html
        assert 'theme-segmented-control' in html
        assert 'data-theme-value="system"' in html
        assert 'data-theme-value="light"' in html
        assert 'data-theme-value="dark"' in html
        assert 'Interface Theme' in html

    def test_auth_pages_fouc_prevention(self, client):
        """Verify login, register, forgot-password pages have early theme initialization."""
        for path in ['/login', '/register', '/forgot-password']:
            res = client.get(path)
            assert res.status_code == 200, f"Failed on {path}"
            html = res.data.decode('utf-8')
            assert 'sentinel_theme' in html, f"Missing early init on {path}"
            assert 'data-theme-preference' in html, f"Missing preference attribute on {path}"

    def test_admin_pages_contain_theme_controls(self, client, admin_client):
        """Verify admin pages inherit the base theme selector."""
        for path in ['/admin/users', '/admin/audit-logs']:
            res = admin_client.get(path)
            assert res.status_code == 200, f"Failed on {path}"
            html = res.data.decode('utf-8')
            assert 'theme-toggle-btn' in html, f"Missing theme toggle on {path}"
            assert 'data-theme-choice="system"' in html, f"Missing system choice on {path}"

    def test_sentinel_css_theme_definitions(self):
        """Verify sentinel.css includes light and dark theme tokens and reduced motion."""
        with open('static/css/sentinel.css', 'r', encoding='utf-8') as f:
            css = f.read()

        assert '[data-theme="light"]' in css
        assert '[data-theme="dark"]' in css
        assert '--bg-app' in css
        assert '--bg-surface' in css
        assert '.theme-selector-wrapper' in css
        assert '.theme-dropdown-menu' in css
        assert '.theme-segmented-control' in css
        assert '.theme-segment-btn' in css
        assert 'prefers-reduced-motion' in css

    def test_landing_css_theme_definitions(self):
        """Verify landing.css includes light and dark theme tokens and reduced motion."""
        with open('static/css/landing.css', 'r', encoding='utf-8') as f:
            css = f.read()

        assert '[data-theme="light"]' in css
        assert '[data-theme="dark"]' in css
        assert '--bg-primary' in css
        assert '--text-primary' in css
        assert '.theme-selector-wrapper' in css
        assert '.theme-dropdown-menu' in css
        assert 'prefers-reduced-motion' in css
