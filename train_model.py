import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

def train():
    file_path = r'c:\Users\Dinesh A\Downloads\credit card fraud\creditcard_2023.csv'
    print(f"Loading dataset from {file_path}...")

    # Load only a subset if file is too large, but for 2023 version usually it's manageable
    # We will read 100,000 rows to keep it fast for this update
    try:
        df = pd.read_csv(file_path, nrows=100000)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    print(f"Dataset loaded. Shape: {df.shape}")

    # Features and Target
    # Columns are: id, V1, V2, ..., V28, Amount, Class
    X = df.drop(['id', 'Class'], axis=1)
    y = df['Class']

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train a fast model
    print("Training Random Forest model...")
    model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train_scaled, y_train)

    # Evaluate
    score = model.score(X_test_scaled, y_test)
    print(f"Model accuracy: {score:.4f}")

    # Save model and scaler
    joblib.dump(model, 'fraud_model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    print("Model and scaler saved to fraud_model.pkl and scaler.pkl")

    # Save metadata (feature names)
    joblib.dump(X.columns.tolist(), 'features.pkl')

if __name__ == "__main__":
    train()
