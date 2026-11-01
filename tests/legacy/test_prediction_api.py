#!/usr/bin/env python
"""
Automated Test Suite for Credit Card Fraud Detection Engine & API Endpoint
Verifies NumPy serialization, response structure, error handling, and scoring logic across 5 key scenarios.
"""

import sys
import json
import numpy as np

# Import Flask app and components
from app import app, fraud_engine, sanitize_numpy_types, get_db

def assert_native_python_types(data, path="root"):
    """Assert that no NumPy data types exist in data recursively."""
    if isinstance(data, (np.bool_, np.integer, np.floating, np.ndarray)):
        raise TypeError(f"Found NumPy data type at '{path}': {type(data)} with value {data}")
    elif isinstance(data, dict):
        for k, v in data.items():
            assert_native_python_types(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, elem in enumerate(data):
            assert_native_python_types(elem, f"{path}[{i}]")

def run_engine_direct_test():
    print("==================================================")
    print("🔬 TEST 1: Direct FraudDetectionEngine Analysis")
    print("==================================================")
    
    sample_txn = {
        'card_number': '4532123456789012',
        'card_holder': 'Alice Smith',
        'amount': 250.50,
        'merchant': 'Amazon Shopping',
        'category': 'Electronics',
        'location': 'New York, USA',
        'device_type': 'iPhone iOS'
    }
    
    result = fraud_engine.analyze_transaction(sample_txn)
    print("Direct analysis result:")
    print(json.dumps(result, indent=2))
    
    # Assert type checks
    assert isinstance(result['fraud_score'], float), f"fraud_score is type {type(result['fraud_score'])}"
    assert isinstance(result['is_fraud'], bool), f"is_fraud is type {type(result['is_fraud'])}"
    assert isinstance(result['risk_level'], str), f"risk_level is type {type(result['risk_level'])}"
    assert isinstance(result['risk_factors'], list), f"risk_factors is type {type(result['risk_factors'])}"
    assert isinstance(result['component_scores'], dict), f"component_scores is type {type(result['component_scores'])}"
    
    assert_native_python_types(result, "engine_result")
    
    # Test json.dumps serialization explicitly
    serialized = json.dumps(result)
    print("✅ json.dumps(result) succeeded without serialization error!")
    print("\n")

def run_flask_api_tests():
    print("==================================================")
    print("🌐 TEST 2: Flask API Endpoint (/api/transactions/process)")
    print("==================================================")
    
    client = app.test_client()
    
    # Create test context with logged-in user in session for Flask-Login
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'

    # Scenario 1: Genuine Transaction
    print("\n🔹 Scenario 1: Genuine Transaction")
    genuine_txn = {
        'card_number': '4000123456789999',
        'card_holder': 'John Doe',
        'amount': 45.00,
        'merchant': 'Grocery Market',
        'category': 'Groceries',
        'location': 'New York, USA',
        'device_type': 'Desktop Chrome'
    }
    res1 = client.post('/api/transactions/process', json=genuine_txn)
    print(f"Status Code: {res1.status_code}")
    data1 = res1.get_json()
    print("Response payload:", json.dumps(data1, indent=2))
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    assert data1['status'] == 'approved', f"Expected approved, got {data1['status']}"
    assert data1['is_fraud'] is False, "Expected is_fraud False"
    assert_native_python_types(data1, "scenario_1")
    print("✅ Scenario 1 passed!")

    # Scenario 2: Suspicious Transaction
    print("\n🔹 Scenario 2: Suspicious Transaction")
    suspicious_txn = {
        'card_number': '4000123456788888',
        'card_holder': 'Jane Doe',
        'amount': 12000.00,
        'merchant': 'Crypto Exchange',
        'category': 'Cryptocurrency',
        'location': 'Lagos, Nigeria',
        'device_type': 'VPN',
        'V1': -5.0, 'V2': 4.5, 'V3': -6.0, 'V4': 5.5, 'V14': -9.0, 'V17': -7.0
    }
    res2 = client.post('/api/transactions/process', json=suspicious_txn)
    print(f"Status Code: {res2.status_code}")
    data2 = res2.get_json()
    print("Response payload:", json.dumps(data2, indent=2))
    assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
    assert data2['is_fraud'] is True or data2['fraud_score'] >= 40, "Expected fraud detection / high risk score"
    assert_native_python_types(data2, "scenario_2")
    print("✅ Scenario 2 passed!")

    # Scenario 3: Invalid Transaction (Invalid amount format & negative amount)
    print("\n🔹 Scenario 3: Invalid Transaction")
    invalid_txn_str = {
        'card_number': '4000123456787777',
        'card_holder': 'Test User',
        'amount': 'invalid_amount_abc',
        'merchant': 'Test Merchant',
        'category': 'General',
        'location': 'New York, USA'
    }
    res3a = client.post('/api/transactions/process', json=invalid_txn_str)
    print(f"Status Code (string amount): {res3a.status_code}")
    data3a = res3a.get_json()
    print("Response payload:", json.dumps(data3a, indent=2))
    assert res3a.status_code == 400, f"Expected 400, got {res3a.status_code}"
    assert 'error' in data3a, "Expected error message in response"

    invalid_txn_neg = {
        'card_number': '4000123456787777',
        'card_holder': 'Test User',
        'amount': -150.00,
        'merchant': 'Test Merchant',
        'category': 'General',
        'location': 'New York, USA'
    }
    res3b = client.post('/api/transactions/process', json=invalid_txn_neg)
    print(f"Status Code (negative amount): {res3b.status_code}")
    data3b = res3b.get_json()
    print("Response payload:", json.dumps(data3b, indent=2))
    assert res3b.status_code == 400, f"Expected 400, got {res3b.status_code}"
    assert 'error' in data3b, "Expected error message in response"
    assert_native_python_types(data3a, "scenario_3a")
    assert_native_python_types(data3b, "scenario_3b")
    print("✅ Scenario 3 passed!")

    # Scenario 4: Missing Fields
    print("\n🔹 Scenario 4: Missing Fields")
    missing_fields_txn = {
        'card_holder': 'Bob Jones',
        'merchant': 'Coffee Shop',
        'location': 'Boston, USA'
    }
    res4 = client.post('/api/transactions/process', json=missing_fields_txn)
    print(f"Status Code: {res4.status_code}")
    data4 = res4.get_json()
    print("Response payload:", json.dumps(data4, indent=2))
    assert res4.status_code == 400, f"Expected 400, got {res4.status_code}"
    assert 'error' in data4, "Expected error message"
    assert 'card_number' in data4['error'] or 'amount' in data4['error']
    assert_native_python_types(data4, "scenario_4")
    print("✅ Scenario 4 passed!")

    # Scenario 5: Extreme Transaction Amount
    print("\n🔹 Scenario 5: Extreme Transaction Amount")
    extreme_txn = {
        'card_number': '4000123456786666',
        'card_holder': 'Rich VIP',
        'amount': 250000.00,
        'merchant': 'Luxury Yacht Dealership',
        'category': 'Electronics',
        'location': 'Miami, USA',
        'device_type': 'Desktop Safari'
    }
    res5 = client.post('/api/transactions/process', json=extreme_txn)
    print(f"Status Code: {res5.status_code}")
    data5 = res5.get_json()
    print("Response payload:", json.dumps(data5, indent=2))
    assert res5.status_code == 200, f"Expected 200, got {res5.status_code}"
    assert isinstance(data5['fraud_score'], float) and data5['fraud_score'] >= 0, "Expected valid float fraud score"
    assert any("amount" in rf.lower() or "high" in rf.lower() for rf in data5['risk_factors']), "Expected risk factor for extreme amount"
    assert_native_python_types(data5, "scenario_5")
    print("✅ Scenario 5 passed!")

test_engine_direct_analysis = run_engine_direct_test
test_flask_api_predictions = run_flask_api_tests

if __name__ == '__main__':
    run_engine_direct_test()
    run_flask_api_tests()
    print("\n" + "="*50)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY WITH NO NUMPY SERIALIZATION ERRORS!")
    print("="*50 + "\n")
