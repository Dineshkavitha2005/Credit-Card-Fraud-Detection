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
    roc_auc_score, average_precision_score, confusion_matrix, classification_report
)
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

class FixedPreprocessor(TransactionPreprocessor):
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

def test():
    df = pd.read_csv('creditcard_2023.csv', nrows=100000)
    df_domain = prepare_training_dataset(df)
    preprocessor = FixedPreprocessor()
    X = preprocessor.transform_dataframe(df_domain)
    y = df['Class']

    print("Transformed feature statistics for Class 1 (Fraud):")
    print(X[y == 1][['category_risk', 'location_risk', 'device_risk', 'velocity_score', 'v_mean']].describe().T[['mean', 'std', 'min', '50%', 'max']])

    print("\nTransformed feature statistics for Class 0 (Legitimate):")
    print(X[y == 0][['category_risk', 'location_risk', 'device_risk', 'velocity_score', 'v_mean']].describe().T[['mean', 'std', 'min', '50%', 'max']])

    # Split Dev and Test
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Split Train and Val from Dev
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Evaluate multiple models with the fixed features on the validation set
    for name, clf in [
        ("RF default", RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=2)),
        ("RF class_weight='balanced'", RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=2)),
        ("RF class_weight='balanced_subsample'", RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced_subsample', random_state=42, n_jobs=2)),
        ("RF balanced_subsample depth=14 n=150", RandomForestClassifier(n_estimators=150, max_depth=14, min_samples_leaf=2, class_weight='balanced_subsample', random_state=42, n_jobs=2)),
        ("RF weight {0:1, 1:20}", RandomForestClassifier(n_estimators=100, max_depth=12, class_weight={0:1, 1:20}, random_state=42, n_jobs=2)),
        ("RF weight {0:1, 1:50}", RandomForestClassifier(n_estimators=100, max_depth=12, class_weight={0:1, 1:50}, random_state=42, n_jobs=2)),
    ]:
        clf.fit(X_train_scaled, y_train)
        y_val_pred = clf.predict(X_val_scaled)
        y_val_prob = clf.predict_proba(X_val_scaled)[:, 1]

        acc = accuracy_score(y_val, y_val_pred)
        prec = precision_score(y_val, y_val_pred, zero_division=0)
        rec = recall_score(y_val, y_val_pred, zero_division=0)
        f1 = f1_score(y_val, y_val_pred, zero_division=0)
        auc = roc_auc_score(y_val, y_val_prob)
        pr_auc = average_precision_score(y_val, y_val_prob)
        cm = confusion_matrix(y_val, y_val_pred)

        print(f"\n{name:38s}")
        print(f"  Val Rec: {rec:.4f} ({cm[1,1]}/{cm[1,1]+cm[1,0]}) | Prec: {prec:.4f} ({cm[1,1]}/{cm[1,1]+cm[0,1]}) | F1: {f1:.4f} | ROC-AUC: {auc:.4f} | PR-AUC: {pr_auc:.4f}")
        print(f"  CM: TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}")

if __name__ == '__main__':
    test()
