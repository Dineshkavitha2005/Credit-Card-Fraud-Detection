from datetime import datetime, timedelta
from sqlalchemy import or_
from app.extensions import db, audit_logger, EventType
from app.models.user import User
from app.models.audit import AuditLog, AdminAction
from app.models.alert import SuspiciousActivity

class AdminService:
    """Service for administrator management features."""

    @staticmethod
    def serialize_admin_user(user):
        """Format user object for admin management responses."""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'two_factor_enabled': user.two_factor_enabled,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }

    @staticmethod
    def prevent_self_admin_change(target_user, current_user, action_name):
        """Prevent self deactivation/blocking of current admin user."""
        if target_user.id == current_user.id:
            return {'error': f'You cannot {action_name} your own admin account.'}, 400
        return None
