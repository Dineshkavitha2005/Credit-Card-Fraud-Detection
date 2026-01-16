from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Merchant(db.Model):
    __tablename__ = 'merchants'
    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, unique=True, nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    merchant_id = db.Column(db.String(50), db.ForeignKey('merchants.merchant_id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    is_fraud = db.Column(db.Boolean, nullable=False)
    fraud_status = db.Column(db.String(50), default='No Fraud')

class FraudLog(db.Model):
    __tablename__ = 'fraud_logs'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.transaction_id'), nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)
