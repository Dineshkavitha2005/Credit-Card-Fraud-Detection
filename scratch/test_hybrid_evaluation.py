import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import joblib
import json
import pandas as pd
import numpy as np
from app.services.fraud_detection import FraudDetectionEngine
from preprocessor import TransactionPreprocessor

def test_hybrid():
    engine = FraudDetectionEngine()
    print(f"Engine loaded model version: {engine.model_version}")

    test_cases = [
        ("Low Risk Grocery", {
            'card_number': '4000123456781111',
            'card_holder': 'Alice LowRisk',
            'amount': 25.50,
            'merchant': 'Corner Grocery',
            'category': 'Groceries',
            'location': 'New York, USA',
            'device_type': 'Desktop Chrome'
        }),
        ("Medium Risk Electronics", {
            'card_number': '4000123456782222',
            'card_holder': 'Bob MedRisk',
            'amount': 5500.00,
            'merchant': 'Tech MegaStore',
            'category': 'Electronics',
            'location': 'Chicago, USA',
            'device_type': 'Unknown'
        }),
        ("High Risk Crypto VPN", {
            'card_number': '4000123456783333',
            'card_holder': 'Charlie HighRisk',
            'amount': 15000.00,
            'merchant': 'Crypto Exchanger',
            'category': 'Cryptocurrency',
            'location': 'Lagos, Nigeria',
            'device_type': 'VPN',
            'timestamp': '2026-08-15T02:30:00Z'
        }),
        ("Simulation Benchmark with V features", {
            'amount': 500.0,
            'merchant': 'Benchmark Store',
            'category': 'General',
            'location': 'USA',
            'V1': -3.5, 'V2': 3.2, 'V3': -4.1, 'V4': 4.0, 'V14': -7.2, 'V17': -5.5,
            **{f'V{i}': 0.0 for i in range(1, 29) if f'V{i}' not in ['V1', 'V2', 'V3', 'V4', 'V14', 'V17']}
        })
    ]

    for name, txn in test_cases:
        res = engine.analyze_transaction(txn)
        print(f"\n--- {name} ---")
        print(f"  Fraud Score: {res['fraud_score']} | Risk Level: {res['risk_level']} | Is Fraud: {res['is_fraud']}")
        print(f"  ML Score: {res['ml_score']} (Prob: {res['ml_probability']}) | Rule Score: {res['rule_score']}")
        print(f"  Primary Driver: {res['primary_driver']} | Diff: {res['score_difference']}")
        print(f"  Risk Factors: {res['risk_factors']}")

if __name__ == '__main__':
    test_hybrid()
