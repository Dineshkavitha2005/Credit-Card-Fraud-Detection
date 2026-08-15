"""
Automated Test Suite for Upgraded Dashboard Overview API
"""

import unittest
import os
import json
from datetime import datetime, timedelta
from app import app, db, User, Transaction, CardEncryption, mask_card_number, get_db, init_db


class DashboardApiTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key_dashboard_2026'

        self.app_context = app.app_context()
        self.app_context.push()

        init_db()

        self.client = app.test_client()

        # Create or fetch Admin User
        self.admin = User.query.filter_by(username='dashboard_test_admin').first()
        if not self.admin:
            self.admin = User(
                username='dashboard_test_admin',
                email='dash_admin@test.com',
                role='admin',
                is_active=True,
                is_verified=True
            )
            self.admin.set_password('AdminPass123!')
            db.session.add(self.admin)
            db.session.commit()

    def tearDown(self):
        # Cleanup test transactions
        Transaction.query.filter(Transaction.transaction_id.like('TXN_DASH_TEST_%')).delete(synchronize_session=False)
        db.session.commit()
        self.app_context.pop()

    def _login(self):
        return self.client.post('/login', data={
            'username': 'dashboard_test_admin',
            'password': 'AdminPass123!'
        }, follow_redirects=True)

    def test_overview_requires_auth(self):
        response = self.client.get('/api/dashboard/overview')
        self.assertEqual(response.status_code, 401)  # Unauthorized API request

    def test_overview_structure_and_kpi_cards(self):
        self._login()
        response = self.client.get('/api/dashboard/overview')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIn('kpi', data)
        self.assertIn('charts', data)
        self.assertIn('recent_transactions', data)
        self.assertIn('recent_alerts', data)

        kpi = data['kpi']
        self.assertIn('total_transactions', kpi)
        self.assertIn('total_amount', kpi)
        self.assertIn('fraudulent_transactions', kpi)
        self.assertIn('fraud_rate', kpi)
        self.assertIn('high_risk_transactions', kpi)
        self.assertIn('blocked_transactions', kpi)
        self.assertIn('fraud_amount_saved', kpi)
        self.assertIn('blocked_cards', kpi)
        self.assertIn('unread_alerts', kpi)

    def test_8_chart_datasets_presence(self):
        self._login()
        response = self.client.get('/api/dashboard/overview')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        charts = data['charts']

        # 1. Fraud vs Genuine
        self.assertIn('fraud_vs_genuine', charts)
        self.assertIn('genuine_count', charts['fraud_vs_genuine'])
        self.assertIn('fraud_count', charts['fraud_vs_genuine'])

        # 2. Trends by Day
        self.assertIn('trends_by_day', charts)
        self.assertIsInstance(charts['trends_by_day'], list)

        # 3. Trends by Month
        self.assertIn('trends_by_month', charts)
        self.assertIsInstance(charts['trends_by_month'], list)

        # 4. Risk Distribution
        self.assertIn('risk_distribution', charts)
        self.assertEqual(len(charts['risk_distribution']), 5)

        # 5. Hourly Pattern
        self.assertIn('hourly_pattern', charts)
        self.assertEqual(len(charts['hourly_pattern']), 24)

        # 6. Amount Distribution
        self.assertIn('amount_distribution', charts)
        self.assertEqual(len(charts['amount_distribution']), 5)

        # 7. Top Categories
        self.assertIn('top_categories', charts)
        self.assertIsInstance(charts['top_categories'], list)

        # 8. High Risk Locations
        self.assertIn('high_risk_locations', charts)
        self.assertIsInstance(charts['high_risk_locations'], list)

    def test_multi_criteria_filters(self):
        self._login()
        now = datetime.utcnow()
        t1 = Transaction(
            transaction_id='TXN_DASH_TEST_001',
            card_number='4111****1111',
            card_holder='UniqueFilterUserAlice',
            amount=100.0,
            merchant='UniqueStoreAlpha',
            category='Retail',
            location='Seattle, USA',
            is_fraud=False,
            fraud_score=10.0,
            status='approved',
            timestamp=now
        )
        t2 = Transaction(
            transaction_id='TXN_DASH_TEST_002',
            card_number='4222****2222',
            card_holder='UniqueFilterUserBob',
            amount=999.0,
            merchant='UniqueStoreBeta',
            category='Online Shopping',
            location='Miami, USA',
            is_fraud=True,
            fraud_score=85.0,
            status='blocked',
            timestamp=now
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        # Search Filter = UniqueFilterUserBob
        resp = self.client.get('/api/dashboard/overview?search=UniqueFilterUserBob')
        data = resp.get_json()
        self.assertEqual(data['kpi']['total_transactions'], 1)
        self.assertEqual(data['recent_transactions'][0]['transaction_id'], 'TXN_DASH_TEST_002')


if __name__ == '__main__':
    unittest.main()
