import pytest
from app.models.user import User
from app.models.audit import AdminAction
from app.extensions import db

class TestAdminManagement:
    """Test suite for Admin endpoints and user management capabilities."""

    def test_admin_user_listing(self, admin_client, test_user):
        """Test admin can list users with pagination."""
        res = admin_client.get('/api/admin/users')
        assert res.status_code == 200
        data = res.get_json()

        assert 'users' in data
        assert 'total' in data
        assert data['total'] >= 2
        usernames = [u['username'] for u in data['users']]
        assert test_user.username in usernames

    def test_admin_user_listing_filtering_by_role(self, admin_client, test_user, admin_user):
        """Test admin user listing filter by role."""
        res = admin_client.get('/api/admin/users?role=admin')
        assert res.status_code == 200
        data = res.get_json()
        roles = [u['role'] for u in data['users']]
        assert all(r == 'admin' for r in roles)

    def test_admin_user_listing_filtering_by_status(self, admin_client, blocked_user):
        """Test admin user listing filter by active/blocked status."""
        res = admin_client.get('/api/admin/users?status=blocked')
        assert res.status_code == 200
        data = res.get_json()
        statuses = [u['is_active'] for u in data['users']]
        assert all(s is False for s in statuses)

    def test_admin_user_search(self, admin_client, test_user):
        """Test searching for users by username pattern."""
        res = admin_client.get(f'/api/admin/users?search={test_user.username[:4]}')
        assert res.status_code == 200
        data = res.get_json()
        assert len(data['users']) >= 1
        assert any(u['username'] == test_user.username for u in data['users'])

    def test_admin_block_user(self, admin_client, test_user, app):
        """Test admin can block a user account."""
        res = admin_client.post(f'/api/admin/users/{test_user.id}/block', json={
            'reason': 'Suspicious card usage detected'
        })
        assert res.status_code == 200
        data = res.get_json()
        assert 'blocked' in data.get('message', '').lower()

        with app.app_context():
            u = User.query.get(test_user.id)
            assert u.is_active is False

            action = AdminAction.query.filter_by(target_user_id=test_user.id, action_type='user_block').first()
            assert action is not None

    def test_admin_unblock_user(self, admin_client, blocked_user, app):
        """Test admin can unblock a previously blocked user account."""
        res = admin_client.post(f'/api/admin/users/{blocked_user.id}/unblock')
        assert res.status_code == 200
        data = res.get_json()
        assert 'unblocked' in data.get('message', '').lower()

        with app.app_context():
            u = User.query.get(blocked_user.id)
            assert u.is_active is True

    def test_admin_self_block_prevention(self, admin_client, admin_user):
        """Test admin cannot block or deactivate their own account."""
        res = admin_client.post(f'/api/admin/users/{admin_user.id}/block')
        assert res.status_code == 400
        data = res.get_json()
        assert 'cannot' in data.get('error', '').lower()

    def test_admin_update_user_role(self, admin_client, test_user, app):
        """Test admin can promote user role."""
        res = admin_client.patch(f'/api/admin/users/{test_user.id}', json={
            'role': 'admin',
            'reason': 'Promoted to admin'
        })
        assert res.status_code == 200

        with app.app_context():
            u = User.query.get(test_user.id)
            assert u.role == 'admin'

    def test_unauthorized_admin_access_unauthenticated(self, client):
        """Test unauthenticated user is rejected from admin routes."""
        res = client.get('/api/admin/users', headers={'Accept': 'application/json'})
        assert res.status_code == 401

    def test_unauthorized_admin_access_regular_user(self, authenticated_client):
        """Test authenticated regular user is forbidden from admin endpoints."""
        res = authenticated_client.get('/api/admin/users', headers={'Accept': 'application/json'})
        assert res.status_code == 403

        block_res = authenticated_client.post('/api/admin/users/1/block', headers={'Accept': 'application/json'})
        assert block_res.status_code == 403
