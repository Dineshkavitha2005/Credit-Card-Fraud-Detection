import os
import pytest
import numpy as np
from app.services.fraud_detection import FraudDetectionEngine, sanitize_numpy_types
from preprocessor import TransactionPreprocessor

class TestMachineLearning:
    """Test suite for ML model loading, preprocessing, scoring, and output typing."""

    def test_preprocessor_loading_and_config(self):
        """Test preprocessor initializes and loads configuration properly."""
        preprocessor = TransactionPreprocessor.load_config('preprocessing_config.json')
        assert preprocessor is not None
        assert hasattr(preprocessor, 'feature_names')
        assert len(preprocessor.feature_names) > 0

    def test_preprocessor_transformation(self, sample_genuine_transaction):
        """Test transforming a transaction dictionary produces a valid feature DataFrame."""
        preprocessor = TransactionPreprocessor.load_config('preprocessing_config.json')
        df = preprocessor.transform_dict(sample_genuine_transaction)

        assert df is not None
        assert len(df) == 1
        for col in preprocessor.feature_names:
            assert col in df.columns
            # Ensure no nulls in generated features
            assert not df[col].isnull().any()

    def test_ml_model_artifacts_loading(self):
        """Test FraudDetectionEngine loads ML model artifacts and scaler."""
        engine = FraudDetectionEngine()
        # Model should be loaded if artifact files exist
        if os.path.exists('fraud_model.pkl') and os.path.exists('scaler.pkl'):
            assert engine.model is not None
            assert engine.scaler is not None
            assert engine.feature_names is not None
            assert isinstance(engine.model_version, str)

    def test_prediction_pipeline_genuine(self, sample_genuine_transaction):
        """Test analyzing a genuine transaction with FraudDetectionEngine."""
        engine = FraudDetectionEngine()
        result = engine.analyze_transaction(sample_genuine_transaction)

        assert isinstance(result, dict)
        assert 'fraud_score' in result
        assert 'is_fraud' in result
        assert 'risk_level' in result
        assert 'risk_factors' in result
        assert 'ml_score' in result
        assert 'rule_score' in result

        assert result['fraud_score'] >= 0.0
        assert result['fraud_score'] <= 100.0
        assert isinstance(result['is_fraud'], bool)
        assert result['risk_level'].lower() in ['low', 'medium', 'high', 'critical']

    def test_prediction_pipeline_fraud(self, sample_fraud_transaction):
        """Test analyzing a fraudulent transaction triggers high risk score."""
        engine = FraudDetectionEngine()
        result = engine.analyze_transaction(sample_fraud_transaction)

        assert result['fraud_score'] >= 40.0
        assert result['risk_level'].lower() in ['high', 'critical', 'medium']
        assert len(result['risk_factors']) > 0

    def test_score_output_types_serialization(self):
        """Test sanitize_numpy_types converts NumPy objects to native Python serializable types."""
        raw_output = {
            'np_bool': np.bool_(True),
            'np_int': np.int64(42),
            'np_float': np.float64(88.75),
            'np_array': np.array([1.0, 2.0, 3.0]),
            'nested': {
                'inner_float': np.float32(12.34),
                'inner_list': [np.int32(1), np.int32(2)]
            }
        }
        sanitized = sanitize_numpy_types(raw_output)

        assert type(sanitized['np_bool']) is bool
        assert type(sanitized['np_int']) is int
        assert type(sanitized['np_float']) is float
        assert type(sanitized['np_array']) is list
        assert type(sanitized['nested']['inner_float']) is float
        assert type(sanitized['nested']['inner_list'][0]) is int

    def test_engine_graceful_missing_fields_handling(self):
        """Test engine handles transaction payloads with missing optional fields."""
        engine = FraudDetectionEngine()
        minimal_txn = {
            'amount': 150.00,
            'card_number': '**** **** **** 1234'
        }
        result = engine.analyze_transaction(minimal_txn)
        assert isinstance(result, dict)
        assert 'fraud_score' in result
        assert 0.0 <= result['fraud_score'] <= 100.0
