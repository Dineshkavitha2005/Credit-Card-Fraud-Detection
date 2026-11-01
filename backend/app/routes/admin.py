import io
import csv
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db, audit_logger, EventType
from app.models.user import (
    User, UserSession, LoginAttempt, IPAddress, UserActivity,
    Notification, SecurityQuestion
)
from app.models.alert import Alert, SuspiciousActivity
from app.models.audit import AuditLog, AdminAction
from app.services.admin_service import AdminService

from errors import is_json_request, format_error_response

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to enforce admin role access."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            audit_logger.log_event(
                EventType.API_AUTH_FAILURE,
                user_id=current_user.id if current_user.is_authenticated else None,
                status='failure',
                target_resource=request.path,
                details={'reason': 'Unauthorized admin access attempt'}
            )
            if is_json_request():
                return jsonify(format_error_response('Forbidden: Admin access required', status_code=403, code='FORBIDDEN')), 403
            return render_template('message.html', title='Access Denied', message='You do not have administrative privileges to access this area.', type='danger'), 403
        return f(*args, **kwargs)
    return decorated_function


# ─── User Management Routes ───

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_users_page():
    """Render admin user management template"""
    return render_template('admin_users.html')


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Admin API to get all users with optional filtering & pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    query = User.query

    if role_filter and role_filter != 'all':
        query = query.filter_by(role=role_filter)

    if status_filter and status_filter != 'all':
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'blocked':
            query = query.filter_by(is_active=False)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern)
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [AdminService.serialize_admin_user(u) for u in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': pagination.per_page
    })


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_user_detail(user_id):
    """Admin API to get specific user detail."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(AdminService.serialize_admin_user(user))


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
@admin_required
def admin_update_user(user_id):
    """Admin API to update a user record."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': 'No update data provided'}), 400

    if 'role' in data:
        new_role = str(data['role']).strip().lower()
        if new_role not in {'user', 'admin'}:
            return jsonify({'error': 'Role must be either user or admin'}), 400
        if user.id == current_user.id and user.role == 'admin' and new_role != 'admin':
            return jsonify({'error': 'You cannot demote your own admin account.'}), 400
        user.role = new_role

    if 'is_active' in data:
        self_guard = AdminService.prevent_self_admin_change(user, current_user, 'deactivate')
        if self_guard is not None:
            return jsonify(self_guard[0]), self_guard[1]
        user.is_active = bool(data['is_active'])

    if 'full_name' in data:
        user.full_name = (data.get('full_name') or '').strip() or user.full_name
    if 'email' in data:
        email = (data.get('email') or '').strip()
        if email and User.query.filter(User.email == email, User.id != user.id).first():
            return jsonify({'error': 'A user with this email already exists'}), 400
        user.email = email
    if 'username' in data:
        username = (data.get('username') or '').strip()
        if username and User.query.filter(User.username == username, User.id != user.id).first():
            return jsonify({'error': 'A user with this username already exists'}), 400
        user.username = username

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_update',
        target_user_id=user.id,
        reason=data.get('reason', 'Admin updated user profile'),
        details={'changes': {k: v for k, v in data.items() if k not in {'password'}}},
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    audit_logger.log_event(
        EventType.ADMIN_USER_CHANGE,
        user_id=current_user.id,
        status='success',
        target_resource=f"User:{user.id}",
        details={'target_username': user.username, 'changes': {k: v for k, v in data.items() if k not in {'password'}}}
    )

    return jsonify({'message': 'User updated successfully', 'user': AdminService.serialize_admin_user(user)})


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Admin API to deactivate a user account without deleting the record."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    self_guard = AdminService.prevent_self_admin_change(user, current_user, 'delete or deactivate')
    if self_guard is not None:
        return jsonify(self_guard[0]), self_guard[1]

    user.is_active = False
    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_deactivate',
        target_user_id=user.id,
        reason='Admin deactivated user account',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    audit_logger.log_event(
        EventType.ACCOUNT_BLOCK,
        user_id=current_user.id,
        status='success',
        target_resource=f"User:{user.id}",
        details={'deactivated_username': user.username, 'reason': 'Admin deactivated user account'}
    )

    return jsonify({'message': f'User {user.username} deactivated successfully', 'user': AdminService.serialize_admin_user(user)})


