import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import os
import json
import joblib
import numpy as np
from datetime import datetime, timedelta
from preprocessor import TransactionPreprocessor
from app.models.encryption import mask_card_number

def sanitize_numpy_types(obj):
    """Recursively convert NumPy data types into native Python types for JSON serialization."""
    if obj is None:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [sanitize_numpy_types(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): sanitize_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_numpy_types(x) for x in obj]
    return obj


class FraudDetectionEngine:
    """ML-powered fraud detection engine with deterministic feature engineering, scoring, and explainability"""

    def __init__(self):
        self.weights = {
            'amount_score': 0.25,
            'velocity_score': 0.20,
            'geo_score': 0.15,
            'time_score': 0.10,
            'device_score': 0.10,
            'pattern_score': 0.20,
        }
        self.high_risk_countries = ['Nigeria', 'Russia', 'China', 'Romania', 'Brazil']
        self.high_risk_categories = ['Electronics', 'Gift Cards', 'Cryptocurrency', 'Wire Transfer']
        
        # Preprocessor instance
        self.preprocessor = TransactionPreprocessor.load_config('preprocessing_config.json')

        # Load ML model artifacts
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_version = 'v2.1.0'
        self.model_metadata = {}
        self.classification_threshold = 0.25
        
        try:
            if os.path.exists('fraud_model.pkl') and os.path.exists('scaler.pkl'):
                self.model = joblib.load('fraud_model.pkl')
                self.scaler = joblib.load('scaler.pkl')
                if os.path.exists('features.pkl'):
                    self.feature_names = joblib.load('features.pkl')
                else:
                    self.feature_names = self.preprocessor.feature_names
                
                if os.path.exists('model_metadata.json'):
                    with open('model_metadata.json', 'r') as f:
                        self.model_metadata = json.load(f)
                        self.model_version = self.model_metadata.get('model_version', 'v2.1.0')
                        self.classification_threshold = float(self.model_metadata.get('classification_threshold', 0.25))

                print("✅ Machine Learning model v{} loaded successfully (threshold: {})".format(self.model_version, self.classification_threshold))
        except Exception as e:
            print("⚠️ Error loading ML model: {}".format(e))

    def analyze_transaction(self, transaction):
        """Analyze a transaction and return combined risk score, ML prob, rule score, and explainable risk factors."""
        risk_factors = []
        scores = {}
        
        # Create a working copy and populate velocity score if missing
        txn_copy = dict(transaction)
        if 'velocity_score' not in txn_copy:
            txn_copy['velocity_score'] = float(self._check_velocity(txn_copy))

        # ─── 1. ML Model Scoring (Deterministic Preprocessing) ───
        ml_score = 0.0
        ml_prob = 0.0
        if self.model and self.scaler:
            try:
                features_df = self.preprocessor.transform_dict(txn_copy)
                target_features = self.feature_names or self.preprocessor.feature_names
                features_aligned = features_df[target_features]
                features_scaled = self.scaler.transform(features_aligned)
                
                probabilities = self.model.predict_proba(features_scaled)
                if len(probabilities) > 0 and len(probabilities[0]) > 1:
                    ml_prob = float(probabilities[0][1])
                    ml_score = float(ml_prob * 100.0)
                
                if ml_prob >= self.classification_threshold or ml_score >= 65.0:
                    risk_factors.append('ML Engine detects pattern deviation (Probability: {:.1f}%)'.format(ml_prob * 100.0))
            except Exception as e:
                print("ML Scoring Error: {}".format(e))
                ml_score = 0.0
                ml_prob = 0.0

        # ─── 2. Rule-Based Checks ───
        try:
            amount = float(transaction.get('amount', transaction.get('Amount', 0)))
        except (ValueError, TypeError):
            amount = 0.0

        if amount > 10000:
            scores['amount_score'] = 1.0
            risk_factors.append('Extremely high transaction amount (>${:,.0f})'.format(amount))
        elif amount > 5000:
            scores['amount_score'] = 0.8
            risk_factors.append('High transaction amount (>${:,.0f})'.format(amount))
        elif amount > 2000:
            scores['amount_score'] = 0.5
            risk_factors.append('Above average transaction amount')
        else:
            scores['amount_score'] = float(max(0.0, amount / 5000.0))

        # Velocity Check
        scores['velocity_score'] = float(self._check_velocity(transaction))
        if scores['velocity_score'] > 0.5:
            risk_factors.append('Multiple transactions in short time period')

        # Geographic Analysis
        location = str(transaction.get('location', ''))
        if any(country.lower() in location.lower() for country in self.high_risk_countries):
            scores['geo_score'] = 0.9
            risk_factors.append('Transaction from high-risk location: {}'.format(location))
        else:
            scores['geo_score'] = 0.1

        # Time Analysis
        try:
            timestamp = transaction.get('timestamp')
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
            else:
                hour = datetime.now().hour

            if 0 <= hour <= 5:
                scores['time_score'] = 0.7
                risk_factors.append('Transaction during unusual hours (12AM-5AM)')
            else:
                scores['time_score'] = 0.1
        except Exception:
            scores['time_score'] = 0.1

        # Device Analysis
        device = str(transaction.get('device_type', 'unknown'))
        if any(d in device.lower() for d in ['vpn', 'tor', 'unknown']):
            scores['device_score'] = 0.8
            risk_factors.append('Suspicious device or connection type: {}'.format(device))
        else:
            scores['device_score'] = 0.1

        # Merchant Category Analysis
        category = str(transaction.get('category', ''))
        if any(c.lower() in category.lower() for c in self.high_risk_categories):
            scores['pattern_score'] = 0.7
            risk_factors.append('High-risk merchant category: {}'.format(category))
        else:
            scores['pattern_score'] = 0.15

        # Weighted Rule Score
        rule_score = sum(
            float(scores.get(key, 0.0)) * float(weight)
            for key, weight in self.weights.items()
        ) * 100.0

        # ─── 3. Model Score vs. Rule Score Comparison ───
        score_difference = round(float(ml_score) - float(rule_score), 2)
        if abs(score_difference) <= 15.0:
            primary_driver = 'concurrence'
        elif ml_score > rule_score:
            primary_driver = 'ml_engine'
        else:
            primary_driver = 'rule_engine'

        # ─── 4. Combined Risk Score & Decision ───
        if self.model:
            blend_score = (float(ml_score) * 0.50) + (float(rule_score) * 0.50)
            combined_score = max(blend_score, max(ml_score, rule_score))
        else:
            combined_score = float(rule_score)

        fraud_score = float(min(round(float(combined_score), 2), 100.0))

        raw_result = {
            'fraud_score': float(fraud_score),
            'is_fraud': bool(fraud_score >= 65.0),
            'risk_level': str(self._get_risk_level(fraud_score)),
            'ml_score': float(round(ml_score, 2)),
            'rule_score': float(round(rule_score, 2)),
            'ml_probability': float(round(ml_prob, 4)),
            'model_version': str(self.model_version),
            'score_difference': float(score_difference),
            'primary_driver': str(primary_driver),
            'risk_factors': [str(rf) for rf in risk_factors],
            'component_scores': {str(k): float(v) for k, v in scores.items()}
        }

        return sanitize_numpy_types(raw_result)

    def _check_velocity(self, transaction):
        """Check transaction velocity for the card across SQLite and PostgreSQL"""
        try:
            raw_card = transaction.get('card_number', '')
            masked_card = mask_card_number(raw_card)
            five_min_ago = datetime.utcnow() - timedelta(minutes=5)
            
            from app.extensions import db
            from app.models.transaction import Transaction
            from flask import current_app

            def _query_count():
                return Transaction.query.filter(
                    (Transaction.card_number == masked_card) | (Transaction.card_number == raw_card),
                    Transaction.timestamp >= five_min_ago
                ).count()

            if current_app:
                count = _query_count()
            else:
                from app import app
                with app.app_context():
                    count = _query_count()

            return min(count / 5.0, 1.0)
        except Exception:
            return 0.2

    def _get_risk_level(self, score):
        if score >= 80:
            return 'critical'
        elif score >= 65:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'


fraud_engine = FraudDetectionEngine()
