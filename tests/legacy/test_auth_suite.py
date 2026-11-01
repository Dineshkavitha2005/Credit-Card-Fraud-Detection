"""
Comprehensive Automated Test Suite for Credit Card Fraud Detection System
Tests Flask-Login Authentication, Session Management, and Role-Based Authorization
"""

import sys
import os
import unittest
import uuid
from app import app, db, User, init_db

class TestFlaskLoginAuthSystem(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            init_db()
            # Ensure normal test user exists
            normal_user = User.query.filter_by(username='testnormal').first()
            if not normal_user:
                normal_user = User(
                    username='testnormal',
                    email='testnormal@example.com',
                    full_name='Normal Test User',
                    role='user',
                    is_active=True,
                    is_verified=True
                )
                normal_user.set_password('UserPass123!')
                db.session.add(normal_user)
            
            # Ensure admin test user exists
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@fraudshield.com',
                    full_name='System Admin',
                    role='admin',
                    is_active=True,
                    is_verified=True
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
            
            db.session.commit()

    def test_1_user_login(self):
        """Test normal user login succeeds and establishes Flask-Login session"""
        res = self.client.post('/login', data={
            'username': 'testnormal',
            'password': 'UserPass123!'
        }, follow_redirects=False)
        
        # Should redirect to cards page (0 cards) or dashboard
        self.assertIn(res.status_code, [302, 200])
        
        # Verify authenticated session via protected endpoint
        profile_res = self.client.get('/profile')
        self.assertEqual(profile_res.status_code, 200)
        self.assertIn(b'testnormal', profile_res.data)

    def test_2_admin_login(self):
        """Test admin login succeeds and provides admin access"""
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=False)
        
        self.assertIn(res.status_code, [302, 200])
        
        # Access admin page
        admin_res = self.client.get('/admin/users')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'User Management', admin_res.data)

    def test_3_logout(self):
        """Test logout clears session and current_user"""
        # Login first
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        
        # Accessing protected page after logout should redirect to login
        prot_res = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(prot_res.status_code, 302)
        self.assertIn('/login', prot_res.location)

    def test_4_unprotected_access_without_login(self):
        """Test accessing protected page/API without login returns 302/401"""
        # Page request -> Redirect 302
        page_res = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(page_res.status_code, 302)
        
        # API request -> 401 Unauthorized
        api_res = self.client.get('/api/transactions', headers={'Accept': 'application/json'})
        self.assertEqual(api_res.status_code, 401)
        self.assertIn(b'Authentication required', api_res.data)

    def test_5_access_admin_page_as_normal_user(self):
        """Test normal user accessing admin page/API gets 403 Forbidden or access denied"""
        # Login as normal user
        self.client.post('/login', data={'username': 'testnormal', 'password': 'UserPass123!'})
        
        # Try accessing admin HTML page
        admin_page_res = self.client.get('/admin/users')
        self.assertEqual(admin_page_res.status_code, 403)
        self.assertIn(b'Access Denied', admin_page_res.data)
        
        # Try accessing admin API endpoint
        admin_api_res = self.client.get('/api/admin/users', headers={'Accept': 'application/json'})
        self.assertEqual(admin_api_res.status_code, 403)
        self.assertIn(b'Admin access required', admin_api_res.data)

    def test_6_access_admin_page_as_admin(self):
        """Test admin accessing admin page/API succeeds with 200 OK"""
        # Login as admin user
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Access admin HTML page
        admin_page_res = self.client.get('/admin/users')
        self.assertEqual(admin_page_res.status_code, 200)
        self.assertIn(b'User Management', admin_page_res.data)
        
        # Access admin API endpoint
        admin_api_res = self.client.get('/api/admin/users', headers={'Accept': 'application/json'})
        self.assertEqual(admin_api_res.status_code, 200)
        json_data = admin_api_res.get_json()
        self.assertIn('users', json_data)

    def test_7_admin_users_api_supports_search_filter_and_pagination(self):
        """Admin user API should support search, role filter, status filter, and pagination metadata."""
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        unique = uuid.uuid4().hex[:10]
        user = User(
            username=f'aliceadminsearch{unique}',
            email=f'aliceadminsearch{unique}@example.com',
            full_name='Alice Search User',
            role='user',
            is_active=True,
            is_verified=True
        )
        user.set_password('SearchPass123!')
        with self.app.app_context():
            db.session.add(user)
            db.session.commit()

        res = self.client.get('/api/admin/users?search=alice&role=user&status=active&page=1&per_page=10', headers={'Accept': 'application/json'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('users', data)
        self.assertIn('total', data)
        self.assertIn('page', data)
        self.assertIn('pages', data)
        self.assertGreaterEqual(data['total'], 1)

    def test_8_admin_user_detail_and_patch_update(self):
        """Admin can fetch a user and update their role and active state."""
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        with self.app.app_context():
            unique = uuid.uuid4().hex[:10]
            user = User(
                username=f'johndoeadmin{unique}',
                email=f'johndoeadmin{unique}@example.com',
                full_name='John Doe',
                role='user',
                is_active=True,
                is_verified=False
            )
            user.set_password('UserPass123!')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        detail_res = self.client.get(f'/api/admin/users/{user_id}', headers={'Accept': 'application/json'})
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn('johndoeadmin', detail_res.get_json()['username'])

        patch_res = self.client.patch(
            f'/api/admin/users/{user_id}',
            json={'role': 'admin', 'is_active': False},
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        self.assertEqual(patch_res.status_code, 200)
        payload = patch_res.get_json()
        self.assertEqual(payload['user']['role'], 'admin')
        self.assertFalse(payload['user']['is_active'])

    def test_9_admin_cannot_block_or_deactivate_their_own_active_admin_account(self):
        """Admins must not disable their own current admin account while active."""
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        with self.app.app_context():
            admin_user = User.query.filter_by(username='admin').first()
            admin_user_id = admin_user.id

        patch_res = self.client.patch(
            f'/api/admin/users/{admin_user_id}',
            json={'is_active': False},
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        self.assertEqual(patch_res.status_code, 400)
        self.assertIn('own admin account', patch_res.get_json()['error'])

        block_res = self.client.post(f'/api/admin/users/{admin_user_id}/block', headers={'Accept': 'application/json'})
        self.assertEqual(block_res.status_code, 400)
        self.assertIn('own admin account', block_res.get_json()['error'])

    def test_10_admin_cannot_delete_their_own_account(self):
        """Protect the current admin from self-deletion."""
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        with self.app.app_context():
            admin_user = User.query.filter_by(username='admin').first()
            admin_user_id = admin_user.id

        delete_res = self.client.delete(f'/api/admin/users/{admin_user_id}', headers={'Accept': 'application/json'})
        self.assertEqual(delete_res.status_code, 400)
        self.assertIn('own admin account', delete_res.get_json()['error'])

if __name__ == '__main__':
    unittest.main()
