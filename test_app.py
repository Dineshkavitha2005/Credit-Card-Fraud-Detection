import time
from app import app
from models import Merchant, Transaction
import pandas as pd

def test_database_operations():
    """Test database operations within app context."""
    with app.app_context():
        print("=== Database Integrity Tests ===")

        # Test merchant count
        merchants = Merchant.query.all()
        print(f"Total merchants: {len(merchants)}")
        assert len(merchants) > 0, "No merchants found"

        # Test transaction count
        transactions = Transaction.query.all()
        print(f"Total transactions: {len(transactions)}")
        assert len(transactions) > 0, "No transactions found"

        # Test sample merchant exists
        sample_merchant = Merchant.query.filter_by(merchant_id='test123!').first()
        assert sample_merchant is not None, "Sample merchant not found"
        print("Sample merchant exists: test123!")

        # Test transactions for sample merchant
        sample_transactions = Transaction.query.filter_by(merchant_id='test123!').all()
        print(f"Transactions for sample merchant: {len(sample_transactions)}")

        # Test fraud detection on sample transaction
        if sample_transactions:
            tx = sample_transactions[0]
            tx_data = {
                'TransactionID': tx.transaction_id,
                'TransactionDate': tx.transaction_date.isoformat(),
                'Amount': tx.amount,
                'MerchantID': tx.merchant_id,
                'TransactionType': tx.transaction_type,
                'Location': tx.location,
                'IsFraud': tx.is_fraud
            }
            # Load model for prediction
            import joblib
            model = joblib.load('model.pkl')
            preprocessor, _ = joblib.load('preprocessor.pkl')
            prediction = model.predict(preprocessor.transform(pd.DataFrame([tx_data])))[0]
            print(f"Fraud prediction for sample transaction: {'Fraud' if prediction == 1 else 'No Fraud'}")

        print("Database operations: PASSED")

def test_routes():
    """Test key routes using Flask test client (no external server needed)."""
    print("\n=== Route Tests ===")

    with app.test_client() as client:
        # Index page
        response = client.get("/")
        assert response.status_code == 200, f"Index page failed: {response.status_code}"
        print("Index page: PASSED")

        # Signup page
        response = client.get("/signup")
        assert response.status_code == 200, f"Signup page failed: {response.status_code}"
        print("Signup page: PASSED")

        # Signup POST with unique merchant ID (single-step flow)
        unique_id = f"testuser{int(time.time())}"
        signup_data = {
            'MerchantID': unique_id,
            'Password': 'testpass123',
            'ConfirmPassword': 'testpass123'
        }
        response = client.post("/signup", data=signup_data, follow_redirects=False)
        assert response.status_code == 302, f"Signup POST should redirect: {response.status_code}"
        print("Signup POST: PASSED")

        # Login POST
        login_data = {
            'MerchantID': 'test123!',
            'Password': 'password123'
        }
        response = client.post("/", data=login_data, follow_redirects=True)
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        assert b"Dashboard" in response.data, "Dashboard content not found after login"
        print("Login: PASSED")

        # Authenticated routes
        assert client.get("/dashboard").status_code == 200, "Dashboard failed"
        print("Dashboard: PASSED")

        assert client.get("/transactions").status_code == 200, "Transactions failed"
        print("Transactions page: PASSED")

        assert client.get("/insights").status_code == 200, "Insights failed"
        print("Insights page: PASSED")

        live_feed = client.get("/api/live_feed")
        assert live_feed.status_code == 200, "Live feed API failed"
        assert isinstance(live_feed.get_json(), list), "Live feed should return list"
        print("Live feed API: PASSED")

        assert client.get("/live").status_code == 200, "Live page failed"
        print("Live page: PASSED")

        assert client.get("/admin").status_code == 200, "Admin page failed"
        print("Admin page: PASSED")

        assert client.get("/fraud_transactions").status_code == 200, "Fraud transactions failed"
        print("Fraud transactions page: PASSED")

        logout_response = client.get("/logout", follow_redirects=False)
        assert logout_response.status_code == 302, "Logout should redirect"
        print("Logout: PASSED")

    print("All route tests: PASSED")

def test_edge_cases():
    """Test edge cases and error handling with test client."""
    print("\n=== Edge Case Tests ===")

    with app.test_client() as client:
        # Invalid login
        login_data = {'MerchantID': 'invalid', 'Password': 'invalid'}
        response = client.post("/", data=login_data)
        assert response.status_code == 200, "Invalid login should return 200"
        assert b"Invalid MerchantID or Password" in response.data, "Should show error message"
        print("Invalid login handling: PASSED")

        # Protected route without login
        resp_protected = client.get("/dashboard", follow_redirects=False)
        assert resp_protected.status_code == 302, "Dashboard should redirect when not logged in"
        print("Protected route access: PASSED")

        # Login then request non-existent transaction details
        client.post("/", data={'MerchantID': 'test123!', 'Password': 'password123'})
        missing = client.get("/transaction_details?transaction_id=999999")
        assert missing.status_code == 404, "Non-existent transaction should return 404"
        print("Non-existent transaction handling: PASSED")

    print("Edge case tests: PASSED")

if __name__ == "__main__":
    try:
        test_database_operations()
        test_routes()
        test_edge_cases()
        print("\n🎉 All tests passed! The app is working correctly, especially the database functionality.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
