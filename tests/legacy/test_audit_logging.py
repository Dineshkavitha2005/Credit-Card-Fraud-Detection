"""
Comprehensive Test Suite for Audit Logging System
Validates event recording, data sanitization, access protection, filtering, and pagination.
"""

import unittest
import json
import time
from app import app
from models import db, User, AuditLog, UserCard
from audit_logger import audit_logger, EventType, sanitize_audit_metadata, mask_card_str

class TestAuditLoggingSystem(unittest.TestCase):

    def setUp(self):
        """Set up test environment and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Create test admin user
            admin = User(
                username='admin_test',
                email='admin@test.com',
                role='admin',
                is_active=True
            )
            admin.set_password('AdminPass123!')
            db.session.add(admin)

            # Create test normal user
            normal_user = User(
                username='user_test',
                email='user@test.com',
                role='user',
                is_active=True
            )
            normal_user.set_password('UserPass123!')
            db.session.add(normal_user)

            db.session.commit()
            self.admin_id = admin.id
            self.user_id = normal_user.id

    def tearDown(self):
        """Clean up database after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login_user(self, username, password):
        """Helper to log in a user"""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    # ─── 1. Data Sanitization & Redaction Tests ──────────────────────────────

    def test_metadata_sanitization_redacts_passwords_and_secrets(self):
        """Verify sensitive parameters (passwords, tokens, secret keys) are redacted"""
        raw_metadata = {
            'username': 'john_doe',
            'password': 'SuperSecretPassword123!',
            'new_password': 'BrandNewPassword456!',
            'secret_key': 'top-secret-fernet-key-value',
            'token': 'abc123xyztoken',
            '2fa_secret': 'JBSWY3DPEHPK3PXP',
            'cvv': '123'
        }
        sanitized = sanitize_audit_metadata(raw_metadata)
        self.assertEqual(sanitized['password'], '[REDACTED]')
        self.assertEqual(sanitized['new_password'], '[REDACTED]')
        self.assertEqual(sanitized['secret_key'], '[REDACTED]')
        self.assertEqual(sanitized['token'], '[REDACTED]')
        self.assertEqual(sanitized['2fa_secret'], '[REDACTED]')
        self.assertEqual(sanitized['cvv'], '[REDACTED]')
        self.assertEqual(sanitized['username'], 'john_doe')

    def test_metadata_sanitization_masks_card_numbers(self):
        """Verify credit card numbers are masked to **** **** **** 1234"""
        raw_card = '4532015589123456'
        raw_metadata = {
            'card_number': raw_card,
            'amount': 250.00,
            'merchant': 'Tech Store',
            'nested': {
                'cc_num': '5105105105105105'
            }
        }
        sanitized = sanitize_audit_metadata(raw_metadata)
        self.assertEqual(sanitized['card_number'], '**** **** **** 3456')
        self.assertEqual(sanitized['nested']['cc_num'], '**** **** **** 5105')
        self.assertEqual(sanitized['amount'], 250.00)

    # ─── 2. All 13 Event Types Logging Tests ─────────────────────────────────

    def test_event_logging_all_13_event_types(self):
        """Test that all 13 required event types can be recorded and retrieved"""
        with app.app_context():
            # 1. Login
            audit_logger.log_event(EventType.LOGIN, user_id=self.user_id, details={'client': 'web'})
            # 2. Logout
            audit_logger.log_event(EventType.LOGOUT, user_id=self.user_id, details={'duration': 300})
            # 3. Failed Login
            audit_logger.log_event(EventType.FAILED_LOGIN, user_id=None, status='failure', details={'attempted_username': 'hacker'})
            # 4. Registration
            audit_logger.log_event(EventType.REGISTRATION, user_id=self.user_id, status='success', details={'email': 'user@test.com'})
            # 5. Password Change
            audit_logger.log_event(EventType.PASSWORD_CHANGE, user_id=self.user_id, status='success')
            # 6. Transaction Submission
            audit_logger.log_event(EventType.TRANSACTION_SUBMISSION, user_id=self.user_id, details={'amount': 99.99})
            # 7. Fraud Detection
            audit_logger.log_event(EventType.FRAUD_DETECTION, user_id=self.user_id, details={'score': 85.5})
            # 8. Admin User Change
            audit_logger.log_event(EventType.ADMIN_USER_CHANGE, user_id=self.admin_id, details={'updated_user': self.user_id})
            # 9. Account Block & Unblock
            audit_logger.log_event(EventType.ACCOUNT_BLOCK, user_id=self.admin_id, target_resource=f"User:{self.user_id}")
            audit_logger.log_event(EventType.ACCOUNT_UNBLOCK, user_id=self.admin_id, target_resource=f"User:{self.user_id}")
            # 10. Report Generation
            audit_logger.log_event(EventType.REPORT_GENERATION, user_id=self.user_id, details={'format': 'pdf'})
            # 11. Report Download
            audit_logger.log_event(EventType.REPORT_DOWNLOAD, user_id=self.user_id, details={'report_id': 1})
            # 12. Suspicious Activity
            audit_logger.log_event(EventType.SUSPICIOUS_ACTIVITY, user_id=self.user_id, status='failure', details={'reason': 'Rate limit'})
            # 13. API Authorization Failures
            audit_logger.log_event(EventType.API_AUTH_FAILURE, user_id=None, status='failure', target_resource='/api/admin/users')
            # 14. Google OAuth Events
            audit_logger.log_event(EventType.GOOGLE_LOGIN_SUCCESS, user_id=self.user_id, status='success')
            audit_logger.log_event(EventType.GOOGLE_LOGIN_FAILURE, user_id=None, status='failure')
            audit_logger.log_event(EventType.GOOGLE_ACCOUNT_CREATED, user_id=self.user_id, status='success')
            audit_logger.log_event(EventType.GOOGLE_ACCOUNT_LINKED, user_id=self.user_id, status='success')
            audit_logger.log_event(EventType.GOOGLE_ACCOUNT_UNLINKED, user_id=self.user_id, status='success')
            audit_logger.log_event(EventType.GOOGLE_LOGIN_CANCELLED, user_id=None, status='failure')

            logs = AuditLog.query.all()
            recorded_types = {log.get_event_type for log in logs}

            for event in EventType.ALL_EVENTS:
                self.assertIn(event, recorded_types, f"Event type {event} was not recorded")

    # ─── 3. Access Protection & Role Authorization Tests ─────────────────────

    def test_unauthorized_user_cannot_access_audit_logs_ui_or_api(self):
        """Verify non-admin users and guests receive 401/403 on audit log endpoints"""
        from flask_login import logout_user
        # 1. Unauthenticated guest
        with self.app.test_request_context():
            logout_user()

        guest_client = self.app.test_client()
        with guest_client.session_transaction() as sess:
            sess.clear()

        res_ui = guest_client.get('/admin/audit-logs', follow_redirects=False)
        self.assertIn(res_ui.status_code, (302, 401))

        res_api = guest_client.get('/api/admin/audit-logs')
        self.assertEqual(res_api.status_code, 401)

        # 2. Authenticated non-admin user
        self.login_user('user_test', 'UserPass123!')
        res_user_ui = self.client.get('/admin/audit-logs')
        self.assertEqual(res_user_ui.status_code, 403)

        res_user_api = self.client.get('/api/admin/audit-logs')
        self.assertEqual(res_user_api.status_code, 403)

    def test_admin_user_can_access_audit_logs_ui_and_api(self):
        """Verify admin user can access audit log UI and JSON API"""
        self.login_user('admin_test', 'AdminPass123!')

        res_ui = self.client.get('/admin/audit-logs')
        self.assertEqual(res_ui.status_code, 200)

        res_api = self.client.get('/api/admin/audit-logs')
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertIn('logs', data)
        self.assertIn('total', data)
        self.assertIn('stats', data)

    # ─── 4. Filtering and Pagination Tests ───────────────────────────────────

    def test_audit_logs_api_filtering_and_pagination(self):
        """Test event_type filtering, search, and page pagination"""
        with app.app_context():
            # Seed logs
            for i in range(15):
                audit_logger.log_event(EventType.LOGIN, user_id=self.user_id, ip_address=f"192.168.1.{i}")
            for i in range(10):
                audit_logger.log_event(EventType.FAILED_LOGIN, status='failure', ip_address=f"10.0.0.{i}")

        self.login_user('admin_test', 'AdminPass123!')

        # Test per_page pagination
        res_p1 = self.client.get('/api/admin/audit-logs?page=1&per_page=10')
        data_p1 = res_p1.get_json()
        self.assertEqual(len(data_p1['logs']), 10)
        self.assertGreaterEqual(data_p1['total'], 25)

        # Test event_type filter
        res_filter = self.client.get('/api/admin/audit-logs?event_type=failed_login')
        data_filter = res_filter.get_json()
        for log in data_filter['logs']:
            self.assertEqual(log['event_type'], 'failed_login')

        # Test IP search
        res_search = self.client.get('/api/admin/audit-logs?search=10.0.0.5')
        data_search = res_search.get_json()
        self.assertGreaterEqual(len(data_search['logs']), 1)
        self.assertIn('10.0.0.5', data_search['logs'][0]['ip_address'])

    def test_audit_logs_export_api(self):
        """Test CSV and JSON export functionality"""
        with app.app_context():
            audit_logger.log_event(EventType.LOGIN, user_id=self.user_id, details={'test': 'export'})

        self.login_user('admin_test', 'AdminPass123!')

        # JSON Export
        res_json = self.client.get('/api/admin/audit-logs/export?format=json')
        self.assertEqual(res_json.status_code, 200)
        json_data = res_json.get_json()
        self.assertIsInstance(json_data, list)

        # CSV Export
        res_csv = self.client.get('/api/admin/audit-logs/export?format=csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('text/csv', res_csv.content_type)
        self.assertIn(b'Event ID,Event Type', res_csv.data)


if __name__ == '__main__':
    unittest.main()
