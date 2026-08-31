import pandas as pd
import numpy as np

file_path = 'creditcard_2023.csv'
print(f"Inspecting {file_path}...")
df_head = pd.read_csv(file_path, nrows=10)
print(f"Columns: {list(df_head.columns)}")

# Read full dataset or first 100,000 rows
df_100k = pd.read_csv(file_path, nrows=100000)
print(f"100k class distribution:\n{df_100k['Class'].value_counts()}")
print(f"100k class proportions:\n{df_100k['Class'].value_counts(normalize=True)}")

# Let's check full dataset size and class distribution
# Read only 'Class' column for entire CSV to be fast
df_class = pd.read_csv(file_path, usecols=['Class'])
print(f"Full dataset size: {len(df_class)}")
print(f"Full dataset class distribution:\n{df_class['Class'].value_counts()}")
print(f"Full dataset class proportions:\n{df_class['Class'].value_counts(normalize=True)}")