@admin_bp.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
@admin_required
def admin_block_user(user_id):
    """Admin: Block user account."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    self_guard = AdminService.prevent_self_admin_change(user, current_user, 'block')
    if self_guard is not None:
        return jsonify(self_guard[0]), self_guard[1]

    data = request.get_json(silent=True) or {}
    user.is_active = False

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_block',
        target_user_id=user_id,
        reason=data.get('reason', 'Admin blocked user account'),
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    audit_logger.log_event(
        EventType.ACCOUNT_BLOCK,
        user_id=current_user.id,
        status='success',
        target_resource=f"User:{user.id}",
        details={'blocked_username': user.username, 'reason': data.get('reason', 'Admin blocked user account')}
    )

    return jsonify({'message': f'User {user.username} blocked', 'user': AdminService.serialize_admin_user(user)})


@admin_bp.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def admin_unblock_user(user_id):
    """Admin: Unblock user account."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_active = True

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='user_unblock',
        target_user_id=user_id,
        reason='Admin unblocked user account',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    audit_logger.log_event(
        EventType.ACCOUNT_UNBLOCK,
        user_id=current_user.id,
        status='success',
        target_resource=f"User:{user.id}",
        details={'unblocked_username': user.username}
    )

    return jsonify({'message': f'User {user.username} unblocked', 'user': AdminService.serialize_admin_user(user)})


