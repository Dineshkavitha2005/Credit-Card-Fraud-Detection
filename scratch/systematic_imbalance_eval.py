import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import (
    RandomForestClassifier, ExtraTreesClassifier,
    HistGradientBoostingClassifier, GradientBoostingClassifier
)
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, precision_recall_curve
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

# Fix preprocessor to ensure category_risk, location_risk, device_risk are properly read
class UnifiedPreprocessor(TransactionPreprocessor):
    def transform_dataframe(self, df):
        df_out = pd.DataFrame()

        if 'Amount' in df.columns:
            df_out['amount_raw'] = df['Amount'].astype(float).clip(lower=0.0)
        elif 'amount' in df.columns:
            df_out['amount_raw'] = df['amount'].astype(float).clip(lower=0.0)
        elif 'amount_raw' in df.columns:
            df_out['amount_raw'] = df['amount_raw'].astype(float).clip(lower=0.0)
        else:
            df_out['amount_raw'] = 0.0

        df_out['log_amount'] = np.log1p(df_out['amount_raw'])

        if 'category' in df.columns:
            df_out['category_risk'] = df['category'].apply(self.get_category_risk)
        elif 'category_risk' in df.columns:
            df_out['category_risk'] = df['category_risk'].astype(float)
        else:
            df_out['category_risk'] = 0.15

        if 'location' in df.columns:
            df_out['location_risk'] = df['location'].apply(self.get_location_risk)
        elif 'location_risk' in df.columns:
            df_out['location_risk'] = df['location_risk'].astype(float)
        else:
            df_out['location_risk'] = 0.15

        if 'device_type' in df.columns:
            df_out['device_risk'] = df['device_type'].apply(self.get_device_risk)
        elif 'device_risk' in df.columns:
            df_out['device_risk'] = df['device_risk'].astype(float)
        else:
            df_out['device_risk'] = 0.15

        if 'hour' in df.columns:
            df_out['hour'] = df['hour'].astype(float)
        else:
            df_out['hour'] = 12.0

        df_out['hour_sin'] = np.sin(2.0 * np.pi * df_out['hour'] / 24.0)
        df_out['hour_cos'] = np.cos(2.0 * np.pi * df_out['hour'] / 24.0)
        df_out['unusual_hour_flag'] = ((df_out['hour'] >= 0) & (df_out['hour'] <= 5)).astype(float)

        if 'velocity_score' in df.columns:
            df_out['velocity_score'] = df['velocity_score'].astype(float)
        else:
            df_out['velocity_score'] = 0.0

        v_cols = [f'V{i}' for i in range(1, 29)]
        has_v = all(col in df.columns for col in v_cols)

        if has_v:
            v_df = df[v_cols].astype(float)
            df_out['v_mean'] = v_df.mean(axis=1)
            df_out['v_std'] = v_df.std(axis=1)
            df_out['v_min'] = v_df.min(axis=1)
            df_out['v_max'] = v_df.max(axis=1)
            df_out['v_sum_abs'] = v_df.abs().sum(axis=1)
        else:
            df_out['v_mean'] = (df_out['category_risk'] + df_out['location_risk'] + df_out['device_risk']) / 3.0 - 0.5
            df_out['v_std'] = 1.0 + (df_out['amount_raw'] > 2000).astype(float) * 0.5
            df_out['v_min'] = -1.0 - 2.0 * df_out['location_risk']
            df_out['v_max'] = 1.0 + 2.0 * df_out['category_risk']
            df_out['v_sum_abs'] = (df_out['category_risk'] + df_out['location_risk'] + df_out['device_risk']) * 5.0

        return df_out[self.feature_names]

