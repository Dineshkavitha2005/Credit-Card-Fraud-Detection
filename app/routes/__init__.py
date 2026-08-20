from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.transactions import transactions_bp
from app.routes.cards import cards_bp
from app.routes.admin import admin_bp
from app.routes.analytics import analytics_bp
from app.routes.reports import reports_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'transactions_bp',
    'cards_bp',
    'admin_bp',
    'analytics_bp',
    'reports_bp',
]
