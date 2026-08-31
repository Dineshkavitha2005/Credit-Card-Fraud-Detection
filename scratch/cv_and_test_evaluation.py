import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, precision_recall_curve
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

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

def run_cv_and_test():
    df = pd.read_csv('creditcard_2023.csv', nrows=100000)
    df_domain = prepare_training_dataset(df)
    preprocessor = UnifiedPreprocessor()
    X = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    # 1. Untouched Holdout Test Set (20% = 20,000 samples)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("================================================================================")
    print("STEP 1: 5-FOLD STRATIFIED CROSS-VALIDATION ON DEV SET (80,000 samples)")
    print(f"Dev Set: {len(y_dev)} samples (Legitimate: {(y_dev==0).sum()}, Fraud: {(y_dev==1).sum()})")
    print("================================================================================")

    # Test candidate hyperparameter configurations across 5 folds
    configs = [
        ("RF n=150 max_depth=14 balanced_subsample", {
            'n_estimators': 150, 'max_depth': 14, 'min_samples_split': 4, 'min_samples_leaf': 2,
            'class_weight': 'balanced_subsample', 'random_state': 42, 'n_jobs': 2
        }),
        ("RF n=150 max_depth=14 weight={0:1, 1:25}", {
            'n_estimators': 150, 'max_depth': 14, 'min_samples_split': 4, 'min_samples_leaf': 2,
            'class_weight': {0: 1, 1: 25}, 'random_state': 42, 'n_jobs': 2
        }),
        ("RF n=200 max_depth=15 weight={0:1, 1:30}", {
            'n_estimators': 200, 'max_depth': 15, 'min_samples_split': 4, 'min_samples_leaf': 2,
            'class_weight': {0: 1, 1: 30}, 'random_state': 42, 'n_jobs': 2
        }),
        ("RF n=150 max_depth=12 weight={0:1, 1:20}", {
            'n_estimators': 150, 'max_depth': 12, 'min_samples_split': 4, 'min_samples_leaf': 2,
            'class_weight': {0: 1, 1: 20}, 'random_state': 42, 'n_jobs': 2
        }),
    ]

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    best_config_name = None
    best_oof_f1 = 0.0
    best_oof_thresh = 0.5
    best_config_params = None

    for name, params in configs:
        oof_probs = np.zeros(len(y_dev))
        oof_preds_def = np.zeros(len(y_dev))

        for fold, (train_idx, val_idx) in enumerate(skf.split(X_dev, y_dev)):
            X_tr, y_tr = X_dev.iloc[train_idx], y_dev.iloc[train_idx]
            X_va, y_va = X_dev.iloc[val_idx], y_dev.iloc[val_idx]

            sc = StandardScaler()
            X_tr_sc = sc.fit_transform(X_tr)
            X_va_sc = sc.transform(X_va)

            clf = RandomForestClassifier(**params)
            clf.fit(X_tr_sc, y_tr)

            oof_probs[val_idx] = clf.predict_proba(X_va_sc)[:, 1]
            oof_preds_def[val_idx] = clf.predict(X_va_sc)

        roc_auc = roc_auc_score(y_dev, oof_probs)
        pr_auc = average_precision_score(y_dev, oof_probs)
        prec_def = precision_score(y_dev, oof_preds_def, zero_division=0)
        rec_def = recall_score(y_dev, oof_preds_def, zero_division=0)
        f1_def = f1_score(y_dev, oof_preds_def, zero_division=0)

        precisions, recalls, thresholds = precision_recall_curve(y_dev, oof_probs)
        f1_scores = np.where((precisions + recalls) > 0, 2 * (precisions * recalls) / (precisions + recalls), 0)
        best_i = np.argmax(f1_scores)
        opt_thresh = thresholds[best_i] if best_i < len(thresholds) else 0.5
        opt_f1 = f1_scores[best_i]
        opt_prec = precisions[best_i]
        opt_rec = recalls[best_i]

        print(f"\n--- Config: {name} ---")
        print(f"  OOF ROC-AUC: {roc_auc:.4f} | OOF PR-AUC: {pr_auc:.4f}")
        print(f"  Default (0.50) -> Recall: {rec_def:.4f}, Precision: {prec_def:.4f}, F1: {f1_def:.4f}")
        print(f"  Optimal OOF    -> Threshold: {opt_thresh:.4f} | Recall: {opt_rec:.4f}, Precision: {opt_prec:.4f}, F1: {opt_f1:.4f}")

        if opt_f1 > best_oof_f1:
            best_oof_f1 = opt_f1
            best_oof_thresh = opt_thresh
            best_config_name = name
            best_config_params = params

    print(f"\n>>> Selected Best Architecture: {best_config_name}")
    print(f">>> Calibrated Decision Threshold from OOF CV: {best_oof_thresh:.4f}")

    # STEP 2: Retrain best model on full Dev Set (80,000 samples)
    print("\n================================================================================")
    print("STEP 2: RETRAINING SELECTED MODEL ON FULL DEV SET (80,000 samples)")
    print("================================================================================")
    final_scaler = StandardScaler()
    X_dev_scaled = final_scaler.fit_transform(X_dev)
    X_test_scaled = final_scaler.transform(X_test)

    final_model = RandomForestClassifier(**best_config_params)
    final_model.fit(X_dev_scaled, y_dev)

    # STEP 3: Final Holdout Test Evaluation
    print("\n================================================================================")
    print("STEP 3: EVALUATION ON UNTOUCHED HOLDOUT TEST SET (20,000 samples)")
    print("================================================================================")
    test_probs = final_model.predict_proba(X_test_scaled)[:, 1]
    
    # 1. At standard default threshold 0.50
    test_pred_def = (test_probs >= 0.50).astype(int)
    cm_def = confusion_matrix(y_test, test_pred_def)
    acc_def = accuracy_score(y_test, test_pred_def)
    prec_def = precision_score(y_test, test_pred_def)
    rec_def = recall_score(y_test, test_pred_def)
    f1_def = f1_score(y_test, test_pred_def)

    # 2. At calibrated threshold chosen from CV
    test_pred_opt = (test_probs >= best_oof_thresh).astype(int)
    cm_opt = confusion_matrix(y_test, test_pred_opt)
    acc_opt = accuracy_score(y_test, test_pred_opt)
    prec_opt = precision_score(y_test, test_pred_opt)
    rec_opt = recall_score(y_test, test_pred_opt)
    f1_opt = f1_score(y_test, test_pred_opt)
    roc_auc_test = roc_auc_score(y_test, test_probs)
    pr_auc_test = average_precision_score(y_test, test_probs)

    print(f"Test Set Size: {len(y_test)} (Legitimate: {(y_test==0).sum()}, Fraud: {(y_test==1).sum()})")
    print(f"ROC-AUC on Holdout: {roc_auc_test:.6f}")
    print(f"PR-AUC on Holdout : {pr_auc_test:.6f}")
    
    print("\n[A] Holdout Results at Standard Default Threshold (0.50):")
    print(f"  Confusion Matrix: TN={cm_def[0,0]}, FP={cm_def[0,1]}, FN={cm_def[1,0]}, TP={cm_def[1,1]}")
    print(f"  Accuracy : {acc_def:.6f} ({acc_def*100:.2f}%)")
    print(f"  Precision: {prec_def:.6f} ({prec_def*100:.2f}%)")
    print(f"  Recall   : {rec_def:.6f} ({rec_def*100:.2f}%)")
    print(f"  F1 Score : {f1_def:.6f}")

    print(f"\n[B] Holdout Results at Calibrated Threshold ({best_oof_thresh:.4f}):")
    print(f"  Confusion Matrix: TN={cm_opt[0,0]}, FP={cm_opt[0,1]}, FN={cm_opt[1,0]}, TP={cm_opt[1,1]}")
    print(f"  Accuracy : {acc_opt:.6f} ({acc_opt*100:.2f}%)")
    print(f"  Precision: {prec_opt:.6f} ({prec_opt*100:.2f}%)")
    print(f"  Recall   : {rec_opt:.6f} ({rec_opt*100:.2f}%)")
    print(f"  F1 Score : {f1_opt:.6f}")

if __name__ == '__main__':
    run_cv_and_test()
