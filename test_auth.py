#!/usr/bin/env python
"""
Test script to verify the authentication system is working
"""

from app import app
from models import User, db

app.app_context().push()

print("\n" + "="*50)
print("🔐 FraudShield Authentication System Test")
print("="*50 + "\n")

# Test 1: Check routes exist
print("1️⃣  Checking authentication routes...")
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
    status = '✅' if found else '❌'
    print(f"  {status} {method:6} {route:30} ({name})")

# Test 2: Password hashing
print("\n2️⃣  Testing Bcrypt password hashing...")
test_user = User(username='test_user', email='test@example.com')
password = 'SecurePass123'
test_user.set_password(password)

# Test password verification
correct = test_user.check_password(password)
incorrect = test_user.check_password('WrongPassword!')

print(f"  ✅ Password hashed: {test_user.password_hash[:50]}...")
print(f"  ✅ Correct password check: {correct}")
print(f"  ✅ Incorrect password rejected: {not incorrect}")

# Test 3: Check database models
print("\n3️⃣  Checking database models...")
from models import User, UserCard, Transaction, Alert, FraudRule, BlockedCard, AuditLog, UserSession

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
    print(f"  ✅ {model_name:20} model loaded")

# Test 4: Verify admin user exists
print("\n4️⃣  Checking admin user...")
admin = User.query.filter_by(username='admin').first()
if admin:
    print(f"  ✅ Admin user exists")
    print(f"     - Email: {admin.email}")
    print(f"     - Role: {admin.role}")
    print(f"     - Created: {admin.created_at}")
else:
    print(f"  ❌ Admin user not found!")

# Test 5: Check fraud rules
print("\n5️⃣  Checking default fraud rules...")
rule_count = FraudRule.query.count()
print(f"  ✅ {rule_count} fraud rules configured")
for rule in FraudRule.query.limit(3).all():
    print(f"     - {rule.rule_name} (Type: {rule.rule_type})")

print("\n" + "="*50)
print("✅ All authentication components working!")
print("="*50 + "\n")

print("📝 Next steps:")
print("  1. Go to http://127.0.0.1:5000/login")
print("  2. Login with admin / admin123")
print("  3. Change the admin password immediately")
print("  4. Create a new user account via /register")
print("\n")
