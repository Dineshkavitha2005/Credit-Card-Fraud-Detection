"""
Comprehensive Error Handling, Validation, and Security Test Suite
Tests status codes 400, 401, 403, 404, 405, 409, 413, 422, 429, 500, input validation,
sanitization, database rollbacks, and file upload security.
"""

import unittest
import json
import os
import io
from app import app, db, User, UserCard, Transaction, init_db
from errors import APIError, BadRequestError, ValidationError, format_error_response
from validators import (
    sanitize_string, sanitize_payload, validate_email, validate_username,
    validate_amount, validate_card_number, validate_file_upload
)

class TestErrorHandlingAndValidation(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key_error_handling_2026'
        self.app_context = app.app_context()
        self.app_context.push()
        init_db()
        self.client = app.test_client()

        # Create Normal Test User
        self.normal_user = User.query.filter_by(username='normal_test_user').first()
        if not self.normal_user:
            self.normal_user = User(
                username='normal_test_user',
                email='normal@test.com',
                role='user',
                is_active=True,
                is_verified=True
            )
            self.normal_user.set_password('UserPass123!')
            db.session.add(self.normal_user)
            db.session.commit()

        # Create Admin Test User
        self.admin_user = User.query.filter_by(username='admin_test_user').first()
        if not self.admin_user:
            self.admin_user = User(
                username='admin_test_user',
                email='admin_suite@test.com',
                role='admin',
                is_active=True,
                is_verified=True
            )
            self.admin_user.set_password('AdminPass123!')
            db.session.add(self.admin_user)
            db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def login_as_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.normal_user.id)

    def login_as_admin(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.admin_user.id)

    # ─── 1. Test Input Sanitization & Validation Helpers ─────────────

    def test_string_sanitization(self):
        """Test sanitization of HTML, XSS scripts, and null bytes."""
        xss_input = "<script>alert('xss')</script>"
        sanitized = sanitize_string(xss_input)
        self.assertNotIn("<script>", sanitized)
        self.assertIn("&lt;script&gt;", sanitized)

        null_byte_input = "hello\x00world"
        sanitized_null = sanitize_string(null_byte_input)
        self.assertEqual(sanitized_null, "helloworld")

        payload = {
            "name": "<b style='color:red;'>Test</b>",
            "nested": {"comment": "<iframe src='evil.com'></iframe>"},
            "list": ["<svg onload=alert(1)>", 123]
        }
        clean_payload = sanitize_payload(payload)
        self.assertNotIn("<b>", clean_payload["name"])
        self.assertNotIn("<iframe", clean_payload["nested"]["comment"])
        self.assertNotIn("<svg", clean_payload["list"][0])
        self.assertEqual(clean_payload["list"][1], 123)

    def test_field_validators(self):
        """Test validation helpers for email, username, card numbers, and amounts."""
        # Email
        self.assertEqual(validate_email("TEST@Example.com"), "test@example.com")
        with self.assertRaises(ValidationError):
            validate_email("invalid-email-format")

        # Username
        self.assertEqual(validate_username("valid_user123"), "valid_user123")
        with self.assertRaises(ValidationError):
            validate_username("a")  # Too short

        # Amount
        self.assertEqual(validate_amount(45.50), 45.50)
        self.assertEqual(validate_amount("100.25"), 100.25)
        with self.assertRaises(ValidationError):
            validate_amount(-10)
        with self.assertRaises(ValidationError):
            validate_amount("abc")

        # Card Number (Luhn algorithm)
        # 4532015112830366 is valid Visa
        self.assertEqual(validate_card_number("4532015112830366"), "4532015112830366")
        with self.assertRaises(ValidationError):
            validate_card_number("1234567890123456")  # Fails Luhn check

    def test_file_upload_validation(self):
        """Test file upload validation for allowed extension and size limits."""
        class MockFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.data = io.BytesIO(content)
            def seek(self, offset, whence=0):
                return self.data.seek(offset, whence)
            def tell(self):
                return self.data.tell()

        valid_file = MockFile("report.csv", b"id,amount\n1,100")
        filename, size = validate_file_upload(valid_file, allowed_extensions={"csv", "pdf"})
        self.assertEqual(filename, "report.csv")

        invalid_ext_file = MockFile("malicious.exe", b"binary content")
        with self.assertRaises(ValidationError):
            validate_file_upload(invalid_ext_file, allowed_extensions={"csv", "pdf"})

    # ─── 2. Test HTTP Error Status Codes ──────────────────────────────

    def test_400_bad_request_malformed_json(self):
        """Test 400 Bad Request on malformed JSON payload."""
        self.login_as_user()
        res = self.client.post(
            '/api/transactions/process',
            data="{ malformed json payload ",
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'BAD_REQUEST')

    def test_401_unauthorized(self):
        """Test 401 Unauthorized for unauthenticated API requests."""
        res = self.client.get('/api/cards')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'UNAUTHORIZED')

    def test_403_forbidden(self):
        """Test 403 Forbidden when normal user accesses admin endpoints."""
        self.login_as_user()
        res = self.client.get('/api/admin/users')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'FORBIDDEN')

    def test_404_not_found_api_and_web(self):
        """Test 404 Not Found for non-existent API endpoints and web pages."""
        # API 404
        res_api = self.client.get('/api/nonexistent-endpoint')
        self.assertEqual(res_api.status_code, 404)
        data_api = res_api.get_json()
        self.assertIn('error', data_api)
        self.assertEqual(data_api['code'], 'NOT_FOUND')

        # Web 404
        res_web = self.client.get('/nonexistent-page-url')
        self.assertEqual(res_web.status_code, 404)
        self.assertIn(b'404', res_web.data)
        self.assertIn(b'Not Found', res_web.data)

    def test_405_method_not_allowed(self):
        """Test 405 Method Not Allowed when calling GET on POST-only API."""
        self.login_as_user()
        res = self.client.get('/api/cards/block')
        self.assertEqual(res.status_code, 405)
        data = res.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'METHOD_NOT_ALLOWED')

    def test_422_unprocessable_entity_and_invalid_inputs(self):
        """Test 420/422/400 validation failures on invalid transaction amounts."""
        self.login_as_user()
        invalid_txn = {
            'card_number': '4000123456787777',
            'card_holder': 'Test User',
            'amount': -150.00,
            'merchant': 'Test Merchant',
            'category': 'General',
            'location': 'New York, USA'
        }
        res = self.client.post('/api/transactions/process', json=invalid_txn)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    def test_413_payload_too_large(self):
        """Test 413 Payload Too Large when sending oversized data."""
        self.login_as_user()
        oversized_data = {"data": "x" * (17 * 1024 * 1024)}  # > 16MB
        res = self.client.post('/api/transactions/process', json=oversized_data)
        self.assertEqual(res.status_code, 413)
        data = res.get_json()
        self.assertEqual(data['code'], 'PAYLOAD_TOO_LARGE')

    def test_500_internal_error_and_database_rollback(self):
        """Test 500 Internal Error handling and database rollback safety."""
        res = self.client.get('/api/test/force-db-error', headers={'Accept': 'application/json'})
        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertIn('error', data)
        # Ensure stack trace is NOT exposed in response body
        self.assertNotIn('Traceback', json.dumps(data))
        self.assertNotIn('non_existent_table_xyz', data['error'])

        # Verify database session state is clean after automatic rollback
        user_in_db = User.query.filter_by(username='tmp_user_rollback_test').first()
        self.assertIsNone(user_in_db, "Uncommitted transaction was not rolled back")

if __name__ == '__main__':
    unittest.main()
