import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, precision_recall_curve
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

def run_experiments():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    file_path = os.path.join(repo_root, 'creditcard_2023.csv')
    df = pd.read_csv(file_path, nrows=100000)

    df_domain = prepare_training_dataset(df)
    preprocessor = TransactionPreprocessor()
    X_processed = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    # 1. First split: 80% Dev (Train + Validation), 20% Holdout Test (Untouched!)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, stratify=y
    )

    # 2. Second split: Dev set into 75% Train (60% of total) and 25% Validation (20% of total)
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )

    print(f"Dataset splits:")
    print(f"  Train set     : {len(y_train)} samples (Legit: {(y_train==0).sum()}, Fraud: {(y_train==1).sum()}, Fraud rate: {(y_train==1).mean()*100:.3f}%)")
    print(f"  Validation set: {len(y_val)} samples (Legit: {(y_val==0).sum()}, Fraud: {(y_val==1).sum()})")
    print(f"  Test set      : {len(y_test)} samples (Legit: {(y_test==0).sum()}, Fraud: {(y_test==1).sum()})")

    # Fit scaler ONLY on train set
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Candidate models to evaluate on validation set
    models = {
        "Baseline RF (no class_weight)": RandomForestClassifier(
            n_estimators=100, max_depth=12, random_state=42, n_jobs=-1
        ),
        "RF class_weight='balanced'": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1
        ),
        "RF class_weight='balanced_subsample'": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight='balanced_subsample', random_state=42, n_jobs=-1
        ),
        "RF class_weight={0:1, 1:10}": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight={0: 1, 1: 10}, random_state=42, n_jobs=-1
        ),
        "RF class_weight={0:1, 1:25}": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight={0: 1, 1: 25}, random_state=42, n_jobs=-1
        ),
        "RF class_weight={0:1, 1:50}": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight={0: 1, 1: 50}, random_state=42, n_jobs=-1
        ),
        "RF class_weight={0:1, 1:100}": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight={0: 1, 1: 100}, random_state=42, n_jobs=-1
        ),
        "RF balanced_subsample depth=15 n=200": RandomForestClassifier(
            n_estimators=200, max_depth=15, min_samples_split=5, min_samples_leaf=2,
            class_weight='balanced_subsample', random_state=42, n_jobs=-1
        ),
        "HistGradientBoosting balanced": HistGradientBoostingClassifier(
            class_weight='balanced', random_state=42
        ),
        "ExtraTrees balanced_subsample": ExtraTreesClassifier(
            n_estimators=100, max_depth=12, class_weight='balanced_subsample', random_state=42, n_jobs=-1
        )
    }

    results = []
    print("\n--- Model Training & Validation Evaluation ---")
    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        y_val_pred = model.predict(X_val_scaled)
        y_val_prob = model.predict_proba(X_val_scaled)[:, 1]

        acc = accuracy_score(y_val, y_val_pred)
        prec = precision_score(y_val, y_val_pred, zero_division=0)
        rec = recall_score(y_val, y_val_pred, zero_division=0)
        f1 = f1_score(y_val, y_val_pred, zero_division=0)
        roc_auc = roc_auc_score(y_val, y_val_prob)
        pr_auc = average_precision_score(y_val, y_val_prob)
        cm = confusion_matrix(y_val, y_val_pred)
        tn, fp, fn, tp = cm.ravel()

        results.append({
            'Model': name,
            'Val Acc': acc,
            'Val Prec': prec,
            'Val Rec': rec,
            'Val F1': f1,
            'Val ROC-AUC': roc_auc,
            'Val PR-AUC': pr_auc,
            'TN': tn, 'FP': fp, 'FN': fn, 'TP': tp,
            'model_obj': model
        })
        print(f"{name:40s} | Rec: {rec:.4f} | Prec: {prec:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | TP={tp}, FN={fn}, FP={fp}")

    results_df = pd.DataFrame(results).drop(columns=['model_obj'])
    print("\nValidation Summary Table:")
    print(results_df.to_string(index=False))

    return results, X_train, y_train, X_val, y_val, X_test, y_test

if __name__ == '__main__':
    run_experiments()
