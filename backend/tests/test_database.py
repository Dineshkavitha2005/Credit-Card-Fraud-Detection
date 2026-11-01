import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.models.user import User, UserCard, UserSession
from app.models.transaction import Transaction, BlockedCard
from app.models.alert import Alert
from app.models.rule import FraudRule
from app.models.audit import AuditLog
from app.extensions import db

class TestDatabaseOperations:
    """Test suite for Database CRUD operations, constraints, and rollback behavior."""

    def test_user_crud_operations(self, app):
        """Test User model Create, Read, Update, and Delete operations."""
        with app.app_context():
            # Create
            user = User(
                username='cruduser',
                email='cruduser@example.com',
                full_name='CRUD User',
                role='user'
            )
            user.set_password('CrudPass123!')
            db.session.add(user)
            db.session.commit()

            # Read
            fetched = User.query.filter_by(username='cruduser').first()
            assert fetched is not None
            assert fetched.email == 'cruduser@example.com'

            # Update
            fetched.full_name = 'CRUD User Updated'
            fetched.phone = '+15551234567'
            db.session.commit()

            updated = User.query.filter_by(username='cruduser').first()
            assert updated.full_name == 'CRUD User Updated'
            assert updated.phone == '+15551234567'

            # Delete
            db.session.delete(updated)
            db.session.commit()

            deleted = User.query.filter_by(username='cruduser').first()
            assert deleted is None

    def test_transaction_crud_operations(self, app, test_user):
        """Test Transaction model Create, Read, Update, Delete."""
        with app.app_context():
            txn = Transaction(
                user_id=test_user.id,
                transaction_id='TXN-TEST-12345',
                card_number='**** **** **** 1092',
                card_holder=test_user.full_name,
                amount=250.00,
                merchant='Electronics MegaStore',
                category='Electronics',
                is_fraud=False,
                fraud_score=15.5,
                status='approved'
            )
            db.session.add(txn)
            db.session.commit()

            fetched_txn = Transaction.query.filter_by(transaction_id='TXN-TEST-12345').first()
            assert fetched_txn is not None
            assert fetched_txn.amount == 250.00

            # Update status
            fetched_txn.status = 'reviewed'
            db.session.commit()

            updated_txn = Transaction.query.filter_by(transaction_id='TXN-TEST-12345').first()
            assert updated_txn.status == 'reviewed'

    def test_fraud_rule_crud_operations(self, app):
        """Test FraudRule model creation and query."""
        with app.app_context():
            rule = FraudRule(
                rule_name='Extreme Amount Check',
                rule_type='amount_threshold',
                threshold=10000.0,
                is_active=True
            )
            db.session.add(rule)
            db.session.commit()

            found_rule = FraudRule.query.filter_by(rule_name='Extreme Amount Check').first()
            assert found_rule is not None
            assert found_rule.threshold == 10000.0

    def test_database_rollback_on_unique_constraint_violation(self, app):
        """Test database rolls back successfully when unique constraint is violated."""
        with app.app_context():
            user1 = User(username='unique_name', email='unique1@example.com')
            user1.set_password('Pass123!')
            db.session.add(user1)
            db.session.commit()

            # Attempt to add duplicate username
            user2 = User(username='unique_name', email='unique2@example.com')
            user2.set_password('Pass123!')
            db.session.add(user2)

            with pytest.raises(IntegrityError):
                db.session.commit()

            db.session.rollback()

            # Session should be clean and functional after rollback
            valid_user = User(username='clean_name', email='clean@example.com')
            valid_user.set_password('Pass123!')
            db.session.add(valid_user)
            db.session.commit()

            assert User.query.filter_by(username='clean_name').first() is not None

    def test_database_rollback_preserves_previous_state(self, app):
        """Test that rolling back an uncommitted transaction leaves previous data intact."""
        with app.app_context():
            initial_count = User.query.count()

            # Add a user without committing
            temp_user = User(username='temp_rollback_user', email='temp@example.com')
            temp_user.set_password('Pass123!')
            db.session.add(temp_user)

            # Rollback
            db.session.rollback()

            final_count = User.query.count()
            assert final_count == initial_count
            assert User.query.filter_by(username='temp_rollback_user').first() is None
