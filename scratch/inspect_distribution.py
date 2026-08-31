import pandas as pd
import numpy as np

file_path = 'creditcard_2023.csv'
df_id_class = pd.read_csv(file_path, usecols=['id', 'Class'])
print("Total rows:", len(df_id_class))
print("Class counts:", df_id_class['Class'].value_counts())

# Check how fraud is distributed across index ranges
for start in range(0, len(df_id_class), 100000):
    chunk = df_id_class.iloc[start:start+100000]
    n_fraud = (chunk['Class'] == 1).sum()
    print(f"Rows {start:6d} to {start+len(chunk)-1:6d}: {n_fraud:6d} frauds ({n_fraud/len(chunk)*100:6.2f}%)")

print("\nWhere are the first 1000 fraud rows located by index?")
fraud_indices = df_id_class[df_id_class['Class'] == 1].index
print(fraud_indices[:20])
print(f"Total fraud rows in full file: {len(fraud_indices)}")
