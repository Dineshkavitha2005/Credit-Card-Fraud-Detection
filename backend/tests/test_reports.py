import os
import pytest
from app.models.report import Report
from app.models.transaction import Transaction
from app.extensions import db

class TestReports:
    """Test suite for CSV/PDF report generation, filters, and authorization."""

    def test_csv_report_generation(self, authenticated_client, sample_genuine_transaction, app):
        """Test generating a CSV report creates the file and database record."""
        # Create a transaction
        authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)

        res = authenticated_client.post('/api/reports/generate', json={
            'report_type': 'transaction_report',
            'format': 'csv',
            'title': 'Test CSV Report'
        })
        assert res.status_code == 200
        data = res.get_json()

        assert data['status'] == 'completed'
        assert data['file_format'] == 'csv'
        assert 'report_id' in data

        report_id = data['report_id']
        with app.app_context():
            report = Report.query.get(report_id)
            assert report is not None
            assert report.file_format == 'csv'
            assert report.file_path is not None
            full_path = os.path.join(app.config['REPORTS_DIR'], report.file_path)
            assert os.path.exists(full_path)
            assert report.file_size > 0

    def test_pdf_report_generation(self, authenticated_client, sample_genuine_transaction, app):
        """Test generating a PDF report creates the file and database record."""
        # Create a transaction
        authenticated_client.post('/api/transactions/process', json=sample_genuine_transaction)

        res = authenticated_client.post('/api/reports/generate', json={
            'report_type': 'dashboard_summary_report',
            'format': 'pdf',
            'title': 'Executive PDF Summary'
        })
        assert res.status_code == 200
        data = res.get_json()

        assert data['status'] == 'completed'
        assert data['file_format'] == 'pdf'
        assert 'report_id' in data

        report_id = data['report_id']
        with app.app_context():
            report = Report.query.get(report_id)
            assert report is not None
            assert report.file_format == 'pdf'
            assert report.file_path is not None
            full_path = os.path.join(app.config['REPORTS_DIR'], report.file_path)
            assert os.path.exists(full_path)

    def test_report_download_own_report(self, authenticated_client, sample_genuine_transaction):
        """Test user can download their own generated report."""
        gen_res = authenticated_client.post('/api/reports/generate', json={
            'report_type': 'transaction_report',
            'format': 'csv'
        })
        report_id = gen_res.get_json()['report_id']

        dl_res = authenticated_client.get(f'/api/reports/{report_id}/download')
        assert dl_res.status_code == 200
        assert dl_res.mimetype in ['text/csv', 'application/octet-stream', 'text/plain']

    def test_report_authorization_other_user_forbidden(self, client, test_user, admin_user, app):
        """Test standard user cannot download another user's report."""
        # Generate report as admin_user
        client.post('/login', data={'username': admin_user.username, 'password': 'AdminPass123!'}, follow_redirects=True)
        gen_res = client.post('/api/reports/generate', json={'format': 'csv', 'title': 'Admin Secret Report'})
        report_id = gen_res.get_json()['report_id']
        client.get('/logout')

        # Try to download as test_user
        client.post('/login', data={'username': test_user.username, 'password': 'TestPass123!'}, follow_redirects=True)
        dl_res = client.get(f'/api/reports/{report_id}/download')
        # Should return 404 (not found for this user) or 403
        assert dl_res.status_code in [403, 404]

    def test_report_generation_with_invalid_filters(self, authenticated_client):
        """Test report generation gracefully handles invalid/malformed filter criteria without crash."""
        res = authenticated_client.post('/api/reports/generate', json={
            'report_type': 'transaction_report',
            'format': 'csv',
            'filters': {
                'start_date': 'invalid-date-format',
                'end_date': '2099-99-99',
                'is_fraud': 'not_a_bool',
                'risk_level': 'invalid_level'
            }
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'completed'

    def test_list_reports_endpoint(self, authenticated_client):
        """Test listing generated reports."""
        authenticated_client.post('/api/reports/generate', json={'format': 'csv', 'title': 'List Test'})
        res = authenticated_client.get('/api/reports')
        assert res.status_code == 200
        data = res.get_json()
        assert 'reports' in data
        assert len(data['reports']) >= 1
