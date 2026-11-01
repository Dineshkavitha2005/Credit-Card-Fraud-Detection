from datetime import datetime
from app.extensions import db

class Alert(db.Model):
    """Fraud alert"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), db.ForeignKey('transactions.transaction_id'))
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # Critical, High, Medium, Low
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Alert {self.alert_type}>'


class SuspiciousActivity(db.Model):
    """Log suspicious activities for analysis"""
    __tablename__ = 'suspicious_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    country = db.Column(db.String(100))
    risk_score = db.Column(db.Float, default=0.0)
    data = db.Column(db.JSON, default={})
    is_reviewed = db.Column(db.Boolean, default=False)
    is_threat = db.Column(db.Boolean, default=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<SuspiciousActivity {self.activity_name}>'
