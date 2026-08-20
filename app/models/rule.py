from datetime import datetime
from app.extensions import db

class FraudRule(db.Model):
    """Configurable fraud detection rules"""
    __tablename__ = 'fraud_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(120), nullable=False)
    rule_type = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FraudRule {self.rule_name}>'
