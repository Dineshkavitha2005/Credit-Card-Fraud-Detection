from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app, Response, request, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime
import os
from app.extensions import db
from app.models.user import User

main_bp = Blueprint('main', __name__)

# Centralized list of public canonical routes for SEO indexing & sitemaps
PUBLIC_ROUTES = [
    {'path': '/', 'priority': '1.0', 'changefreq': 'daily'},
    {'path': '/features', 'priority': '0.9', 'changefreq': 'weekly'},
    {'path': '/how-it-works', 'priority': '0.9', 'changefreq': 'weekly'},
    {'path': '/fraud-detection', 'priority': '0.8', 'changefreq': 'weekly'},
    {'path': '/security', 'priority': '0.8', 'changefreq': 'monthly'},
    {'path': '/about', 'priority': '0.7', 'changefreq': 'monthly'},
    {'path': '/contact', 'priority': '0.7', 'changefreq': 'monthly'},
    {'path': '/faq', 'priority': '0.8', 'changefreq': 'weekly'},
    {'path': '/privacy', 'priority': '0.6', 'changefreq': 'monthly'},
    {'path': '/terms', 'priority': '0.6', 'changefreq': 'monthly'},
]


def get_canonical_domain():
    """Resolve the production canonical domain without leaking placeholder domains."""
    cfg_domain = (current_app.config.get('CANONICAL_DOMAIN') or '').strip().rstrip('/')
    if cfg_domain and 'your-domain.com' not in cfg_domain and 'localhost' not in cfg_domain:
        return cfg_domain
    
    # In request context, determine canonical HTTPS domain from request headers or host
    if request and request.host:
        return f"https://{request.host}".rstrip('/')
    
    return 'https://sentinel.internal'


@main_bp.route('/')
def index():
    """Render public home landing page or redirect to dashboard if authenticated."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')


# ==============================================================================
# Public Technical SEO Pages
# ==============================================================================

@main_bp.route('/features')
def features_page():
    """Render public features showcase page."""
    return render_template('seo_features.html')


@main_bp.route('/how-it-works')
def how_it_works_page():
    """Render public technical architecture and fraud pipeline walkthrough."""
    return render_template('seo_how_it_works.html')


@main_bp.route('/fraud-detection')
def fraud_detection_page():
    """Render public fraud typology and anomaly detection overview."""
    return render_template('seo_fraud_detection.html')


@main_bp.route('/security')
def security_page():
    """Render public security, encryption, and compliance architecture."""
    return render_template('seo_security.html')


@main_bp.route('/about')
def about_page():
    """Render public about page detailing Sentinel's mission and architecture."""
    return render_template('seo_about.html')


@main_bp.route('/contact')
def contact_page():
    """Render public security inquiry and support contact page."""
    return render_template('seo_contact.html')


@main_bp.route('/faq')
def faq_page():
    """Render public FAQ page with structured FAQPage schema."""
    return render_template('seo_faq.html')


@main_bp.route('/privacy')
def privacy_page():
    """Render public Privacy Policy page based on actual Sentinel implementation."""
    return render_template('privacy.html')


@main_bp.route('/terms')
def terms_page():
    """Render public Terms of Service page based on actual Sentinel service parameters."""
    return render_template('terms.html')


# ==============================================================================
# Static Icons & Manifest Endpoints
# ==============================================================================

@main_bp.route('/favicon.ico')
def favicon():
    """Serve favicon for browser default requests."""
    return send_from_directory(
        os.path.join(current_app.static_folder, 'img'),
        'favicon-32x32.png',
        mimetype='image/png'
    )


@main_bp.route('/site.webmanifest')
def site_webmanifest():
    """Serve site.webmanifest for PWA and mobile bookmark metadata."""
    return send_from_directory(
        current_app.static_folder,
        'site.webmanifest',
        mimetype='application/manifest+json'
    )


# ==============================================================================
# Search Engine Indexing Directives (robots.txt & sitemap.xml)
# ==============================================================================

@main_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt directive for search engine crawlers."""
    domain = get_canonical_domain()
    
    allow_lines = "\n".join([f"Allow: {route['path']}" for route in PUBLIC_ROUTES])
    content = f"""User-agent: *
{allow_lines}
Allow: /static/

# Disallow private application routes and authenticated dashboards
Disallow: /dashboard
Disallow: /transactions
Disallow: /analytics
Disallow: /alerts
Disallow: /cards
Disallow: /reports
Disallow: /settings
Disallow: /admin
Disallow: /admin/
Disallow: /api/
Disallow: /auth/

Sitemap: {domain}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@main_bp.route('/sitemap.xml')
def sitemap_xml():
    """Generate XML sitemap listing canonical public pages from centralized route registry."""
    domain = get_canonical_domain()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for route in PUBLIC_ROUTES:
        loc = f"{domain}{route['path']}" if route['path'] != '/' else f"{domain}/"
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{loc}</loc>')
        xml_lines.append(f'    <lastmod>{today}</lastmod>')
        xml_lines.append(f'    <changefreq>{route["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{route["priority"]}</priority>')
        xml_lines.append('  </url>')
    xml_lines.append('</urlset>')
    
    return Response('\n'.join(xml_lines), mimetype='application/xml')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Render dashboard page."""
    return render_template('dashboard.html', user=current_user)


@main_bp.route('/transactions')
@login_required
def transactions_page():
    """Render transactions management page."""
    return render_template('transactions.html', user=current_user)


@main_bp.route('/analytics')
@login_required
def analytics_page():
    """Render analytics dashboard page."""
    return render_template('analytics.html', user=current_user)


@main_bp.route('/alerts')
@login_required
def alerts_page():
    """Render alerts page."""
    return render_template('alerts.html', user=current_user)


@main_bp.route('/settings')
@login_required
def settings_page():
    """Render user settings page."""
    return render_template('settings.html', user=current_user)


@main_bp.route('/cards')
@login_required
def cards_page():
    """Render cards management page."""
    return render_template('cards.html', user=current_user)


@main_bp.route('/health')
@main_bp.route('/api/health')
def health():
    """Health check endpoint for Docker container probes, Kubernetes liveness/readiness, and load balancers."""
    health_status = {
        "status": "healthy",
        "service": "credit-card-fraud-detection",
        "database": "connected"
    }
    status_code = 200
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"unhealthy: {str(e)}"
        status_code = 503
    return jsonify(health_status), status_code


@main_bp.route('/api/test/force-db-error')
def test_force_db_error():
    """Endpoint for testing database rollback and 500 error handling."""
    u = User(username='tmp_user_rollback_test', email='tmp_roll@test.com')
    db.session.add(u)
    db.session.execute(db.text("SELECT * FROM non_existent_table_xyz"))
    db.session.commit()
    return jsonify({"message": "OK"})

