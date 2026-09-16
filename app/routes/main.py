from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app, Response, request
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models.user import User

main_bp = Blueprint('main', __name__)

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


# ==============================================================================
# Search Engine Indexing Directives (robots.txt & sitemap.xml)
# ==============================================================================

@main_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt directive for search engine crawlers."""
    canonical_domain = current_app.config.get('CANONICAL_DOMAIN', 'https://your-domain.com').rstrip('/')
    content = f"""User-agent: *
Allow: /
Allow: /features
Allow: /how-it-works
Allow: /fraud-detection
Allow: /security
Allow: /about
Allow: /contact
Allow: /faq
Allow: /static/

# Disallow private application routes and authenticated dashboards
Disallow: /dashboard
Disallow: /transactions
Disallow: /analytics
Disallow: /alerts
Disallow: /cards
Disallow: /reports
Disallow: /settings
Disallow: /admin/
Disallow: /api/
Disallow: /auth/

Sitemap: {canonical_domain}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@main_bp.route('/sitemap.xml')
def sitemap_xml():
    """Generate XML sitemap listing canonical public pages."""
    canonical_domain = current_app.config.get('CANONICAL_DOMAIN', 'https://your-domain.com').rstrip('/')
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    pages = [
        {'loc': f"{canonical_domain}/", 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': f"{canonical_domain}/features", 'priority': '0.9', 'changefreq': 'weekly'},
        {'loc': f"{canonical_domain}/how-it-works", 'priority': '0.9', 'changefreq': 'weekly'},
        {'loc': f"{canonical_domain}/fraud-detection", 'priority': '0.8', 'changefreq': 'weekly'},
        {'loc': f"{canonical_domain}/security", 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': f"{canonical_domain}/about", 'priority': '0.7', 'changefreq': 'monthly'},
        {'loc': f"{canonical_domain}/contact", 'priority': '0.7', 'changefreq': 'monthly'},
        {'loc': f"{canonical_domain}/faq", 'priority': '0.8', 'changefreq': 'weekly'},
    ]
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for page in pages:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{page["loc"]}</loc>')
        xml_lines.append(f'    <lastmod>{today}</lastmod>')
        xml_lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{page["priority"]}</priority>')
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

