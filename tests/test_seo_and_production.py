"""
Test Suite for Public SEO Pages, Directives, ProxyFix, and Security Headers
Zero-dependency test suite using Python standard libraries (re, json, xml.etree.ElementTree).
Verifies:
- Public landing page and SEO subpages return HTTP 200 with unique titles and descriptions.
- robots.txt correctly formats crawler directives and sitemap reference.
- sitemap.xml dynamically generates compliant XML containing only canonical public URLs.
- Private / authenticated routes include X-Robots-Tag: noindex, nofollow.
- HTTP security headers are consistently present across responses.
- ProxyFix correctly decodes forwarded headers (X-Forwarded-Proto, X-Forwarded-For).
- JSON-LD structured data is present and valid JSON.
"""

import re
import json
import xml.etree.ElementTree as ET
import pytest


class TestSEOAndProductionArchitecture:
    """Test cases for SEO infrastructure, public pages, robots.txt, and security headers."""

    def test_public_landing_page_renders_successfully(self, client):
        """Verify root / serves the public landing page with semantic content for unauthenticated users."""
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        assert 'Intelligent Fraud Defense' in html or 'Sentinel' in html
        assert 'Real-Time Transaction Surveillance' in html
        assert '<h1' in html
        assert 'class="hero"' in html
        assert '/login' in html
        assert '/register' in html

    def test_public_seo_subpages_status_and_metadata(self, client):
        """Verify all public SEO subpages return 200 and possess unique titles and meta descriptions."""
        seo_pages = [
            ('/features', 'Features'),
            ('/how-it-works', 'How It Works'),
            ('/fraud-detection', 'Fraud Detection'),
            ('/security', 'Security'),
            ('/about', 'About'),
            ('/contact', 'Contact'),
            ('/faq', 'FAQ'),
        ]

        seen_titles = set()
        seen_descriptions = set()

        for path, expected_phrase in seo_pages:
            res = client.get(path)
            assert res.status_code == 200, f"Page {path} failed with status {res.status_code}"
            html = res.data.decode('utf-8')

            # Extract title using regex
            title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
            assert title_match is not None, f"Missing <title> tag on {path}"
            title_text = title_match.group(1).strip()
            assert len(title_text) > 10, f"Title too short on {path}"
            assert expected_phrase.lower() in title_text.lower(), f"Expected keyword '{expected_phrase}' in title on {path}"
            assert title_text not in seen_titles, f"Duplicate title detected on {path}: {title_text}"
            seen_titles.add(title_text)

            # Extract meta description using regex (support double or single quoted content)
            desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content="([^"]*)"', html, re.DOTALL | re.IGNORECASE)
            if not desc_match:
                desc_match = re.search(r"<meta\s+name=['\"]description['\"]\s+content='([^']*)'", html, re.DOTALL | re.IGNORECASE)
            assert desc_match is not None, f"Missing <meta name='description'> on {path}"
            desc_text = desc_match.group(1).strip()
            assert len(desc_text) > 25, f"Meta description too short on {path}"
            assert desc_text not in seen_descriptions, f"Duplicate meta description on {path}"
            seen_descriptions.add(desc_text)

            # Extract canonical link
            canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href="([^"]*)"', html, re.DOTALL | re.IGNORECASE)
            if not canonical_match:
                canonical_match = re.search(r"<link\s+rel=['\"]canonical['\"]\s+href='([^']*)'", html, re.DOTALL | re.IGNORECASE)
            assert canonical_match is not None, f"Missing <link rel='canonical'> on {path}"
            assert canonical_match.group(1).startswith('https://')

    def test_robots_txt_specification(self, client):
        """Verify /robots.txt serves plain text with correct crawler allowances and disallowances."""
        res = client.get('/robots.txt')
        assert res.status_code == 200
        assert 'text/plain' in res.content_type

        content = res.data.decode('utf-8')
        assert 'User-agent: *' in content
        assert 'Allow: /' in content
        assert 'Allow: /features' in content
        assert 'Allow: /how-it-works' in content
        assert 'Allow: /fraud-detection' in content
        assert 'Allow: /security' in content
        assert 'Allow: /about' in content
        assert 'Allow: /contact' in content
        assert 'Allow: /faq' in content

        # Check that private endpoints are disallowed
        assert 'Disallow: /dashboard' in content
        assert 'Disallow: /transactions' in content
        assert 'Disallow: /analytics' in content
        assert 'Disallow: /alerts' in content
        assert 'Disallow: /cards' in content
        assert 'Disallow: /reports' in content
        assert 'Disallow: /settings' in content
        assert 'Disallow: /admin/' in content
        assert 'Disallow: /api/' in content
        assert 'Disallow: /auth/' in content

        # Check sitemap directive
        assert 'Sitemap: https://' in content
        assert '/sitemap.xml' in content

    def test_sitemap_xml_validity_and_urls(self, client):
        """Verify /sitemap.xml generates valid XML containing only canonical public URLs."""
        res = client.get('/sitemap.xml')
        assert res.status_code == 200
        assert 'application/xml' in res.content_type

        xml_data = res.data.decode('utf-8')
        root = ET.fromstring(xml_data)

        # Namespace for standard sitemap
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('sm:url', ns)
        assert len(urls) == 8, f"Expected 8 canonical URLs in sitemap, got {len(urls)}"

        locs = [url.find('sm:loc', ns).text for url in urls]
        # Check canonical HTTPS prefix
        for loc in locs:
            assert loc.startswith('https://'), f"Sitemap URL not HTTPS: {loc}"
            assert not any(p in loc for p in ['/dashboard', '/admin', '/transactions', '/api']), f"Private route leaked in sitemap: {loc}"

        expected_paths = ['/', '/features', '/how-it-works', '/fraud-detection', '/security', '/about', '/contact', '/faq']
        for path in expected_paths:
            assert any(loc.endswith(path) for loc in locs), f"Missing path in sitemap: {path}"

    def test_private_routes_have_noindex_tag(self, client):
        """Verify authenticated / internal routes return X-Robots-Tag: noindex, nofollow."""
        private_paths = [
            '/dashboard',
            '/transactions',
            '/analytics',
            '/alerts',
            '/cards',
            '/reports',
            '/settings',
            '/api/health',
        ]
        for path in private_paths:
            res = client.get(path, follow_redirects=False)
            robots_header = res.headers.get('X-Robots-Tag')
            assert robots_header is not None, f"Missing X-Robots-Tag on private path {path}"
            assert 'noindex' in robots_header
            assert 'nofollow' in robots_header

    def test_public_pages_do_not_have_noindex(self, client):
        """Verify public marketing and SEO pages are NOT flagged with noindex."""
        public_paths = ['/', '/features', '/how-it-works', '/fraud-detection', '/security', '/about', '/contact', '/faq']
        for path in public_paths:
            res = client.get(path)
            assert res.status_code == 200
            robots_header = res.headers.get('X-Robots-Tag')
            assert robots_header is None or 'noindex' not in robots_header, f"Accidental noindex on public page {path}"

    def test_defense_in_depth_security_headers(self, client):
        """Verify standard security headers are injected into HTTP responses."""
        res = client.get('/')
        assert res.status_code == 200
        assert res.headers.get('X-Content-Type-Options') == 'nosniff'
        assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'
        assert res.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
        assert 'camera=()' in res.headers.get('Permissions-Policy', '')

    def test_json_ld_structured_data_on_faq(self, client):
        """Verify /faq contains valid JSON-LD schema with FAQPage type."""
        res = client.get('/faq')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        assert len(matches) > 0, "Missing JSON-LD structured data on /faq"

        parsed = False
        for content in matches:
            try:
                data = json.loads(content.strip())
                if data.get('@type') == 'FAQPage':
                    assert 'mainEntity' in data
                    assert len(data['mainEntity']) >= 3
                    parsed = True
            except (json.JSONDecodeError, TypeError):
                pass
        assert parsed, "Failed to locate and validate FAQPage schema in /faq"

    def test_proxy_fix_forwarded_proto_handling(self, client):
        """Verify ProxyFix middleware correctly treats X-Forwarded-Proto: https as secure."""
        res = client.get('/', headers={'X-Forwarded-Proto': 'https'})
        assert res.status_code == 200
        # When request is secure, Strict-Transport-Security header must be present
        assert 'Strict-Transport-Security' in res.headers
        assert 'max-age=31536000' in res.headers['Strict-Transport-Security']
