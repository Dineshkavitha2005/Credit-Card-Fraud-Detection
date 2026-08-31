import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import joblib
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from train_model import prepare_training_dataset
from scratch.cv_and_test_evaluation import UnifiedPreprocessor

def test_new_hybrid():
    df = pd.read_csv('creditcard_2023.csv', nrows=100000)
    df_domain = prepare_training_dataset(df)
    preprocessor = UnifiedPreprocessor()
    X = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_dev_scaled = scaler.fit_transform(X_dev)
    
    # Selected best model from 5-fold CV
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight={0: 1, 1: 30},
        random_state=42,
        n_jobs=2
    )
    model.fit(X_dev_scaled, y_dev)

    # Let's test the preprocessor and model on transactions
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
            'timestamp': '2026-08-15T02:30:00Z',
            'velocity_score': 0.9
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
        feat_df = preprocessor.transform_dict(txn)
        scaled = scaler.transform(feat_df[preprocessor.feature_names])
        prob = model.predict_proba(scaled)[0, 1]
        print(f"\n--- {name} ---")
        print(f"  Features:\n{feat_df.to_dict(orient='records')[0]}")
        print(f"  ML Probability: {prob:.4f} ({prob*100:.2f}%)")

if __name__ == '__main__':
    test_new_hybrid()
