from datetime import datetime
from app.extensions import db

class Transaction(db.Model):
    """Transaction record"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    transaction_id = db.Column(db.String(100), unique=True, index=True)
    card_number = db.Column(db.String(255))
    card_holder = db.Column(db.String(120))
    amount = db.Column(db.Float, nullable=False)
    merchant = db.Column(db.String(120))
    category = db.Column(db.String(50))
    location = db.Column(db.String(120))
    ip_address = db.Column(db.String(50))
    device_type = db.Column(db.String(50))
    is_fraud = db.Column(db.Boolean, default=False, index=True)
    fraud_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending', index=True)
    risk_factors = db.Column(db.JSON, default=[])
    reviewed_by = db.Column(db.String(80))
    reviewed_at = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}>'


class BlockedCard(db.Model):
    """Blocked cards for fraud prevention"""
    __tablename__ = 'blocked_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(255), unique=True, nullable=False)
    reason = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    blocked_by = db.Column(db.String(80))
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        from app.models.encryption import mask_card_number
        return f'<BlockedCard {mask_card_number(self.card_number)}>'
