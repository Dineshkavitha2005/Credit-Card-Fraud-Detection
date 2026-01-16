import pandas as pd
from models import db, Merchant, Transaction, FraudLog
from datetime import datetime
from app import app

def migrate_data():
    with app.app_context():
        # Create tables
        db.create_all()

        # Load CSV data
        df = pd.read_csv('credit_card_fraud_dataset.csv')

        # Get unique merchant_ids from dataset
        unique_merchant_ids = df['MerchantID'].unique()

        # Migrate merchants
        for mid in unique_merchant_ids:
            if not Merchant.query.filter_by(merchant_id=int(mid)).first():
                merchant = Merchant(merchant_id=int(mid), password="password123")  # Default password
                db.session.add(merchant)

        # Commit merchants first
        db.session.commit()

        # Migrate transactions
        for _, row in df.iterrows():
            if not Transaction.query.filter_by(transaction_id=int(row['TransactionID'])).first():
                transaction = Transaction(
                    transaction_id=int(row['TransactionID']),
                    transaction_date=datetime.strptime(row['TransactionDate'], '%Y-%m-%d %H:%M:%S.%f'),
                    amount=float(row['Amount']),
                    merchant_id=int(row['MerchantID']),
                    transaction_type=row['TransactionType'],
                    location=row['Location'],
                    is_fraud=bool(row['IsFraud'])
                )
                db.session.add(transaction)

        # Commit changes
        db.session.commit()
        print("Data migration completed successfully!")

if __name__ == '__main__':
    migrate_data()
