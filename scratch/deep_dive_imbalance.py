import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    precision_recall_curve, roc_curve
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

def deep_dive():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    file_path = os.path.join(repo_root, 'creditcard_2023.csv')
    df = pd.read_csv(file_path, nrows=100000)

    df_domain = prepare_training_dataset(df)
    preprocessor = TransactionPreprocessor()
    X_processed = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    # 1. 80% dev, 20% untouched holdout test
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, stratify=y
    )

    # 2. 75% train (60k), 25% val (20k) from dev
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Train a well-regularized Random Forest with balanced subsampling / weights
    rf_baseline = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=2)
    rf_baseline.fit(X_train_scaled, y_train)

    val_probs_base = rf_baseline.predict_proba(X_val_scaled)[:, 1]
    
    print("=== BASELINE RF PROBABILITIES ON VALIDATION SET ===")
    fraud_val_probs = val_probs_base[y_val == 1]
    legit_val_probs = val_probs_base[y_val == 0]
    print(f"Legit max prob: {legit_val_probs.max():.4f}, 99th percentile: {np.percentile(legit_val_probs, 99):.4f}, 99.9th percentile: {np.percentile(legit_val_probs, 99.9):.4f}")
    print(f"Fraud probs sorted:\n{np.sort(fraud_val_probs)}")

    # Precision-Recall Curve on Validation
    precisions, recalls, thresholds = precision_recall_curve(y_val, val_probs_base)
    f1_scores = np.where((precisions + recalls) > 0, 2 * (precisions * recalls) / (precisions + recalls), 0)
    best_idx = np.argmax(f1_scores)
    best_thresh = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    print(f"\nBest F1 on Validation for Baseline RF: F1={f1_scores[best_idx]:.4f} at Threshold={best_thresh:.4f} (Prec={precisions[best_idx]:.4f}, Rec={recalls[best_idx]:.4f})")

    # Let's inspect multiple thresholds on validation
    print("\nThreshold Scan on Validation Set (Baseline RF):")
    for t in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]:
        y_val_p = (val_probs_base >= t).astype(int)
        p = precision_score(y_val, y_val_p, zero_division=0)
        r = recall_score(y_val, y_val_p, zero_division=0)
        f = f1_score(y_val, y_val_p, zero_division=0)
        cm = confusion_matrix(y_val, y_val_p)
        print(f"Thresh={t:.2f} | Rec={r:.4f} ({cm[1,1]}/{cm[1,1]+cm[1,0]}) | Prec={p:.4f} | F1={f:.4f} | FP={cm[0,1]}")

if __name__ == '__main__':
    deep_dive()
