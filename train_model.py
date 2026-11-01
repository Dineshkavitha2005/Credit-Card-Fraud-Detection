"""
Training script for Sentinel Credit Card Fraud Detection model.
Re-exported from backend.ml.train_model for backward compatibility.
"""
import sys
import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.ml.train_model import (  # noqa: F401
    prepare_training_dataset,
    train
)

if __name__ == '__main__':
    train()
