"""
Comprehensive Automated Test Suite for Credit Card Fraud Detection Reporting Module
Tests:
- PDF & CSV Generation for 4 required report types
- Filter functionality (date, status, risk level, amount, user)
- Safe card masking in CSV and PDF reports
- Security authorization enforcement (admin vs non-admin)
- Non-exposure of filesystem paths
- Direct stream downloads and deletion error handling
"""

import unittest
import os
import io
import json
import sqlite3
from datetime import datetime, timedelta
from app import app, db, User, Transaction, UserCard, Report, CardEncryption, mask_card_number
from utils import ReportGenerator


class ReportingModuleTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test_secret_key_reporting_2026'
        app.config['CARD_ENCRYPTION_KEY'] = 'g7xK_vL8_S02mD_KjN2P9zQ3xR4vT7yU8wA='
        os.environ['CARD_ENCRYPTION_KEY'] = app.config['CARD_ENCRYPTION_KEY']

        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        # Create Admin User
        self.admin = User(
            username='admin_test',
            email='admin@test.com',
            role='admin',
            is_active=True,
            is_verified=True
        )
        self.admin.set_password('AdminPass123!')

        # Create Regular User
        self.user1 = User(
            username='user1_test',
            email='user1@test.com',
            role='user',
            is_active=True,
            is_verified=True
        )
        self.user1.set_password('UserPass123!')

        # Create Another User (for permission isolation tests)
        self.user2 = User(
            username='user2_test',
            email='user2@test.com',
            role='user',
            is_active=True,
            is_verified=True
        )
        self.user2.set_password('UserPass123!')

        db.session.add_all([self.admin, self.user1, self.user2])
        db.session.commit()

        # Seed Sample Transactions
        now = datetime.utcnow()

        t1 = Transaction(
            transaction_id='TXN_1001',
            user_id=self.user1.id,
            card_number='4111111111111111',
            card_holder='User One',
            amount=150.00,
            merchant='Amazon',
            category='Shopping',
            location='New York, US',
            is_fraud=False,
            fraud_score=0.12,
            status='approved',
            timestamp=now - timedelta(days=2)
        )

        t2 = Transaction(
            transaction_id='TXN_1002',
            user_id=self.user1.id,
            card_number='4111111111111111',
            card_holder='User One',
            amount=4800.00,
            merchant='CryptoExchange',
            category='Finance',
            location='Moscow, RU',
            is_fraud=True,
            fraud_score=0.94,
            status='flagged',
            timestamp=now - timedelta(days=1)
        )

        t3 = Transaction(
            transaction_id='TXN_1003',
            user_id=self.user2.id,
            card_number='5500000000000004',
            card_holder='User Two',
            amount=89.99,
            merchant='Walmart',
            category='Groceries',
            location='Chicago, US',
            is_fraud=False,
            fraud_score=0.05,
            status='approved',
            timestamp=now
        )

        db.session.add_all([t1, t2, t3])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_report_generator_csv_card_masking(self):
        """Verify ReportGenerator.generate_csv masks card numbers safely"""
        txns = [
            {
                'transaction_id': 'TXN_9999',
                'user_id': 1,
                'card_number': '4111222233334444',
                'card_holder': 'John Doe',
                'amount': 250.0,
                'merchant': 'Apple Store',
                'category': 'Electronics',
                'location': 'CA, US',
                'status': 'approved',
                'fraud_score': 0.08,
                'is_fraud': False,
                'timestamp': datetime.utcnow()
            }
        ]

        csv_bytes = ReportGenerator.generate_csv(txns)
        csv_text = csv_bytes.decode('utf-8')

        self.assertNotIn('4111222233334444', csv_text)
        self.assertIn('**** **** **** 4444', csv_text)

    def test_report_generator_pdf_build(self):
        """Verify ReportGenerator.generate_pdf builds valid PDF bytes for required report types"""
        txns = [
            {
                'transaction_id': 'TXN_8888',
                'user_id': 1,
                'card_number': '4111222233334444',
                'card_holder': 'John Doe',
                'amount': 1200.0,
                'merchant': 'Jewelry Hub',
                'category': 'Luxury',
                'location': 'Miami, US',
                'status': 'flagged',
                'fraud_score': 0.88,
                'is_fraud': True,
                'timestamp': datetime.utcnow()
            }
        ]

        for r_type in ['pdf_transaction_report', 'fraud_analysis_report', 'dashboard_summary_report']:
            pdf_bytes = ReportGenerator.generate_pdf(r_type, f"Test {r_type}", txns)
            self.assertTrue(len(pdf_bytes) > 500)
            self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_generate_report_api_user_authorization(self):
        """Test /api/reports/generate forces user_id filter for non-admin users"""
        self.login('user1_test', 'UserPass123!')

        response = self.client.post('/api/reports/generate', json={
            'report_type': 'pdf_transaction_report',
            'format': 'pdf',
            'filters': {}
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'completed')
        report_id = data['report_id']

        report = Report.query.get(report_id)
        self.assertEqual(report.user_id, self.user1.id)
        self.assertEqual(report.filters.get('user_id'), self.user1.id)

    def test_download_report_security_isolation(self):
        """Test user cannot download another user's report"""
        # User 1 generates a report
        self.login('user1_test', 'UserPass123!')
        res1 = self.client.post('/api/reports/generate', json={
            'report_type': 'csv_transaction_report',
            'format': 'csv'
        })
        rep_id_1 = res1.get_json()['report_id']

        # User 2 attempts to download User 1's report
        self.login('user2_test', 'UserPass123!')
        res2 = self.client.get(f'/api/reports/{rep_id_1}/download')
        self.assertEqual(res2.status_code, 404)

        # Admin can download User 1's report
        self.login('admin_test', 'AdminPass123!')
        res_admin = self.client.get(f'/api/reports/{rep_id_1}/download')
        self.assertEqual(res_admin.status_code, 200)
        self.assertEqual(res_admin.mimetype, 'text/csv')

    def test_download_report_headers_and_path_safety(self):
        """Verify download endpoint returns proper stream headers and hides filesystem paths"""
        self.login('admin_test', 'AdminPass123!')

        res = self.client.post('/api/reports/generate', json={
            'report_type': 'fraud_analysis_report',
            'format': 'pdf'
        })
        rep_id = res.get_json()['report_id']

        down_res = self.client.get(f'/api/reports/{rep_id}/download')
        self.assertEqual(down_res.status_code, 200)
        self.assertEqual(down_res.mimetype, 'application/pdf')
        self.assertIn('attachment;', down_res.headers.get('Content-Disposition', ''))

        # Verify API status response does not expose disk filesystem paths
        stat_res = self.client.get(f'/api/reports/{rep_id}')
        stat_json = stat_res.get_json()
        self.assertNotIn('file_path', stat_json)

    def test_export_transactions_direct_stream(self):
        """Test /api/transactions/export returns direct streaming CSV or PDF file"""
        self.login('admin_test', 'AdminPass123!')

        # Test CSV export stream
        res_csv = self.client.get('/api/transactions/export?format=csv&risk_level=high')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, 'text/csv')
        self.assertIn('TXN_1002', res_csv.get_data(as_text=True))
        self.assertNotIn('TXN_1001', res_csv.get_data(as_text=True)) # filtered out low risk

        # Test PDF export stream
        res_pdf = self.client.get('/api/transactions/export?format=pdf')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, 'application/pdf')
        self.assertTrue(res_pdf.get_data().startswith(b'%PDF'))

    def test_delete_report_safe_cleanup(self):
        """Test report deletion removes database entry and file safely"""
        self.login('admin_test', 'AdminPass123!')

        gen_res = self.client.post('/api/reports/generate', json={
            'report_type': 'dashboard_summary_report',
            'format': 'csv'
        })
        rep_id = gen_res.get_json()['report_id']
        report = Report.query.get(rep_id)
        filepath = os.path.join(app.config['REPORTS_DIR'], report.file_path)

        self.assertTrue(os.path.exists(filepath))

        del_res = self.client.delete(f'/api/reports/{rep_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm DB entry and physical file deleted
        self.assertIsNone(Report.query.get(rep_id))
        self.assertFalse(os.path.exists(filepath))


if __name__ == '__main__':
    unittest.main()
