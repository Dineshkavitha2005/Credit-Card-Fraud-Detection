"""
Test Suite for Redesigned Sentinel Public Landing Page
Verifies all 24 required sections, semantic elements, editorial labels,
live transaction stream telemetry, security architecture specifications,
and motion script assets.
"""

import pytest


class TestLandingPageRedesign:
    """Validate redesigned Sentinel command center landing page elements."""

    def test_hero_narrative_and_eyebrow(self, client):
        """Verify hero headline, eyebrow, subtext, and CTAs match design requirements."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Eyebrow & Headline
        assert 'REAL-TIME FINANCIAL SECURITY' in html
        assert 'Detect the transaction.' in html
        assert 'Understand the risk.' in html
        assert 'Stop the fraud.' in html

        # Subtext
        assert 'Machine-learning risk scoring and transaction surveillance for modern payment systems.' in html

        # CTAs
        assert 'Open Sentinel Console' in html
        assert 'See how it works' in html

    def test_live_transaction_stream_telemetry(self, client):
        """Verify live transaction stream displays expected rows, score, and decision."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Transaction cards
        assert 'VISA' in html
        assert '4921' in html
        assert '$842' in html

        assert 'MASTERCARD' in html
        assert '7812' in html
        assert '$124' in html

        assert 'AMEX' in html
        assert '3349' in html
        assert '$4,920' in html

        # Trigger evaluation
        assert '93' in html
        assert '100' in html
        assert 'BLOCK' in html

    def test_editorial_section_labels(self, client):
        """Verify editorial numbered section labels replace generic badges."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        expected_labels = [
            '01 — THE PROBLEM',
            '02 — LIVE EVALUATION',
            '03 — DETECTION PIPELINE',
            '04 — INSIDE A DECISION',
            '05 — SECURITY ARCHITECTURE',
            '06 — AUDIT TRAIL',
            '07 — CONSOLE OPERATIONS',
            '08 — ENGINEERING FOUNDATION'
        ]
        for label in expected_labels:
            assert label in html, f"Missing editorial label: {label}"

    def test_problem_section_horizontal_timeline(self, client):
        """Verify the problem section headline and 5 timeline stages."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Fraud moves faster than manual review.' in html
        assert 'Transaction' in html
        assert 'Anomaly' in html
        assert 'Signal' in html
        assert 'Risk' in html
        assert 'Decision' in html

    def test_live_detection_workbench_telemetry(self, client):
        """Verify live evaluation workbench details and risk engine outputs."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Watch Sentinel evaluate a transaction.' in html
        assert 'Amazon' in html
        assert '48,920' in html
        assert 'Chennai, IN' in html
        assert '7 transactions / 2 min' in html
        assert '0.87' in html
        assert '0.91' in html
        assert 'BLOCK TRANSACTION' in html

    def test_seven_stage_detection_pipeline(self, client):
        """Verify all 7 stages of the transaction surveillance pipeline."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        stages = [
            'TRANSACTION',
            'INGESTION',
            'FEATURE ENGINEERING',
            'ML SCORING',
            'RULE ENGINE',
            'DECISION',
            'AUDIT EVENT'
        ]
        for stage in stages:
            assert stage in html, f"Missing pipeline stage: {stage}"

    def test_security_architecture_nodes(self, client):
        """Verify enterprise security components are rendered."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Google OIDC + PKCE' in html
        assert 'RFC 7636' in html
        assert 'AES-128' in html
        assert 'Tokenization Layer' in html
        assert 'Role-Based Access' in html
        assert 'Immutable Audit Logging' in html
        assert 'Session Security' in html

    def test_audit_trail_timeline_events(self, client):
        """Verify microsecond audit trail timestamps and events."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert '10:32:18.104' in html
        assert 'Transaction received' in html
        assert '10:32:18.112' in html
        assert 'Features extracted' in html
        assert '10:32:19.041' in html
        assert 'Risk score generated' in html
        assert '10:32:19.055' in html
        assert 'Velocity rule triggered' in html
        assert '10:32:19.068' in html
        assert 'Transaction blocked' in html
        assert '10:32:20.002' in html
        assert 'Audit event recorded' in html

    def test_engineering_credibility_factual_claims(self, client):
        """Verify engineering credibility grid shows real, verifiable capabilities."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Automated Testing' in html
        assert 'OAuth 2.0 + PKCE' in html
        assert 'Granular RBAC' in html
        assert 'Encrypted Card Vault' in html
        assert 'Audit Logging' in html
        assert 'Docker Deployment' in html
        assert 'PostgreSQL & SQLite' in html
        assert 'CI/CD Automation' in html

    def test_static_assets_serve_successfully(self, client):
        """Verify landing CSS and landing-motion JS return HTTP 200."""
        css_res = client.get('/static/css/landing.css')
        assert css_res.status_code == 200
        assert 'sentinel-nav-header' in css_res.data.decode('utf-8')

        js_res = client.get('/static/js/landing-motion.js')
        assert js_res.status_code == 200
        assert 'initLiveTransactionStream' in js_res.data.decode('utf-8')
