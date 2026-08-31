import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, classification_report
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

def evaluate_current_baseline():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    file_path = os.path.join(repo_root, 'creditcard_2023.csv')
    df = pd.read_csv(file_path, nrows=100000)
    print(f"Loaded {len(df)} rows. Class counts:\n{df['Class'].value_counts()}")

    df_domain = prepare_training_dataset(df)
    preprocessor = TransactionPreprocessor()
    X_processed = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    # Stratified Train/Test Split (80% train+val, 20% holdout test)
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, stratify=y
    )

    # Load existing saved scaler and model
    scaler = joblib.load(os.path.join(repo_root, 'scaler.pkl'))
    model = joblib.load(os.path.join(repo_root, 'fraud_model.pkl'))

    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)

    print("\n================ CURRENT BASELINE EVALUATION (HOLDOUT TEST SET) ================")
    print(f"Test Set Size: {len(y_test)} (Legitimate: {(y_test==0).sum()}, Fraud: {(y_test==1).sum()})")
    print(f"Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print(f"Accuracy : {acc:.6f} ({acc*100:.2f}%)")
    print(f"Precision: {prec:.6f} ({prec*100:.2f}%)")
    print(f"Recall   : {rec:.6f} ({rec*100:.2f}%)")
    print(f"F1 Score : {f1:.6f}")
    print(f"ROC-AUC  : {roc_auc:.6f}")
    print(f"PR-AUC   : {pr_auc:.6f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=['Legitimate', 'Fraud'], digits=4))

if __name__ == '__main__':
    evaluate_current_baseline()
