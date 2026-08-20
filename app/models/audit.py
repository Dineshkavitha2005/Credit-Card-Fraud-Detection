from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    """Security audit log for tracking user actions and system events"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=True, index=True)
    target_resource = db.Column(db.String(255), nullable=True, index=True)
    resource = db.Column(db.String(100), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='success', index=True)
    details = db.Column(db.JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __init__(self, **kwargs):
        if 'event_type' in kwargs and 'action' not in kwargs:
            kwargs['action'] = kwargs['event_type']
        elif 'action' in kwargs and 'event_type' not in kwargs:
            kwargs['event_type'] = kwargs['action']
            
        if 'target_resource' in kwargs and 'resource' not in kwargs:
            kwargs['resource'] = kwargs['target_resource'][:100] if kwargs['target_resource'] else None
        elif 'resource' in kwargs and 'target_resource' not in kwargs:
            kwargs['target_resource'] = kwargs['resource']
            
        super().__init__(**kwargs)

    @property
    def event_id(self):
        return f"AUD-{self.id:06d}" if self.id else "AUD-000000"

    @property
    def timestamp(self):
        return self.created_at

    @property
    def get_event_type(self):
        return self.event_type or self.action or "unknown"

    @property
    def get_target_resource(self):
        return self.target_resource or self.resource or "n/a"

    @property
    def is_success(self):
        return self.status == 'success'

    def to_dict(self):
        """Serialize audit log to dictionary for API responses"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'event_type': self.get_event_type,
            'action': self.action or self.event_type,
            'target_resource': self.get_target_resource,
            'resource': self.resource or self.target_resource,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'success': self.is_success,
            'details': self.details or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'timestamp': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<AuditLog {self.get_event_type} - {self.status}>'


class AdminAction(db.Model):
    """Track administrative actions for compliance"""
    __tablename__ = 'admin_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    target_resource = db.Column(db.String(255))
    reason = db.Column(db.Text)
    details = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default='executed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AdminAction {self.action_type} by {self.admin_id}>'


class RateLimitRecord(db.Model):
    """Track API rate limiting per user/IP"""
    __tablename__ = 'rate_limit_records'
    
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(255), nullable=False, index=True)
    endpoint = db.Column(db.String(255), nullable=False)
    request_count = db.Column(db.Integer, default=0)
    first_request = db.Column(db.DateTime, default=datetime.utcnow)
    last_request = db.Column(db.DateTime, default=datetime.utcnow)
    is_limited = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<RateLimitRecord {self.identifier}>'
