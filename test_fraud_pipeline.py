"""
Comprehensive Test Suite for ML Fraud Detection Pipeline.
Validates model versioning, prediction probability, explainable risk factors,
rule score vs ML score comparison, combined risk scoring, and test cases
for low-, medium-, and high-risk transactions.
"""

import unittest
import json
import numpy as np
from app import app, fraud_engine, sanitize_numpy_types
from preprocessor import TransactionPreprocessor

class TestFraudDetectionPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_preprocessor_deterministic_transform(self):
        """Verify that TransactionPreprocessor generates deterministic features without random numbers."""
        txn = {
            'amount': 150.00,
            'merchant': 'Apple Store',
            'category': 'Electronics',
            'location': 'New York, USA',
            'device_type': 'Desktop Chrome'
        }
        prep = TransactionPreprocessor()
        df1 = prep.transform_dict(txn)
        df2 = prep.transform_dict(txn)
        
        # Exact equality check
        np.testing.assert_array_equal(df1.values, df2.values)
        self.assertEqual(list(df1.columns), prep.feature_names)
        self.assertFalse(df1.isna().any().any())

    def test_low_risk_transaction(self):
        """Test routine low-risk transaction."""
        txn = {
            'card_number': '4000123456781111',
            'card_holder': 'Alice LowRisk',
            'amount': 25.50,
            'merchant': 'Corner Grocery',
            'category': 'Groceries',
            'location': 'New York, USA',
            'device_type': 'Desktop Chrome'
        }
        res = fraud_engine.analyze_transaction(txn)
        
        self.assertLess(res['fraud_score'], 40.0)
        self.assertFalse(res['is_fraud'])
        self.assertEqual(res['risk_level'], 'low')
        self.assertIn('model_version', res)
        self.assertIn('ml_probability', res)
        self.assertIn('ml_score', res)
        self.assertIn('rule_score', res)
        self.assertIn('score_difference', res)
        self.assertIn('primary_driver', res)

    def test_medium_risk_transaction(self):
        """Test medium-risk transaction with above average amount ($5,500) and elevated category/device risk."""
        txn = {
            'card_number': '4000123456782222',
            'card_holder': 'Bob MedRisk',
            'amount': 5500.00,
            'merchant': 'Tech MegaStore',
            'category': 'Electronics',
            'location': 'Chicago, USA',
            'device_type': 'Unknown'
        }
        res = fraud_engine.analyze_transaction(txn)
        
        self.assertGreaterEqual(res['fraud_score'], 40.0)
        self.assertIn(res['risk_level'], ['medium', 'high'])
        self.assertGreater(len(res['risk_factors']), 0)
        self.assertIsInstance(res['ml_probability'], float)

    def test_high_risk_transaction(self):
        """Test high-risk transaction (extreme amount, crypto category, high-risk country, VPN, unusual hour)."""
        txn = {
            'card_number': '4000123456783333',
            'card_holder': 'Charlie HighRisk',
            'amount': 15000.00,
            'merchant': 'Crypto Exchanger',
            'category': 'Cryptocurrency',
            'location': 'Lagos, Nigeria',
            'device_type': 'VPN',
            'timestamp': '2026-08-15T02:30:00Z'
        }
        res = fraud_engine.analyze_transaction(txn)
        
        self.assertGreaterEqual(res['fraud_score'], 65.0)
        self.assertTrue(res['is_fraud'])
        self.assertIn(res['risk_level'], ['high', 'critical'])
        self.assertGreater(res['rule_score'], 60.0)
        self.assertGreater(len(res['risk_factors']), 2)

    def test_simulation_benchmark_transaction(self):
        """Test transaction payload with explicit V1..V28 features."""
        txn = {
            'amount': 500.0,
            'merchant': 'Benchmark Store',
            'category': 'General',
            'location': 'USA',
            'V1': -3.5, 'V2': 3.2, 'V3': -4.1, 'V4': 4.0, 'V14': -7.2, 'V17': -5.5
        }
        # Add remaining V features
        for i in range(1, 29):
            k = f'V{i}'
            if k not in txn:
                txn[k] = 0.0

        res = fraud_engine.analyze_transaction(txn)
        self.assertIn('fraud_score', res)
        self.assertIn('ml_probability', res)
        self.assertEqual(res['model_version'], 'v2.0.0')

    def test_api_endpoint_integration(self):
        """Test Flask POST endpoint /api/transactions/process with new metadata fields."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'

        txn = {
            'card_number': '4000123456784444',
            'card_holder': 'Test API User',
            'amount': 120.00,
            'merchant': 'Department Store',
            'category': 'General',
            'location': 'Boston, USA',
            'device_type': 'Mobile iOS'
        }
        response = self.client.post('/api/transactions/process', json=txn)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['status'], 'approved')
        self.assertIn('model_version', data)
        self.assertIn('ml_probability', data)
        self.assertIn('ml_score', data)
        self.assertIn('rule_score', data)
        self.assertIn('score_difference', data)
        self.assertIn('primary_driver', data)

if __name__ == '__main__':
    unittest.main()
