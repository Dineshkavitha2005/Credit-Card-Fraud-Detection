from datetime import datetime, timedelta
from app.extensions import db

class Report(db.Model):
    """Generated reports (CSV, PDF) for export"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    file_format = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    filters = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    download_count = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Report {self.report_type} by {self.user_id}>'
