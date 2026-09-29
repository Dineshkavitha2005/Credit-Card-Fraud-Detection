"""
Test Suite for Omrix-Style Sentinel Public Landing Page
Verifies all 9 sections, semantic elements, interactive components,
live fraud detection cockpit, bento grid, pricing toggle, FAQ accordions,
and static assets.
"""

import pytest


class TestLandingPageRedesign:
    """Validate Omrix-style Sentinel command center landing page elements."""

    def test_hero_narrative_and_eyebrow(self, client):
        """Verify hero headline, eyebrow, subtext, and CTAs match Omrix credit card design."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Eyebrow & Headline
        assert 'NOW IN PUBLIC BETA' in html
        assert 'PROTECTING $12B+ TRANSACTIONS' in html
        assert 'Stop Card Fraud.' in html
        assert 'Settle Smarter.' in html
        assert 'Scale Further.' in html

        # Subtext
        assert 'Sentinel connects your payment rails, evaluates credit card transactions in sub-10ms with ensemble ML' in html

        # CTAs & Guarantees
        assert 'Start Free Trial' in html
        assert 'Book a Demo' in html
        assert 'No credit card required' in html
        assert 'Sub-10ms scoring latency' in html

    def test_live_transaction_cockpit_elements(self, client):
        """Verify live credit card fraud cockpit, telemetry, and interactive buttons."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Telemetry & Badges
        assert 'LIVE ENGINE ACTIVE' in html
        assert 'RF-XGB ENSEMBLE' in html
        assert 'sim-btn-normal' in html
        assert 'sim-btn-stolen' in html
        assert 'sim-btn-velocity' in html

        # Transaction Card & Risk Assessment
        assert 'Card Authorization Payload' in html
        assert 'AI Risk Evaluation' in html
        assert 'risk-score-display' in html
        assert 'decision-badge' in html

        # Key Metrics
        assert '99.8%' in html
        assert '0.02%' in html
        assert '$14.2M' in html

    def test_how_it_works_three_steps(self, client):
        """Verify the 3-step 'From swipe to prevention in three steps' section."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'From swipe to prevention in three steps.' in html
        assert 'Connect Your Payment Stack' in html
        assert 'Real-Time AI Risk Scoring' in html
        assert 'Automate & Enforce Actions' in html
        assert '01' in html
        assert '02' in html
        assert '03' in html

    def test_bento_grid_six_cards(self, client):
        """Verify the 6-card bento grid matching Omrix's asymmetric layout."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Built for speed. Designed for scale.' in html
        assert 'AI-Powered Fraud Intelligence' in html
        assert 'Real-Time Telemetry Stream' in html
        assert 'Visual Rule & Threshold Engine' in html
        assert '50+ Native Integrations' in html
        assert 'Collaborative Workstation' in html
        assert 'Enterprise-Grade Security & PCI-DSS Level 1' in html

    def test_testimonials_and_spotlight_quote(self, client):
        """Verify social proof spotlight quote and verified testimonial reviews."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'LOVED BY RISK LEADERS WORLDWIDE' in html
        assert 'We automated 84% of our fraud review operations in 30 days.' in html
        assert 'Jordan Mitchell' in html
        assert 'NexaPay Technologies' in html
        assert 'Sophie Bennett' in html
        assert 'Ethan Walker' in html

    def test_pricing_plans_and_toggle(self, client):
        """Verify pricing cards and interactive monthly/yearly billing toggle."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Start free. Scale without limits.' in html
        assert 'btn-monthly' in html
        assert 'btn-yearly' in html
        assert '20% off' in html
        assert 'Starter' in html
        assert 'Pro' in html
        assert 'Business' in html
        assert 'MOST POPULAR' in html

    def test_faq_accordion_items(self, client):
        """Verify FAQ section and expandable accordion questions."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'COMMON QUESTIONS' in html
        assert 'Everything you need to know.' in html
        assert 'How does Sentinel achieve sub-10ms scoring latency?' in html
        assert 'Will Sentinel cause false declines or hurt checkout conversions?' in html
        assert 'Is Sentinel compliant with PCI-DSS Level 1 and SOC 2?' in html
        assert 'Can we test Sentinel with historical transaction datasets?' in html

    def test_resources_and_insights_cards(self, client):
        """Verify research and resource insight articles."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Learn, build, and grow with Sentinel.' in html
        assert 'Stopping Account Takeover & Card-Testing Attacks in 2026' in html
        assert 'Why Heuristics Alone Fail: Shifting to Ensemble Risk Scoring' in html
        assert 'Zero-Knowledge Card Vaulting: Achieving PCI-DSS Level 1' in html

    def test_cta_banner_and_demo_modal(self, client):
        """Verify bottom CTA card and demo booking modal."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        assert 'Your revenue deserves bulletproof protection.' in html
        assert 'demo-modal-backdrop' in html
        assert 'Book a Live Architecture Demo' in html
        assert 'demo-volume' in html

    def test_static_assets_serve_successfully(self, client):
        """Verify landing CSS and Sentinel JS return HTTP 200."""
        css_res = client.get('/static/css/landing.css')
        assert css_res.status_code == 200
        assert 'omrix-navbar' in css_res.data.decode('utf-8')

        js_res = client.get('/static/js/sentinel.js')
        assert js_res.status_code == 200
        assert 'window.Sentinel' in js_res.data.decode('utf-8')

    def test_scrolling_animations_and_interactions(self, client):
        """Verify top reading progress bar, back to top button, and scroll reveal hooks."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')

        # Top scroll reading progress bar
        assert 'scroll-progress-container' in html
        assert 'scroll-progress-bar' in html

        # Back to top floating button with progress ring
        assert 'back-to-top' in html
        assert 'progress-ring' in html
        assert 'back-to-top-ring' in html

        # Hero mockup scroll reveal hook
        assert 'scroll-reveal-hero-mockup' in html

        # Script inclusion
        assert 'landing-motion.js' in html

        # CSS rules for scroll animations
        css_res = client.get('/static/css/landing.css')
        assert css_res.status_code == 200
        css_text = css_res.data.decode('utf-8')
        assert 'scroll-progress-bar' in css_text
        assert 'back-to-top-btn' in css_text
        assert 'scroll-reveal' in css_text
        assert 'prefers-reduced-motion' in css_text

        # Landing motion controller JS
        js_res = client.get('/static/js/landing-motion.js')
        assert js_res.status_code == 200
        js_text = js_res.data.decode('utf-8')
        assert 'initScrollProgress' in js_text
        assert 'initNavbarScroll' in js_text
        assert 'initScrollSpy' in js_text
        assert 'initScrollReveal' in js_text
        assert 'IntersectionObserver' in js_text

