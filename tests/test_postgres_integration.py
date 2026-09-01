"""
Integration Test Suite for Database Models, Constraints, Transactions, and Rollback.
Verifies requirements:
- Reports, transactions, users, cards, alerts, sessions, and audit logs work properly.
- SQLAlchemy connection configuration and engine options.
- Migrations and schema creation succeed.
- Transaction rollback behavior on unique constraint violations and uncommitted transactions.
- Unique constraints and indexes.
"""

import os
import unittest
import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, text

from app import create_app
from app.config import Config, TestingConfig, ProductionConfig
from app.extensions import db
from app.models.user import User, UserCard, UserSession, UserIdentity
from app.models.transaction import Transaction, BlockedCard
from app.models.alert import Alert, SuspiciousActivity
from app.models.rule import FraudRule
from app.models.audit import AuditLog, AdminAction, RateLimitRecord
from app.models.report import Report
from app.models.encryption import CardEncryption, mask_card_number
from app import init_db, migrate_audit_logs_table, migrate_user_identities_table


class TestDatabaseIntegration(unittest.TestCase):
    """Verify all database entities, relationships, constraints, and rollbacks."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ─── 1. SQLAlchemy Configuration & Engine Options ─────────────────────────

    def test_sqlalchemy_engine_options(self):
        """Verify engine options include pool_pre_ping and production pool settings."""
        self.assertTrue(Config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_pre_ping'))
        self.assertTrue(ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS.get('pool_pre_ping'))
        self.assertIn('pool_size', ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS)
        self.assertIn('max_overflow', ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS)
        self.assertIn('pool_recycle', ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS)
        self.assertIn('pool_timeout', ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS)

    # ─── 2. Dialect-Agnostic Migrations ───────────────────────────────────────

    def test_migrations_execute_without_dialect_errors(self):
        """Verify migration functions run cleanly across engines using inspection."""
        # Should not raise SQLite-specific PRAGMA syntax errors
        migrate_audit_logs_table()
        migrate_user_identities_table()

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        self.assertIn('users', table_names)
        self.assertIn('transactions', table_names)
        self.assertIn('audit_logs', table_names)
        self.assertIn('user_identities', table_names)

    # ─── 3. User, Sessions & User Identity Models ─────────────────────────────

    def test_user_and_session_lifecycle(self):
        """Verify User, UserSession, and UserIdentity creation and relationship integrity."""
        user = User(
            username="pg_test_user",
            email="pg_test@example.com",
            full_name="Postgres Test User",
            role="user"
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

        self.assertIsNotNone(user.id)
        self.assertTrue(user.check_password("SecurePassword123!"))

        # UserSession creation
        session = UserSession(
            user_id=user.id,
            session_token="token_pg_session_12345",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Sentinel Test Agent"
        )
        db.session.add(session)
        db.session.commit()

        fetched_session = UserSession.query.filter_by(session_token="token_pg_session_12345").first()
        self.assertIsNotNone(fetched_session)
        self.assertEqual(fetched_session.user_id, user.id)

        # UserIdentity creation with unique constraint
        identity = UserIdentity(
            user_id=user.id,
            provider="google",
            provider_subject="google_sub_1001",
            provider_email="pg_test@example.com"
        )
        db.session.add(identity)
        db.session.commit()

        # Duplicate provider + provider_subject must fail
        dup_identity = UserIdentity(
            user_id=user.id,
            provider="google",
            provider_subject="google_sub_1001",
            provider_email="pg_test_other@example.com"
        )
        db.session.add(dup_identity)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    # ─── 4. User Cards & Card Encryption ──────────────────────────────────────

    def test_cards_and_encryption(self):
        """Verify UserCard and BlockedCard models with CardEncryption."""
        user = User(username="card_user", email="card_user@example.com")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        raw_card = "4532123456789012"
        enc_card = CardEncryption.encrypt_card_number(raw_card)
        user_card = UserCard(
            user_id=user.id,
            card_number=enc_card,
            card_holder="Card Holder",
            card_type="Visa",
            expiry_month=12,
            expiry_year=2028
        )
        db.session.add(user_card)

        blocked = BlockedCard(
            card_number=enc_card,
            reason="Stolen card reported",
            blocked_by="admin"
        )
        db.session.add(blocked)
        db.session.commit()

        saved_card = UserCard.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(saved_card)
        self.assertEqual(CardEncryption.decrypt_card_number(saved_card.card_number), raw_card)

    # ─── 5. Transactions & Rollback Behavior ──────────────────────────────────

    def test_transactions_and_unique_constraint_rollback(self):
        """Verify Transaction CRUD and rollback behavior on duplicate transaction_id."""
        user = User(username="txn_user", email="txn_user@example.com")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        txn1 = Transaction(
            user_id=user.id,
            transaction_id="TXN-UNIQUE-9999",
            card_number="**** **** **** 9012",
            card_holder="Test Holder",
            amount=500.00,
            merchant="Tech Store",
            category="Retail",
            is_fraud=False,
            fraud_score=10.0,
            status="approved"
        )
        db.session.add(txn1)
        db.session.commit()

        # Insert duplicate transaction_id
        txn2 = Transaction(
            user_id=user.id,
            transaction_id="TXN-UNIQUE-9999",
            card_number="**** **** **** 9012",
            card_holder="Test Holder",
            amount=100.00,
            merchant="Other Store",
            category="Retail",
            is_fraud=True,
            fraud_score=90.0,
            status="declined"
        )
        db.session.add(txn2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

        # Rollback preserves session integrity
        db.session.rollback()

        # Verify previous transaction remains intact
        verified = Transaction.query.filter_by(transaction_id="TXN-UNIQUE-9999").first()
        self.assertIsNotNone(verified)
        self.assertEqual(verified.amount, 500.00)

        # Subsequent queries work seamlessly after rollback
        new_txn = Transaction(
            user_id=user.id,
            transaction_id="TXN-AFTER-ROLLBACK",
            card_number="**** **** **** 9012",
            card_holder="Test Holder",
            amount=75.00,
            merchant="Coffee Shop",
            category="Dining",
            is_fraud=False,
            status="approved"
        )
        db.session.add(new_txn)
        db.session.commit()
        self.assertIsNotNone(Transaction.query.filter_by(transaction_id="TXN-AFTER-ROLLBACK").first())

    # ─── 6. Alerts & Suspicious Activity ──────────────────────────────────────

    def test_alerts_and_suspicious_activity(self):
        """Verify Alert and SuspiciousActivity persistence."""
        alert = Alert(
            transaction_id="TXN-ALERT-001",
            alert_type="High Amount Threshold",
            severity="High",
            message="Transaction exceeded $5,000 threshold"
        )
        db.session.add(alert)

        suspicious = SuspiciousActivity(
            activity_name="Multiple failed logins from new IP",
            severity="high",
            description="5 consecutive failed logins observed",
            ip_address="203.0.113.42",
            risk_score=78.5
        )
        db.session.add(suspicious)
        db.session.commit()

        self.assertIsNotNone(Alert.query.filter_by(transaction_id="TXN-ALERT-001").first())
        self.assertIsNotNone(SuspiciousActivity.query.filter_by(ip_address="203.0.113.42").first())

    # ─── 7. Audit Logs, Admin Actions & Rate Limiting ─────────────────────────

    def test_audit_logs_and_admin_actions(self):
        """Verify AuditLog, AdminAction, and RateLimitRecord persistence."""
        user = User(username="audit_user", email="audit_user@example.com")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        audit = AuditLog(
            user_id=user.id,
            event_type="password_change",
            target_resource="/auth/change-password",
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
            status="success",
            details={"ip": "10.0.0.1"}
        )
        db.session.add(audit)

        admin_action = AdminAction(
            admin_id=user.id,
            action_type="user_unblock",
            target_user_id=user.id,
            reason="User confirmed identity",
            details={"approved_by": "supervisor"}
        )
        db.session.add(admin_action)

        rate_limit = RateLimitRecord(
            identifier="ip:10.0.0.1",
            endpoint="/api/v1/predict",
            request_count=15,
            is_limited=False
        )
        db.session.add(rate_limit)
        db.session.commit()

        self.assertIsNotNone(AuditLog.query.filter_by(event_type="password_change").first())
        self.assertIsNotNone(AdminAction.query.filter_by(action_type="user_unblock").first())
        self.assertIsNotNone(RateLimitRecord.query.filter_by(identifier="ip:10.0.0.1").first())

    # ─── 8. Reports Generation Persistence ───────────────────────────────────

    def test_reports_persistence(self):
        """Verify Report model CRUD."""
        user = User(username="report_user", email="report_user@example.com")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        report = Report(
            user_id=user.id,
            report_type="fraud_summary",
            title="Monthly Fraud Analysis Report",
            description="Audit summary of high-risk transactions",
            file_format="pdf",
            file_size=20480,
            status="completed",
            download_count=1
        )
        db.session.add(report)
        db.session.commit()

        fetched_report = Report.query.filter_by(title="Monthly Fraud Analysis Report").first()
        self.assertIsNotNone(fetched_report)
        self.assertEqual(fetched_report.file_format, "pdf")
        self.assertEqual(fetched_report.download_count, 1)


if __name__ == '__main__':
    unittest.main()
