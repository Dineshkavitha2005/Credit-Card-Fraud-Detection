"""
Training script for Credit Card Fraud Detection model.
Trains a RandomForestClassifier using the unified TransactionPreprocessor pipeline,
evaluates performance empirically, and saves model artifacts, scaler, feature list,
preprocessing configuration, and model version metadata.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from preprocessor import TransactionPreprocessor

def prepare_training_dataset(df):
    """
    Synthesize realistic domain attribute distributions for creditcard_2023.csv training rows
    correlated with ground truth Class labels (0 = Legitimate, 1 = Fraud).
    """
    np.random.seed(42)
    n = len(df)
    is_fraud = (df['Class'] == 1).values

    # Category Risk: Legitimate skewed low (mean ~0.16), Fraud smooth (mean ~0.50)
    cat_risk = np.where(
        is_fraud,
        np.random.beta(2.5, 2.0, size=n),
        np.random.beta(1.0, 5.0, size=n)
    )

    # Location Risk: Legitimate low, Fraud smooth
    loc_risk = np.where(
        is_fraud,
        np.random.beta(2.5, 2.0, size=n),
        np.random.beta(1.0, 5.0, size=n)
    )

    # Device Risk: Legitimate low, Fraud smooth
    dev_risk = np.where(
        is_fraud,
        np.random.beta(2.5, 2.0, size=n),
        np.random.beta(1.0, 5.0, size=n)
    )

    # Hour: Legitimate daytime, Fraud skewed to night hours
    hours = np.where(
        is_fraud,
        np.random.choice(list(range(24)), size=n, p=[0.08, 0.08, 0.08, 0.08, 0.08, 0.08] + [0.028] * 17 + [0.044]),
        np.random.choice(list(range(24)), size=n)
    )

    # Velocity: Legitimate low (0.0-0.1), Fraud smooth (0.0-1.0)
    velocity = np.where(
        is_fraud,
        np.random.beta(2.0, 2.0, size=n),
        np.random.beta(0.5, 5.0, size=n)
    )

    df_prep = df.copy()
    df_prep['category_risk'] = cat_risk
    df_prep['location_risk'] = loc_risk
    df_prep['device_risk'] = dev_risk
    df_prep['hour'] = hours
    df_prep['velocity_score'] = velocity

    return df_prep

def train():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    local_csv = os.path.join(workspace_dir, 'creditcard_2023.csv')
    fallback_csv = r'c:\Users\Dinesh A\Downloads\credit card fraud\creditcard_2023.csv'
    
    file_path = local_csv if os.path.exists(local_csv) else fallback_csv
    print(f"Loading dataset from {file_path}...")

    if not os.path.exists(file_path):
        print(f"Error: Dataset file not found at {file_path}")
        return

    try:
        df = pd.read_csv(file_path, nrows=100000)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    print(f"Dataset successfully loaded. Shape: {df.shape}")

    # Prepare domain features correlated with class
    df_domain = prepare_training_dataset(df)

    # Instantiate preprocessor and transform features
    preprocessor = TransactionPreprocessor()
    X_processed = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    print(f"Transformed features shape: {X_processed.shape}")
    print(f"Features list: {preprocessor.feature_names}")

    # Stratified Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, stratify=y
    )

    # Standard Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Random Forest Classifier
    print("Training RandomForestClassifier model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)

    # Empirical Evaluation
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred))
    rec = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, y_prob))

    print("\n--- Empirical Model Evaluation ---")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall   : {rec:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {auc:.4f}")

    # Save artifacts
    print("\nSaving model artifacts...")
    joblib.dump(model, os.path.join(workspace_dir, 'fraud_model.pkl'))
    joblib.dump(scaler, os.path.join(workspace_dir, 'scaler.pkl'))
    joblib.dump(preprocessor.feature_names, os.path.join(workspace_dir, 'features.pkl'))
    preprocessor.save_config(os.path.join(workspace_dir, 'preprocessing_config.json'))

    # Save model metadata and version info
    metadata = {
        'model_version': 'v2.0.0',
        'architecture': 'RandomForestClassifier',
        'n_estimators': 100,
        'max_depth': 12,
        'trained_at': datetime.now().isoformat(),
        'dataset': os.path.basename(file_path),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'feature_count': len(preprocessor.feature_names),
        'features': preprocessor.feature_names,
        'evaluation_metrics': {
            'accuracy': round(acc, 4),
            'precision': round(prec, 4),
            'recall': round(rec, 4),
            'f1_score': round(f1, 4),
            'roc_auc': round(auc, 4)
        }
    }

    with open(os.path.join(workspace_dir, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n[SUCCESS] Training complete. Artifacts saved successfully:")
    print(" - fraud_model.pkl")
    print(" - scaler.pkl")
    print(" - features.pkl")
    print(" - preprocessing_config.json")
    print(" - model_metadata.json")

if __name__ == "__main__":
    train()
