#!/usr/bin/env python
"""
Smoke test to verify the authentication system routes, models, and rules.
"""

import pytest
from app import app, init_db
from models import User, db, FraudRule, UserCard, Transaction, Alert, BlockedCard, AuditLog, UserSession

def test_authentication_smoke_system():
    """Verify auth routes, bcrypt password hashing, models, and default admin user."""
    with app.app_context():
        init_db()
        
        # Test 1: Check routes exist
        routes = [
            ('/register', 'GET', 'User Registration'),
            ('/login', 'GET', 'User Login'),
            ('/logout', 'GET', 'User Logout'),
            ('/profile', 'GET', 'User Profile'),
            ('/api/profile', 'POST', 'Update Profile'),
            ('/api/change-password', 'POST', 'Change Password'),
            ('/api/cards', 'GET', 'Get Cards'),
            ('/api/cards', 'POST', 'Add Card'),
        ]
        
        for route, method, name in routes:
            found = False
            for rule in app.url_map.iter_rules():
                if rule.rule == route and method in rule.methods:
                    found = True
                    break
            assert found, f"Route {route} [{method}] not found"
        
        # Test 2: Password hashing
        test_user = User(username='test_user_smoke', email='test_smoke@example.com')
        password = 'SecurePass123'
        test_user.set_password(password)
        
        assert test_user.check_password(password) is True
        assert test_user.check_password('WrongPassword!') is False
        
        # Test 3: Check database models
        models = [
            (User, 'User'),
            (UserCard, 'UserCard'),
            (Transaction, 'Transaction'),
            (Alert, 'Alert'),
            (FraudRule, 'FraudRule'),
            (BlockedCard, 'BlockedCard'),
            (AuditLog, 'AuditLog'),
            (UserSession, 'UserSession'),
        ]
        for model_class, model_name in models:
            assert model_class is not None
        
        # Test 4: Verify admin user exists
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.role == 'admin'
        
        # Test 5: Check fraud rules
        rule_count = FraudRule.query.count()
        assert rule_count >= 5

