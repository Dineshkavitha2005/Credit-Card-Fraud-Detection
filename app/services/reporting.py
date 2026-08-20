import os
import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy import or_
from app.extensions import db, audit_logger, EventType
from app.models.transaction import Transaction
from app.models.report import Report
from utils import ReportGenerator

def query_filtered_transactions_data(filters, user):
    """Query transactions based on filter parameters and user access permissions."""
    query = Transaction.query
    if user.role != 'admin':
        query = query.filter_by(user_id=user.id)

    if not isinstance(filters, dict):
        filters = {}

    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    if start_date:
        try:
            dt_start = datetime.fromisoformat(start_date)
            query = query.filter(Transaction.timestamp >= dt_start)
        except (ValueError, TypeError):
            pass
    if end_date:
        try:
            dt_end = datetime.fromisoformat(end_date)
            query = query.filter(Transaction.timestamp <= dt_end)
        except (ValueError, TypeError):
            pass

    status = filters.get('status')
    if status and status != 'all':
        query = query.filter_by(status=status)

    is_fraud = filters.get('is_fraud')
    if is_fraud is not None and is_fraud != 'all':
        is_fraud_bool = str(is_fraud).lower() in ('true', '1')
        query = query.filter_by(is_fraud=is_fraud_bool)

    risk_level = filters.get('risk_level')
    if risk_level and risk_level != 'all':
        if risk_level == 'low':
            query = query.filter(Transaction.fraud_score < 20.0)
        elif risk_level == 'medium':
            query = query.filter(Transaction.fraud_score >= 20.0, Transaction.fraud_score < 50.0)
        elif risk_level == 'high':
            query = query.filter(or_(Transaction.fraud_score >= 50.0, Transaction.is_fraud == True))
        elif risk_level == 'critical':
            query = query.filter(Transaction.fraud_score >= 80.0)

    return query.order_by(Transaction.timestamp.desc()).all()


class ReportingService:
    """Service for handling PDF and CSV report creation and downloads."""

    @staticmethod
    def generate_report(user, data):
        """Generate actual PDF or CSV report and save to secure directory."""
        report_type = data.get('report_type', 'transaction_report')
        file_format = (data.get('format') or data.get('file_format') or 'pdf').lower()
        if file_format not in ('csv', 'pdf'):
            file_format = 'pdf'
            
        filters = data.get('filters', {})
        if not isinstance(filters, dict):
            filters = {}

        if user.role != 'admin':
            filters['user_id'] = user.id

        transactions = query_filtered_transactions_data(filters, user)

        title_map = {
            'csv_transaction_report': 'CSV Transaction Detail Report',
            'pdf_transaction_report': 'PDF Transaction Detail Report',
            'transaction_report': f"{file_format.upper()} Transaction Detail Report",
            'fraud_analysis_report': 'Fraud Analysis & Vulnerability Report',
            'dashboard_summary_report': 'Dashboard Executive Summary Report',
            'dashboard_summary': 'Dashboard Executive Summary Report'
        }
        report_title = data.get('title') or title_map.get(report_type, f"{report_type.replace('_', ' ').title()}")

        file_ext = 'pdf' if file_format == 'pdf' else 'csv'
        unique_filename = f"report_{user.id}_{uuid.uuid4().hex[:12]}.{file_ext}"
        reports_dir = current_app.config['REPORTS_DIR']
        output_filepath = os.path.abspath(os.path.join(reports_dir, unique_filename))

        if file_format == 'csv':
            ReportGenerator.generate_csv(transactions, output_path=output_filepath)
        else:
            ReportGenerator.generate_pdf(report_type, report_title, transactions, filters=filters, output_path=output_filepath)

        file_size = os.path.getsize(output_filepath) if os.path.exists(output_filepath) else 0

        report = Report(
            user_id=user.id,
            report_type=report_type,
            title=report_title,
            description=f"Generated {file_format.upper()} report with {len(transactions)} transaction records",
            file_path=unique_filename,
            file_format=file_format,
            file_size=file_size,
            filters=filters,
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()

        audit_logger.log_event(
            EventType.REPORT_GENERATION,
            user_id=user.id,
            status='success',
            target_resource=f"Report:{report.id}",
            details={'report_id': report.id, 'report_type': report_type, 'file_format': file_format, 'title': report_title}
        )

        return report
