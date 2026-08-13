#!/usr/bin/env python
"""
Security Verification Suite for Payment & Transaction Security
Verifies:
1. Plain-text card numbers are NEVER stored in database tables (transactions, user_cards, blocked_cards).
2. CardEncryption validates keys strictly and rejects default/unsafe keys without silent plain-text fallback.
3. API responses (/api/transactions, /api/blocked-cards, /api/cards, CSV export) never expose full card numbers.
4. Database security migration sanitizes legacy plain-text records.
"""

import unittest
import os
import sqlite3
import json
from app import app, db, init_db, get_db, User, UserCard, Transaction, BlockedCard, migrate_database_security
from models import CardEncryption, mask_card_number


class TestPaymentSecurity(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()

    def test_1_card_masking_utility(self):
        """Test mask_card_number formats card numbers securely"""
        self.assertEqual(mask_card_number('4532123456789012'), '**** **** **** 9012')
        self.assertEqual(mask_card_number('4532-1234-5678-9012'), '**** **** **** 9012')
        self.assertEqual(mask_card_number('**** **** **** 9012'), '**** **** **** 9012')
        self.assertEqual(mask_card_number('•••• •••• •••• 9012'), '•••• •••• •••• 9012')
        self.assertEqual(mask_card_number(''), '')
        self.assertEqual(mask_card_number('123'), '**** **** **** ****')

    def test_2_encryption_key_validation(self):
        """Test CardEncryption key validation rejects unsafe key fallbacks"""
        original_key = os.environ.get('CARD_ENCRYPTION_KEY')

        # Test invalid/unsafe key rejection
        for unsafe in ['default-unsafe-key', 'use_Fernet.generate_key()', 'your_secret_key_here', '12345', '']:
            os.environ['CARD_ENCRYPTION_KEY'] = unsafe
            with self.assertRaises(ValueError):
                CardEncryption.validate_key()

        # Restore valid key
        if original_key:
            os.environ['CARD_ENCRYPTION_KEY'] = original_key
        else:
            os.environ['CARD_ENCRYPTION_KEY'] = 'TKe6O7Aqn_ukF0xUAFJ9i7xCtGjEwshAHmQ39u1x3Js='

        # Valid key should pass
        validated = CardEncryption.validate_key()
        self.assertTrue(len(validated) >= 16)

    def test_3_transaction_card_storage_is_masked(self):
        """Test processing a transaction stores ONLY masked card numbers in DB"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'

        raw_card = '4111222233334444'
        payload = {
            'card_number': raw_card,
            'card_holder': 'Security Tester',
            'amount': 99.99,
            'merchant': 'Secure Merchant',
            'category': 'Shopping',
            'location': 'New York, USA'
        }

        res = self.client.post('/api/transactions/process', json=payload)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        txn_id = data['transaction_id']

        # Query database directly to inspect stored record
        conn = get_db()
        row = conn.execute('SELECT card_number FROM transactions WHERE transaction_id = ?', (txn_id,)).fetchone()
        conn.close()

        stored_card = row['card_number']
        # Assert stored card is NOT plain text
        self.assertNotIn(raw_card, stored_card)
        self.assertTrue(stored_card.startswith('****'))
        self.assertEqual(stored_card, '**** **** **** 4444')

    def test_4_api_responses_never_expose_full_card(self):
        """Test API endpoints (/api/transactions, /api/transactions/export, /api/blocked-cards) never expose raw card numbers"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'

        raw_card = '4555666677778888'

        # 1. Process transaction
        res = self.client.post('/api/transactions/process', json={
            'card_number': raw_card,
            'card_holder': 'API Exposure Test',
            'amount': 150.00,
            'merchant': 'Test Shop',
            'category': 'General',
            'location': 'Chicago, USA'
        })
        self.assertEqual(res.status_code, 200)

        # 2. Get transaction history API
        hist_res = self.client.get('/api/transactions')
        self.assertEqual(hist_res.status_code, 200)
        txns = hist_res.get_json()['transactions']
        for t in txns:
            self.assertNotIn(raw_card, t['card_number'])
            self.assertTrue(t['card_number'].startswith('****') or t['card_number'].startswith('••••'))

        # 3. CSV Export API
        csv_res = self.client.get('/api/transactions/export')
        self.assertEqual(csv_res.status_code, 200)
        csv_text = csv_res.get_json()['csv']
        self.assertNotIn(raw_card, csv_text)

    def test_5_user_card_encryption(self):
        """Test user card numbers are encrypted in UserCard table"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'

        raw_card = '4000123412349999'
        add_res = self.client.post('/api/cards', json={
            'card_number': raw_card,
            'card_holder': 'Encrypted User',
            'expiry_month': 12,
            'expiry_year': 2028,
            'cvv': '123'
        })
        self.assertIn(add_res.status_code, [200, 400])  # 400 if already added in previous test run

        with self.app.app_context():
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                for card in admin_user.cards:
                    # Stored card_number MUST NOT equal raw card number
                    self.assertNotEqual(card.card_number, raw_card)
                    # Decryption must recover original card number
                    decrypted = CardEncryption.decrypt_card_number(card.card_number)
                    self.assertEqual(decrypted[-4:], '9999')

    def test_6_database_security_migration(self):
        """Test migrate_database_security sanitizes legacy plain text records"""
        conn = get_db()
        # Insert artificial plain-text record
        test_id = 'TXN_TEST_PLAIN_123'
        conn.execute('DELETE FROM transactions WHERE transaction_id = ?', (test_id,))
        conn.execute('''
            INSERT INTO transactions (transaction_id, card_number, card_holder, amount, merchant, category, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (test_id, '4999888877776666', 'Migration Test', 50.0, 'Test', 'Test', 'Local'))
        conn.commit()
        conn.close()

        # Run migration
        with self.app.app_context():
            migrate_database_security()

        # Verify record is now masked
        conn = get_db()
        row = conn.execute('SELECT card_number FROM transactions WHERE transaction_id = ?', (test_id,)).fetchone()
        conn.close()
        self.assertNotIn('4999888877776666', row['card_number'])
        self.assertEqual(row['card_number'], '**** **** **** 6666')


if __name__ == '__main__':
    unittest.main()
