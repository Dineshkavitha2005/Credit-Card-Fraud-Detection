import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from preprocessor import TransactionPreprocessor
from train_model import prepare_training_dataset

df = pd.read_csv('creditcard_2023.csv', nrows=100000)
df_domain = prepare_training_dataset(df)
preprocessor = TransactionPreprocessor()
X = preprocessor.transform_dataframe(df_domain)
y = df['Class']

print("Summary statistics of 15 features for Class 0 (Legitimate):")
print(X[y == 0].describe().T[['mean', 'std', 'min', '50%', 'max']])

print("\nSummary statistics of 15 features for Class 1 (Fraud):")
print(X[y == 1].describe().T[['mean', 'std', 'min', '50%', 'max']])

# Also check individual V features in raw df
v_cols = [f'V{i}' for i in range(1, 29)]
diffs = []
for col in v_cols:
    m0 = df[df['Class'] == 0][col].mean()
    m1 = df[df['Class'] == 1][col].mean()
    s0 = df[df['Class'] == 0][col].std()
    s1 = df[df['Class'] == 1][col].std()
    # Cohen's d / standardized difference
    d = (m1 - m0) / np.sqrt((s0**2 + s1**2) / 2)
    diffs.append((col, m0, m1, d))

diffs.sort(key=lambda x: abs(x[3]), reverse=True)
print("\nTop 10 most discriminative raw V features by standardized difference:")
for col, m0, m1, d in diffs[:10]:
    print(f"  {col:5s} | Mean(0): {m0:7.3f} | Mean(1): {m1:7.3f} | Cohen's d: {d:7.3f}")
