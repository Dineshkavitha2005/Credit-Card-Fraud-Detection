import os
import json
import joblib
import pytest
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
from app.services.fraud_detection import FraudDetectionEngine, sanitize_numpy_types
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

class TestMachineLearning:
    """Test suite for ML model loading, preprocessing, scoring, output typing, and performance regression."""

    def test_preprocessor_loading_and_config(self):
        """Test preprocessor initializes and loads configuration properly."""
        preprocessor = TransactionPreprocessor.load_config('preprocessing_config.json')
        assert preprocessor is not None
        assert hasattr(preprocessor, 'feature_names')
        assert len(preprocessor.feature_names) == 15

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
        if os.path.exists('fraud_model.pkl') and os.path.exists('scaler.pkl'):
            assert engine.model is not None
            assert engine.scaler is not None
            assert engine.feature_names is not None
            assert isinstance(engine.model_version, str)
            assert engine.model_version == 'v2.1.0'
            assert hasattr(engine, 'classification_threshold')
            assert 0.0 < engine.classification_threshold < 1.0

    def test_model_metadata_consistency(self):
        """Test model_metadata.json contains complete evaluation metrics and parameters."""
        assert os.path.exists('model_metadata.json')
        with open('model_metadata.json', 'r') as f:
            meta = json.load(f)
        
        assert meta['model_version'] == 'v2.1.0'
        assert meta['architecture'] == 'RandomForestClassifier'
        assert 'classification_threshold' in meta
        assert 'evaluation_metrics' in meta
        metrics = meta['evaluation_metrics']
        assert metrics['recall'] >= 0.85
        assert metrics['precision'] >= 0.85
        assert metrics['roc_auc'] >= 0.98
        assert 'confusion_matrix' in metrics

    def test_holdout_model_performance_regression(self):
        """Regression test verifying trained model exceeds minimum performance targets on holdout test set."""
        if not os.path.exists('creditcard_2023.csv'):
            pytest.skip("Dataset file creditcard_2023.csv not present for holdout regression test")

        df = pd.read_csv('creditcard_2023.csv', nrows=100000)
        df_domain = prepare_training_dataset(df)
        preprocessor = TransactionPreprocessor()
        X_processed = preprocessor.transform_dataframe(df_domain)
        y = df['Class']

        # Exact holdout test split
        _, X_test, _, y_test = train_test_split(
            X_processed, y, test_size=0.2, random_state=42, stratify=y
        )

        scaler = joblib.load('scaler.pkl')
        model = joblib.load('fraud_model.pkl')
        with open('model_metadata.json', 'r') as f:
            meta = json.load(f)
        threshold = meta.get('classification_threshold', 0.25)

        X_test_scaled = scaler.transform(X_test)
        probs = model.predict_proba(X_test_scaled)[:, 1]
        preds = (probs >= threshold).astype(int)

        rec = recall_score(y_test, preds)
        prec = precision_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        pr_auc = average_precision_score(y_test, probs)

        # Assert material improvement over baseline (recall was 0.4667)
        assert rec >= 0.85, f"Expected holdout recall >= 0.85, got {rec:.4f}"
        assert prec >= 0.85, f"Expected holdout precision >= 0.85, got {prec:.4f}"
        assert auc >= 0.98, f"Expected holdout ROC-AUC >= 0.98, got {auc:.4f}"
        assert pr_auc >= 0.90, f"Expected holdout PR-AUC >= 0.90, got {pr_auc:.4f}"

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
        assert 'model_version' in result

        assert result['fraud_score'] >= 0.0
        assert result['fraud_score'] <= 100.0
        assert isinstance(result['is_fraud'], bool)
        assert result['risk_level'].lower() in ['low', 'medium', 'high', 'critical']
        assert result['ml_probability'] < engine.classification_threshold

    def test_prediction_pipeline_fraud(self, sample_fraud_transaction):
        """Test analyzing a fraudulent transaction triggers high risk score and ML pattern factor."""
        engine = FraudDetectionEngine()
        result = engine.analyze_transaction(sample_fraud_transaction)

        assert result['fraud_score'] >= 65.0
        assert result['risk_level'].lower() in ['high', 'critical']
        assert result['is_fraud'] is True
        assert len(result['risk_factors']) > 0
        assert result['ml_probability'] >= engine.classification_threshold

    def test_deterministic_scoring(self, sample_genuine_transaction):
        """Test repeated inference calls yield identical scoring output."""
        engine = FraudDetectionEngine()
        r1 = engine.analyze_transaction(sample_genuine_transaction)
        r2 = engine.analyze_transaction(sample_genuine_transaction)

        assert r1['fraud_score'] == r2['fraud_score']
        assert r1['ml_probability'] == r2['ml_probability']
        assert r1['rule_score'] == r2['rule_score']

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
