import pytest
from app.models.transaction import Transaction, BlockedCard
from app.models.alert import Alert
from app.extensions import db

class TestTransactions:
    """Test suite for transaction processing, fraud analysis, and storage."""

    def test_process_valid_genuine_transaction(self, authenticated_client, sample_genuine_transaction, app):
        """Test processing a valid genuine transaction succeeds and stores in DB."""
        res = authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)
        assert res.status_code == 200
        data = res.get_json()

        assert data['status'] in ['approved', 'flagged', 'blocked']
        assert 'transaction_id' in data
        assert 'fraud_score' in data
        assert isinstance(data['fraud_score'], (int, float))
        assert 'is_fraud' in data
        assert isinstance(data['is_fraud'], bool)
        assert 'analysis' in data

        # Verify database storage
        with app.app_context():
            txn = Transaction.query.filter_by(transaction_id=data['transaction_id']).first()
            assert txn is not None
            assert txn.amount == sample_genuine_transaction['amount']
            assert txn.merchant == sample_genuine_transaction['merchant']
            assert txn.card_number.startswith('****') or txn.card_number.startswith('••••')
            assert txn.card_number.endswith(sample_genuine_transaction['card_number'][-4:])

    def test_process_invalid_transaction_zero_amount(self, authenticated_client):
        """Test transaction processing fails with 0 amount."""
        res = authenticated_client.post('/api/transactions/process', json={
            'amount': 0,
            'card_number': '4532759283741092',
            'merchant': 'Coffee Shop'
        })
        assert res.status_code == 400
        data = res.get_json()
        assert 'error' in data or 'message' in data

    def test_process_invalid_transaction_negative_amount(self, authenticated_client):
        """Test transaction processing fails with negative amount."""
        res = authenticated_client.post('/api/transactions/process', json={
            'amount': -100.50,
            'card_number': '4532759283741092',
            'merchant': 'Store'
        })
        assert res.status_code == 400
        data = res.get_json()
        assert 'error' in data or 'message' in data

    def test_process_invalid_transaction_non_numeric_amount(self, authenticated_client):
        """Test transaction processing fails with non-numeric amount."""
        res = authenticated_client.post('/api/transactions/process', json={
            'amount': 'invalid_amount',
            'card_number': '4532759283741092',
            'merchant': 'Store'
        })
        assert res.status_code == 400

    def test_fraud_prediction_high_risk(self, authenticated_client, sample_fraud_transaction, app):
        """Test high-risk transaction triggers fraud scoring and flags multiple risk factors."""
        res = authenticated_client.post('/api/transactions/process', json=sample_fraud_transaction)
        assert res.status_code == 200
        data = res.get_json()

        assert data['fraud_score'] >= 50.0
        assert data['status'] in ['approved', 'blocked', 'flagged']
        assert len(data['risk_factors']) >= 3

        risk_text = " ".join(data['risk_factors'])
        assert 'amount' in risk_text.lower()
        assert 'location' in risk_text.lower() or 'nigeria' in risk_text.lower()
        assert 'category' in risk_text.lower() or 'merchant' in risk_text.lower() or 'device' in risk_text.lower()

        # Verify transaction storage in database
        with app.app_context():
            txn = Transaction.query.filter_by(transaction_id=data['transaction_id']).first()
            assert txn is not None
            assert txn.fraud_score >= 50.0

    def test_genuine_prediction_low_risk(self, authenticated_client, sample_genuine_transaction):
        """Test genuine transaction results in low risk and approval."""
        res = authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)
        assert res.status_code == 200
        data = res.get_json()

        assert data['is_fraud'] is False
        assert data['fraud_score'] < 50.0
        assert data['status'] == 'approved'

    def test_blocked_card_transaction_declined(self, authenticated_client, app):
        """Test transaction using a blocked card is declined with 403."""
        card_num = '4532759283748888'
        masked_card = f"**** **** **** {card_num[-4:]}"

        with app.app_context():
            blocked = BlockedCard(
                card_number=masked_card,
                reason='Stolen card report',
                is_active=True
            )
            db.session.add(blocked)
            db.session.commit()

        res = authenticated_client.post('/api/transactions/process', json={
            'amount': 50.0,
            'card_number': card_num,
            'merchant': 'Local Store'
        })
        assert res.status_code == 403
        data = res.get_json()
        assert 'declined' in data.get('error', '').lower() or 'blocked' in data.get('error', '').lower()

    def test_get_transactions_api_response(self, authenticated_client, sample_genuine_transaction):
        """Test GET /api/transactions returns formatted list with pagination metadata."""
        # Create a transaction first
        authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)

        res = authenticated_client.get('/api/transactions')
        assert res.status_code == 200
        data = res.get_json()

        assert 'transactions' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data
        assert len(data['transactions']) >= 1

        t = data['transactions'][0]
        assert 'transaction_id' in t
        assert 'card_number' in t
        assert 'amount' in t
        assert 'status' in t
        assert 'is_fraud' in t

    def test_transaction_review_resolution(self, authenticated_client, sample_fraud_transaction, app):
        """Test reviewing/resolving a transaction alert status."""
        proc_res = authenticated_client.post('/api/transactions/process', json=sample_fraud_transaction)
        txn_id = proc_res.get_json()['transaction_id']

        rev_res = authenticated_client.post(f'/api/transactions/{txn_id}/review', json={
            'status': 'reviewed'
        })
        assert rev_res.status_code == 200
        assert 'marked as reviewed' in rev_res.get_json()['message']

        with app.app_context():
            txn = Transaction.query.filter_by(transaction_id=txn_id).first()
            assert txn.status == 'reviewed'
            assert txn.reviewed_by is not None

    def test_simulate_batch_and_single_transactions(self, authenticated_client):
        """Test /api/simulate with both single transaction and batch simulation count."""
        # Single transaction simulation
        single_res = authenticated_client.post('/api/simulate', json={
            'amount': 4500.0,
            'merchant': 'High-End Jeweler',
            'category': 'Jewelry',
            'location': 'Nigeria'
        })
        assert single_res.status_code == 200
        single_data = single_res.get_json()
        assert 'analysis' in single_data
        assert 'fraud_score' in single_data

        # Batch simulation
        batch_res = authenticated_client.post('/api/simulate', json={'count': 20})
        assert batch_res.status_code == 200
        batch_data = batch_res.get_json()
        assert batch_data.get('count') == 20
        assert 'fraud_detected' in batch_data
        assert 'simulated_transactions' in batch_data
        assert len(batch_data['simulated_transactions']) > 0
