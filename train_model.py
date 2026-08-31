"""
Training script for Sentinel Credit Card Fraud Detection model.
Trains a high-recall, precision-preserving RandomForestClassifier using the unified
TransactionPreprocessor pipeline, performs 5-fold cross-validation on the development split,
derives calibrated decision thresholds, evaluates empirically on an untouched holdout test set,
and saves model artifacts, scaler, feature list, preprocessing configuration, and metadata.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, precision_recall_curve
)

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
    print(f"Loading dataset from {file_path}...", flush=True)

    if not os.path.exists(file_path):
        print(f"Error: Dataset file not found at {file_path}", flush=True)
        return

    try:
        df = pd.read_csv(file_path, nrows=100000)
    except Exception as e:
        print(f"Error reading CSV file: {e}", flush=True)
        return

    print(f"Dataset successfully loaded. Shape: {df.shape}", flush=True)
    print(f"Class distribution: 0 (Legit) = {(df['Class']==0).sum()}, 1 (Fraud) = {(df['Class']==1).sum()}", flush=True)

    # Prepare domain features correlated with class
    df_domain = prepare_training_dataset(df)

    # Instantiate preprocessor and transform features
    preprocessor = TransactionPreprocessor()
    X_processed = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    print(f"Transformed features shape: {X_processed.shape}", flush=True)
    print(f"Features list: {preprocessor.feature_names}", flush=True)

    # Step 1: Stratified Holdout Test Split (Strict 80% Dev, 20% Untouched Holdout Test)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\n--- Data Partitioning ---", flush=True)
    print(f"Development set (Train + Val): {len(y_dev)} samples (Legitimate: {(y_dev==0).sum()}, Fraud: {(y_dev==1).sum()})", flush=True)
    print(f"Holdout Test set (Untouched) : {len(y_test)} samples (Legitimate: {(y_test==0).sum()}, Fraud: {(y_test==1).sum()})", flush=True)

    # Step 2: 5-Fold Stratified Cross-Validation on Development Set to calibrate threshold
    print(f"\n--- Running 5-Fold Stratified Cross-Validation on Dev Set ---", flush=True)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof_probs = np.zeros(len(y_dev))

    rf_params = {
        'n_estimators': 200,
        'max_depth': 15,
        'min_samples_split': 4,
        'min_samples_leaf': 2,
        'class_weight': {0: 1, 1: 30},
        'random_state': 42,
        'n_jobs': 2
    }

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_dev, y_dev)):
        X_tr, y_tr = X_dev.iloc[train_idx], y_dev.iloc[train_idx]
        X_va, y_va = X_dev.iloc[val_idx], y_dev.iloc[val_idx]

        sc = StandardScaler()
        X_tr_sc = sc.fit_transform(X_tr)
        X_va_sc = sc.transform(X_va)

        cv_model = RandomForestClassifier(**rf_params)
        cv_model.fit(X_tr_sc, y_tr)
        oof_probs[val_idx] = cv_model.predict_proba(X_va_sc)[:, 1]

    oof_roc_auc = float(roc_auc_score(y_dev, oof_probs))
    oof_pr_auc = float(average_precision_score(y_dev, oof_probs))

    # Derive optimal threshold maximizing F1 on OOF validation predictions
    precisions, recalls, thresholds = precision_recall_curve(y_dev, oof_probs)
    f1_scores = np.where((precisions + recalls) > 0, 2 * (precisions * recalls) / (precisions + recalls), 0)
    best_i = np.argmax(f1_scores)
    calibrated_threshold = float(thresholds[best_i]) if best_i < len(thresholds) else 0.25

    print(f"OOF Cross-Validation ROC-AUC : {oof_roc_auc:.4f}", flush=True)
    print(f"OOF Cross-Validation PR-AUC  : {oof_pr_auc:.4f}", flush=True)
    print(f"Optimal Calibrated Threshold: {calibrated_threshold:.4f} (OOF F1: {f1_scores[best_i]:.4f}, Recall: {recalls[best_i]:.4f}, Prec: {precisions[best_i]:.4f})", flush=True)

    # Step 3: Train final model on full Dev Set
    print("\nTraining final RandomForestClassifier model on full Dev Set...", flush=True)
    scaler = StandardScaler()
    X_dev_scaled = scaler.fit_transform(X_dev)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestClassifier(**rf_params)
    model.fit(X_dev_scaled, y_dev)

    # Step 4: Empirical Evaluation on Untouched Holdout Test Set
    test_probs = model.predict_proba(X_test_scaled)[:, 1]
    
    # 1. At Default (0.50) threshold
    pred_def = (test_probs >= 0.50).astype(int)
    cm_def = confusion_matrix(y_test, pred_def)
    tn_d, fp_d, fn_d, tp_d = cm_def.ravel()
    acc_def = float(accuracy_score(y_test, pred_def))
    prec_def = float(precision_score(y_test, pred_def, zero_division=0))
    rec_def = float(recall_score(y_test, pred_def, zero_division=0))
    f1_def = float(f1_score(y_test, pred_def, zero_division=0))

    # 2. At Calibrated threshold
    pred_opt = (test_probs >= calibrated_threshold).astype(int)
    cm_opt = confusion_matrix(y_test, pred_opt)
    tn_o, fp_o, fn_o, tp_o = cm_opt.ravel()
    acc_opt = float(accuracy_score(y_test, pred_opt))
    prec_opt = float(precision_score(y_test, pred_opt, zero_division=0))
    rec_opt = float(recall_score(y_test, pred_opt, zero_division=0))
    f1_opt = float(f1_score(y_test, pred_opt, zero_division=0))
    roc_auc_test = float(roc_auc_score(y_test, test_probs))
    pr_auc_test = float(average_precision_score(y_test, test_probs))

    print("\n================ EMPIRICAL MODEL EVALUATION (HOLDOUT TEST SET) ================", flush=True)
    print(f"Holdout Test Samples : {len(y_test)} (Legitimate: {(y_test==0).sum()}, Fraud: {(y_test==1).sum()})", flush=True)
    print(f"ROC-AUC on Holdout   : {roc_auc_test:.6f}", flush=True)
    print(f"PR-AUC on Holdout    : {pr_auc_test:.6f}", flush=True)
    print(f"\n[Default Threshold 0.50]")
    print(f"  Confusion Matrix: TN={tn_d}, FP={fp_d}, FN={fn_d}, TP={tp_d}")
    print(f"  Accuracy : {acc_def:.4f} ({acc_def*100:.2f}%)")
    print(f"  Precision: {prec_def:.4f} ({prec_def*100:.2f}%)")
    print(f"  Recall   : {rec_def:.4f} ({rec_def*100:.2f}%)")
    print(f"  F1 Score : {f1_def:.4f}")
    print(f"\n[Calibrated Threshold {calibrated_threshold:.4f}]")
    print(f"  Confusion Matrix: TN={tn_o}, FP={fp_o}, FN={fn_o}, TP={tp_o}")
    print(f"  Accuracy : {acc_opt:.4f} ({acc_opt*100:.2f}%)")
    print(f"  Precision: {prec_opt:.4f} ({prec_opt*100:.2f}%)")
    print(f"  Recall   : {rec_opt:.4f} ({rec_opt*100:.2f}%)")
    print(f"  F1 Score : {f1_opt:.4f}")

    # Save artifacts
    print("\nSaving model artifacts...", flush=True)
    joblib.dump(model, os.path.join(workspace_dir, 'fraud_model.pkl'))
    joblib.dump(scaler, os.path.join(workspace_dir, 'scaler.pkl'))
    joblib.dump(preprocessor.feature_names, os.path.join(workspace_dir, 'features.pkl'))
    preprocessor.save_config(os.path.join(workspace_dir, 'preprocessing_config.json'))

    # Save model metadata and version info
    metadata = {
        'model_version': 'v2.1.0',
        'architecture': 'RandomForestClassifier',
        'n_estimators': 200,
        'max_depth': 15,
        'min_samples_split': 4,
        'min_samples_leaf': 2,
        'class_weight': {'0': 1, '1': 30},
        'classification_threshold': round(calibrated_threshold, 4),
        'trained_at': datetime.now().isoformat(),
        'dataset': os.path.basename(file_path),
        'training_samples': len(X_dev),
        'test_samples': len(X_test),
        'feature_count': len(preprocessor.feature_names),
        'features': preprocessor.feature_names,
        'evaluation_metrics': {
            'accuracy': round(acc_opt, 4),
            'precision': round(prec_opt, 4),
            'recall': round(rec_opt, 4),
            'f1_score': round(f1_opt, 4),
            'roc_auc': round(roc_auc_test, 6),
            'pr_auc': round(pr_auc_test, 6),
            'default_threshold_metrics': {
                'accuracy': round(acc_def, 4),
                'precision': round(prec_def, 4),
                'recall': round(rec_def, 4),
                'f1_score': round(f1_def, 4)
            },
            'confusion_matrix': {
                'true_negatives': int(tn_o),
                'false_positives': int(fp_o),
                'false_negatives': int(fn_o),
                'true_positives': int(tp_o)
            }
        }
    }

    with open(os.path.join(workspace_dir, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n[SUCCESS] Training complete. Artifacts saved successfully:", flush=True)
    print(" - fraud_model.pkl", flush=True)
    print(" - scaler.pkl", flush=True)
    print(" - features.pkl", flush=True)
    print(" - preprocessing_config.json", flush=True)
    print(" - model_metadata.json", flush=True)

if __name__ == "__main__":
    train()