def evaluate_strategies():
    df = pd.read_csv('creditcard_2023.csv', nrows=100000)
    df_domain = prepare_training_dataset(df)
    preprocessor = UnifiedPreprocessor()
    X = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    # 80% Dev, 20% Holdout Test (Untouched)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 75% Train, 25% Validation from Dev
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )

    # Fit scaler strictly on X_train
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    print("================================================================================")
    print("EVALUATING MODEL FAMILIES & SAMPLING STRATEGIES ON VALIDATION DATA")
    print(f"Train: {len(y_train)} (Legit: {(y_train==0).sum()}, Fraud: {(y_train==1).sum()})")
    print(f"Val  : {len(y_val)} (Legit: {(y_val==0).sum()}, Fraud: {(y_val==1).sum()})")
    print("================================================================================")

    # Strategy 1: Resampling train set (SMOTE-like oversampling + controlled undersampling)
    # Fraud indices and legit indices in train
    fraud_idx = np.where(y_train == 1)[0]
    legit_idx = np.where(y_train == 0)[0]
    
    # Random oversampling of fraud by 10x
    rng = np.random.default_rng(42)
    oversampled_fraud_idx = rng.choice(fraud_idx, size=len(fraud_idx)*10, replace=True)
    # Add slight Gaussian jitter to continuous scaled features to avoid exact duplicate leaves
    fraud_samples = X_train_scaled[oversampled_fraud_idx] + rng.normal(0, 0.05, size=(len(oversampled_fraud_idx), X_train_scaled.shape[1]))
    
    # Combine with legit
    X_train_resampled = np.vstack([X_train_scaled[legit_idx], fraud_samples])
    y_train_resampled = np.hstack([np.zeros(len(legit_idx)), np.ones(len(oversampled_fraud_idx))])

    # Strategy 2: Controlled Undersampling (e.g. 10:1 ratio)
    subsampled_legit_idx = rng.choice(legit_idx, size=len(fraud_idx)*15, replace=False)
    X_train_undersampled = np.vstack([X_train_scaled[subsampled_legit_idx], X_train_scaled[fraud_idx]])
    y_train_undersampled = np.hstack([np.zeros(len(subsampled_legit_idx)), np.ones(len(fraud_idx))])

    models_to_test = [
        ("RF Standard (depth=12, n=100)", RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=2), X_train_scaled, y_train),
        ("RF class_weight={0:1, 1:10} (depth=12)", RandomForestClassifier(n_estimators=100, max_depth=12, class_weight={0:1, 1:10}, random_state=42, n_jobs=2), X_train_scaled, y_train),
        ("RF class_weight={0:1, 1:20} (depth=14)", RandomForestClassifier(n_estimators=100, max_depth=14, class_weight={0:1, 1:20}, random_state=42, n_jobs=2), X_train_scaled, y_train),
        ("RF class_weight={0:1, 1:30} (depth=14)", RandomForestClassifier(n_estimators=150, max_depth=14, class_weight={0:1, 1:30}, random_state=42, n_jobs=2), X_train_scaled, y_train),
        ("RF Jitter-Oversampled (depth=14)", RandomForestClassifier(n_estimators=100, max_depth=14, random_state=42, n_jobs=2), X_train_resampled, y_train_resampled),
        ("RF Controlled-Undersampled 15:1", RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=2), X_train_undersampled, y_train_undersampled),
        ("HistGradientBoosting (l2=1.0, max_iter=100)", HistGradientBoostingClassifier(l2_regularization=1.0, max_iter=100, random_state=42), X_train_scaled, y_train),
        ("GradientBoosting (n=100, depth=5, lr=0.1)", GradientBoostingClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42), X_train_scaled, y_train),
    ]

    for label, clf, X_tr, y_tr in models_to_test:
        clf.fit(X_tr, y_tr)
        val_probs = clf.predict_proba(X_val_scaled)[:, 1]
        val_pred = clf.predict(X_val_scaled)

        prec_def = precision_score(y_val, val_pred, zero_division=0)
        rec_def = recall_score(y_val, val_pred, zero_division=0)
        f1_def = f1_score(y_val, val_pred, zero_division=0)
        roc_auc = roc_auc_score(y_val, val_probs)
        pr_auc = average_precision_score(y_val, val_probs)

        # Threshold optimization on Validation
        precisions, recalls, thresholds = precision_recall_curve(y_val, val_probs)
        f1_scores = np.where((precisions + recalls) > 0, 2 * (precisions * recalls) / (precisions + recalls), 0)
        best_i = np.argmax(f1_scores)
        best_thresh = thresholds[best_i] if best_i < len(thresholds) else 0.5
        best_f1 = f1_scores[best_i]
        best_p = precisions[best_i]
        best_r = recalls[best_i]

        # Scan for high-recall operational points (e.g. recall >= 0.80, recall >= 0.85)
        high_rec_idx = np.where(recalls >= 0.80)[0]
        if len(high_rec_idx) > 0:
            hr_i = high_rec_idx[np.argmax(precisions[high_rec_idx])]
            hr_thresh = thresholds[hr_i] if hr_i < len(thresholds) else 0.5
            hr_p = precisions[hr_i]
            hr_r = recalls[hr_i]
            hr_f1 = f1_scores[hr_i]
        else:
            hr_thresh, hr_p, hr_r, hr_f1 = 0.5, 0, 0, 0

        print(f"\nModel: {label}")
        print(f"  ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")
        print(f"  Default (0.50) -> Rec: {rec_def:.4f}, Prec: {prec_def:.4f}, F1: {f1_def:.4f}")
        print(f"  Optimal F1 Val -> Thresh: {best_thresh:.4f} | Rec: {best_r:.4f}, Prec: {best_p:.4f}, F1: {best_f1:.4f}")
        print(f"  Target Rec>=80% -> Thresh: {hr_thresh:.4f} | Rec: {hr_r:.4f}, Prec: {hr_p:.4f}, F1: {hr_f1:.4f}")

if __name__ == '__main__':
    evaluate_strategies()