@admin_bp.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_user_password(user_id):
    """Admin: Force password reset for user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    temp_password = secrets.token_urlsafe(16)
    user.set_password(temp_password)

    admin_action = AdminAction(
        admin_id=current_user.id,
        action_type='password_reset',
        target_user_id=user_id,
        reason='Admin requested password reset',
        status='executed'
    )
    db.session.add(admin_action)
    db.session.commit()

    return jsonify({
        'message': 'Password reset',
        'temporary_password': temp_password,
        'note': 'User should change this immediately'
    })


# ─── Alerts & Notifications ───

@admin_bp.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get fraud alerts list"""
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(50).all()
    return jsonify({
        'alerts': [{
            'id': a.id,
            'transaction_id': a.transaction_id,
            'alert_type': a.alert_type,
            'severity': a.severity,
            'message': a.message,
            'is_read': a.is_read,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in alerts]
    })


@admin_bp.route('/api/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    """Mark alert as read"""
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404

    alert.is_read = True
    db.session.commit()
    return jsonify({'message': 'Alert marked as read'})


@admin_bp.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get user notifications"""
    notifications = Notification.query.filter_by(user_id=current_user.id, is_sent=True).order_by(
        Notification.created_at.desc()
    ).limit(50).all()

    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'channel': n.channel,
            'subject': n.subject,
            'message': n.message,
            'sent_at': n.sent_at.isoformat() if n.sent_at else None,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    })


@admin_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    notification.is_sent = True
    db.session.commit()
    return jsonify({'message': 'Notification marked as read'})


# ─── Suspicious Activity & Security Questions ───

@admin_bp.route('/api/suspicious-activities', methods=['GET'])
@login_required
def get_suspicious_activities():
    """Get suspicious activities"""
    if current_user.role != 'admin':
        activities = SuspiciousActivity.query.filter_by(user_id=current_user.id).order_by(
            SuspiciousActivity.created_at.desc()
        ).limit(20).all()
    else:
        activities = SuspiciousActivity.query.order_by(
            SuspiciousActivity.created_at.desc()
        ).limit(100).all()

    return jsonify({
        'activities': [{
            'id': a.id,
            'activity_name': a.activity_name,
            'severity': a.severity,
            'description': a.description,
            'risk_score': a.risk_score,
            'country': a.country,
            'is_reviewed': a.is_reviewed,
            'is_threat': a.is_threat,
            'created_at': a.created_at.isoformat()
        } for a in activities]
    })


@admin_bp.route('/api/admin/suspicious-activities/<int:activity_id>/review', methods=['POST'])
@admin_required
def review_suspicious_activity(activity_id):
    """Admin: Review suspicious activity"""
    activity = SuspiciousActivity.query.get(activity_id)
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404

    data = request.get_json() or {}
    activity.is_reviewed = True
    activity.is_threat = data.get('is_threat', False)
    activity.reviewed_by = current_user.id
    activity.review_notes = data.get('notes', '')
    activity.reviewed_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': 'Activity reviewed'})


@admin_bp.route('/api/security-questions', methods=['GET', 'POST'])
@login_required
def manage_security_questions():
    """Manage security questions"""
    if request.method == 'GET':
        questions = SecurityQuestion.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'questions': [{
                'id': q.id,
                'question': q.question,
                'created_at': q.created_at.isoformat()
            } for q in questions]
        })

    if request.method == 'POST':
        data = request.get_json() or {}
        question = SecurityQuestion(
            user_id=current_user.id,
            question=data.get('question')
        )
        question.set_answer(data.get('answer'))

        db.session.add(question)
        db.session.commit()

        return jsonify({'message': 'Security question added', 'id': question.id})


# ─── Audit Log Viewer & Export ───

@admin_bp.route('/admin/audit-logs', methods=['GET'])
@admin_required
def admin_audit_logs_page():
    """Render admin audit log viewer template"""
    return render_template('admin_audit_logs.html')


@admin_bp.route('/api/admin/audit-logs', methods=['GET'])
@admin_required
def get_admin_audit_logs():
    """Paginated & Filtered API for Audit Logs."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    event_type = request.args.get('event_type', '').strip()
    status = request.args.get('status', '').strip()
    user_id_param = request.args.get('user_id', type=int)
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    search = request.args.get('search', '').strip()

    query = AuditLog.query

    if event_type and event_type != 'all':
        query = query.filter(or_(AuditLog.event_type == event_type, AuditLog.action == event_type))

    if status and status != 'all':
        query = query.filter_by(status=status)

    if user_id_param:
        query = query.filter_by(user_id=user_id_param)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_date)
        except ValueError:
            pass

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.ip_address.ilike(search_pattern),
                AuditLog.target_resource.ilike(search_pattern),
                AuditLog.event_type.ilike(search_pattern),
                AuditLog.action.ilike(search_pattern),
                AuditLog.user_agent.ilike(search_pattern)
            )
        )

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    total_count = AuditLog.query.count()
    failed_logins = AuditLog.query.filter(
        or_(AuditLog.event_type == 'failed_login', AuditLog.action == 'failed_login')
    ).count()
    fraud_detections = AuditLog.query.filter(
        or_(AuditLog.event_type == 'fraud_detection', AuditLog.action == 'fraud_detection')
    ).count()
    auth_failures = AuditLog.query.filter(
        or_(AuditLog.event_type == 'api_auth_failure', AuditLog.action == 'api_auth_failure')
    ).count()

    return jsonify({
        'logs': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': pagination.per_page,
        'stats': {
            'total': total_count,
            'failed_logins': failed_logins,
            'fraud_detections': fraud_detections,
            'auth_failures': auth_failures
        }
    })


