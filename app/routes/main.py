from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render home landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')


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

