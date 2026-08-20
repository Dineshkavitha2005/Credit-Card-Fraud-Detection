import os
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.extensions import db, audit_logger, EventType
from app.models.report import Report
from app.services.reporting import ReportingService

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate PDF/CSV report API endpoint"""
    try:
        data = request.get_json() or {}
        report = ReportingService.generate_report(current_user, data)
        return jsonify({
            'message': 'Report generated successfully',
            'report_id': report.id,
            'title': report.title,
            'file_format': report.file_format,
            'file_size': report.file_size,
            'status': 'completed'
        })
    except Exception as e:
        db.session.rollback()
        audit_logger.log_event(
            EventType.REPORT_GENERATION,
            user_id=current_user.id,
            status='failure',
            target_resource='Report',
            details={'error': str(e)}
        )
        return jsonify({'error': f"Failed to generate report: {str(e)}"}), 500


@reports_bp.route('/api/reports', methods=['GET'])
@login_required
def list_reports():
    """List generated reports for current user (or all if admin)"""
    if current_user.role == 'admin':
        reports = Report.query.order_by(Report.created_at.desc()).limit(100).all()
    else:
        reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(50).all()

    result = []
    for r in reports:
        result.append({
            'id': r.id,
            'user_id': r.user_id,
            'report_type': r.report_type,
            'title': r.title,
            'file_format': r.file_format,
            'file_size': r.file_size or 0,
            'status': r.status,
            'download_count': r.download_count or 0,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
            'filters': r.filters or {}
        })

    return jsonify({'reports': result})


@reports_bp.route('/api/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report_status(report_id):
    """Get report details & status"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    return jsonify({
        'id': report.id,
        'user_id': report.user_id,
        'status': report.status,
        'title': report.title,
        'report_type': report.report_type,
        'file_format': report.file_format,
        'file_size': report.file_size,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'completed_at': report.completed_at.isoformat() if report.completed_at else None,
        'download_count': report.download_count,
        'filters': report.filters or {}
    })


@reports_bp.route('/api/reports/<int:report_id>/download', methods=['GET'])
@login_required
def download_report(report_id):
    """Download generated report with strict authorization check & path validation"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report or report.status != 'completed' or not report.file_path:
        return jsonify({'error': 'Report not found or not available for download'}), 404

    reports_dir = current_app.config['REPORTS_DIR']
    file_path = os.path.abspath(os.path.join(reports_dir, report.file_path))

    if not file_path.startswith(reports_dir) or not os.path.exists(file_path):
        return jsonify({'error': 'Report file missing from secure storage'}), 404

    report.download_count = (report.download_count or 0) + 1
    db.session.commit()

    audit_logger.log_event(
        EventType.REPORT_DOWNLOAD,
        user_id=current_user.id,
        status='success',
        target_resource=f"Report:{report.id}",
        details={'report_id': report.id, 'title': report.title, 'file_format': report.file_format}
    )

    mimetype = 'application/pdf' if report.file_format == 'pdf' else 'text/csv'
    safe_download_name = f"{report.title.replace(' ', '_')}.{report.file_format}"

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=safe_download_name
    )


@reports_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """Safely delete report record and physical file"""
    if current_user.role == 'admin':
        report = Report.query.get(report_id)
    else:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if report.file_path:
        reports_dir = current_app.config['REPORTS_DIR']
        file_path = os.path.abspath(os.path.join(reports_dir, report.file_path))
        if file_path.startswith(reports_dir) and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    db.session.delete(report)
    db.session.commit()
    return jsonify({'message': 'Report deleted successfully'})