@admin_bp.route('/api/admin/audit-logs/export', methods=['GET'])
@admin_required
def export_admin_audit_logs():
    """Export filtered audit logs as CSV or JSON"""
    export_format = request.args.get('format', 'csv').lower()
    event_type = request.args.get('event_type', '').strip()
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    query = AuditLog.query

    if event_type and event_type != 'all':
        query = query.filter(or_(AuditLog.event_type == event_type, AuditLog.action == event_type))
    if status and status != 'all':
        query = query.filter_by(status=status)
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_date)
        except ValueError:
            pass
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.ip_address.ilike(search_pattern),
                AuditLog.target_resource.ilike(search_pattern),
                AuditLog.event_type.ilike(search_pattern)
            )
        )

    logs = query.order_by(AuditLog.created_at.desc()).limit(1000).all()

    if export_format == 'json':
        return jsonify([l.to_dict() for l in logs])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Event ID', 'Event Type', 'User ID', 'Target Resource', 'IP Address', 'User Agent', 'Status', 'Timestamp', 'Details'])

    for l in logs:
        d = l.to_dict()
        writer.writerow([
            d['event_id'],
            d['event_type'],
            d['user_id'] or 'Anonymous',
            d['target_resource'],
            d['ip_address'],
            d['user_agent'],
            d['status'],
            d['created_at'],
            json.dumps(d['details'])
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=audit_logs_export.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


@admin_bp.route('/api/login-attempts', methods=['GET'])
@admin_required
def get_login_attempts():
    """Get recent login attempts for security auditing"""
    attempts = LoginAttempt.query.order_by(LoginAttempt.created_at.desc()).limit(50).all()
    return jsonify({
        'attempts': [{
            'id': a.id,
            'username': a.username,
            'ip_address': a.ip_address,
            'success': a.success,
            'failure_reason': a.failure_reason,
            'country': a.country,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in attempts]
    })


@admin_bp.route('/api/sessions', methods=['GET'])
@admin_required
def get_active_sessions():
    """Get active user sessions"""
    sessions = UserSession.query.filter_by(is_active=True).order_by(UserSession.last_activity.desc()).all()
    return jsonify({
        'sessions': [{
            'id': s.id,
            'user_id': s.user_id,
            'ip_address': s.ip_address,
            'user_agent': s.user_agent,
            'last_activity': s.last_activity.isoformat() if s.last_activity else None,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in sessions]
    })


@admin_bp.route('/api/sessions/<int:session_id>/revoke', methods=['POST'])
@admin_required
def revoke_session(session_id):
    """Revoke specific user session"""
    user_session = UserSession.query.get(session_id)
    if not user_session:
        return jsonify({'error': 'Session not found'}), 404

    user_session.is_active = False
    db.session.commit()
    return jsonify({'message': 'Session revoked successfully'})


@admin_bp.route('/api/trusted-ips', methods=['GET', 'POST'])
@admin_required
def manage_trusted_ips():
    """Manage trusted IP list"""
    if request.method == 'GET':
        ips = IPAddress.query.all()
        return jsonify({
            'ips': [{
                'id': i.id,
                'ip_address': i.ip_address,
                'country': i.country,
                'is_vpn': i.is_vpn,
                'risk_score': i.risk_score
            } for i in ips]
        })

    if request.method == 'POST':
        data = request.get_json() or {}
        ip_addr = data.get('ip_address')
        ip_rec = IPAddress.query.filter_by(ip_address=ip_addr).first()
        if not ip_rec:
            ip_rec = IPAddress(ip_address=ip_addr)
            db.session.add(ip_rec)
        ip_rec.risk_score = 0.0
        db.session.commit()
        return jsonify({'message': 'IP updated successfully'})


@admin_bp.route('/api/activity-log', methods=['GET'])
@admin_required
def get_activity_log():
    """Get system user activity log"""
    activities = UserActivity.query.order_by(UserActivity.created_at.desc()).limit(100).all()
    return jsonify({
        'activities': [{
            'id': a.id,
            'user_id': a.user_id,
            'activity_type': a.activity_type,
            'description': a.action_description,
            'ip_address': a.ip_address,
            'status': a.status,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in activities]
    })
