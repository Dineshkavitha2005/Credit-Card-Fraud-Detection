from flask import Flask
from models import db, Merchant, Transaction, FraudLog
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'fraud_detection.db')

app = Flask(__name__)
# Use the same DB file as the app to avoid divergence (instance/fraud_detection.db)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def create_sample_data():
    with app.app_context():
        # Recreate tables for a clean seed (drops existing)
        db.drop_all()
        db.create_all()
        print("Database tables recreated successfully!")

        # Create sample merchants
        merchants_data = [
            {'merchant_id': 'merchant001', 'username': 'merchant001', 'email': 'merchant001@example.com', 'password': 'pass001'},
            {'merchant_id': 'merchant002', 'username': 'merchant002', 'email': 'merchant002@example.com', 'password': 'pass002'},
            {'merchant_id': 'merchant003', 'username': 'merchant003', 'email': 'merchant003@example.com', 'password': 'pass003'},
            {'merchant_id': 'merchant004', 'username': 'merchant004', 'email': 'merchant004@example.com', 'password': 'pass004'},
            {'merchant_id': 'merchant005', 'username': 'merchant005', 'email': 'merchant005@example.com', 'password': 'pass005'},
            {'merchant_id': 'testuser', 'username': 'testuser', 'email': 'testuser@example.com', 'password': 'testpass123'},
            {'merchant_id': 'test123!', 'username': 'test123user', 'email': 'test123@example.com', 'password': 'password123'},  # aligns with tests
        ]

        merchants = []
        for merchant_data in merchants_data:
            pw_hash = generate_password_hash(merchant_data['password'])
            merchant = Merchant(
                merchant_id=merchant_data['merchant_id'],
                username=merchant_data['username'],
                email=merchant_data['email'],
                password=pw_hash
            )
            merchants.append(merchant)
            db.session.add(merchant)

        db.session.commit()
        print(f"Created {len(merchants)} merchants")

        # Create sample transactions for each merchant
        transaction_types = ['Online Purchase', 'ATM Withdrawal', 'POS Payment', 'Transfer', 'Bill Payment']
        locations = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego']

        transaction_id_counter = 1
        total_transactions = 0

        for merchant in merchants:
            # Create 50-100 transactions per merchant
            num_transactions = random.randint(50, 100)

            for i in range(num_transactions):
                # Generate random transaction data
                transaction_date = datetime.now() - timedelta(days=random.randint(0, 365))
                amount = round(random.uniform(10.0, 5000.0), 2)
                transaction_type = random.choice(transaction_types)
                location = random.choice(locations)
                is_fraud = random.choice([True, False]) if random.random() < 0.1 else False  # 10% fraud rate

                transaction = Transaction(
                    transaction_id=transaction_id_counter,
                    transaction_date=transaction_date,
                    amount=amount,
                    merchant_id=merchant.merchant_id,
                    transaction_type=transaction_type,
                    location=location,
                    is_fraud=is_fraud,
                    fraud_status='Fraud' if is_fraud else 'No Fraud'
                )

                db.session.add(transaction)
                transaction_id_counter += 1
                total_transactions += 1

        db.session.commit()
        print(f"Created {total_transactions} transactions")

        # Create some fraud logs for fraudulent transactions
        fraud_transactions = Transaction.query.filter_by(is_fraud=True).all()
        for tx in fraud_transactions[:10]:  # Log first 10 fraud transactions
            fraud_log = FraudLog(
                transaction_id=tx.transaction_id,
                detected_at=datetime.now(),
                details=f"Fraud detected for transaction {tx.transaction_id} with amount ${tx.amount}"
            )
            db.session.add(fraud_log)

        db.session.commit()
        print(f"Created fraud logs for {len(fraud_transactions[:10])} transactions")

        print("\n=== New Database Summary ===")
        print(f"Total Merchants: {Merchant.query.count()}")
        print(f"Total Transactions: {Transaction.query.count()}")
        print(f"Total Fraud Logs: {FraudLog.query.count()}")
        print(f"Fraud Rate: {(Transaction.query.filter_by(is_fraud=True).count() / Transaction.query.count() * 100):.1f}%")

        print("\n=== Test Credentials ===")
        print("Merchant ID: testuser")
        print("Password: testpass123")

if __name__ == "__main__":
    create_sample_data()
    print("\n✅ New database 'fraud_detection_new.db' created successfully with fresh data!")
