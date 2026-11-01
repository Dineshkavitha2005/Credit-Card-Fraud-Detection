import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.extensions import db, audit_logger, EventType
from app.models.transaction import Transaction, BlockedCard
from app.models.alert import Alert
from app.models.rule import FraudRule
from app.models.encryption import CardEncryption, mask_card_number
from app.services.fraud_detection import fraud_engine, sanitize_numpy_types
from validators import validate_amount

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get list of transactions for current user (or all if admin)"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status_filter = request.args.get('status', '').strip()
    is_fraud_filter = request.args.get('is_fraud')

    if current_user.role == 'admin':
        query = Transaction.query
    else:
        query = Transaction.query.filter_by(user_id=current_user.id)

    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if is_fraud_filter is not None and is_fraud_filter != 'all':
        is_fraud_bool = is_fraud_filter.lower() in ('true', '1')
        query = query.filter_by(is_fraud=is_fraud_bool)

    query = query.order_by(Transaction.timestamp.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'transactions': [{
            'id': t.id,
            'transaction_id': t.transaction_id,
            'card_number': mask_card_number(t.card_number),
            'card_holder': t.card_holder,
            'amount': t.amount,
            'merchant': t.merchant,
            'category': t.category,
            'location': t.location,
            'is_fraud': t.is_fraud,
            'fraud_score': t.fraud_score,
            'status': t.status,
            'timestamp': t.timestamp.isoformat() if t.timestamp else None
        } for t in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': pagination.per_page
    })


@transactions_bp.route('/api/transactions/process', methods=['POST'])
@login_required
def process_transaction():
    """Process incoming transaction and perform real-time fraud analysis"""
    data = request.get_json() or {}
    amount_str = data.get('amount')
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid transaction amount'}), 400

    raw_card = data.get('card_number', '')
    masked_card = mask_card_number(raw_card)

    blocked = BlockedCard.query.filter_by(card_number=masked_card, is_active=True).first()
    if blocked:
        audit_logger.log_event(
            EventType.TRANSACTION_SUBMISSION,
            user_id=current_user.id,
            status='failure',
            target_resource='Transaction',
            details={'reason': 'Card blocked', 'card': masked_card}
        )
        return jsonify({'error': 'Transaction declined: Credit card is blocked for security reasons.'}), 403

    analysis = fraud_engine.analyze_transaction({
        'amount': amount,
        'card_number': masked_card,
        'merchant': data.get('merchant', 'Unknown Merchant'),
        'category': data.get('category', 'General'),
        'location': data.get('location', 'Unknown Location'),
        'ip_address': request.remote_addr,
        'device_type': data.get('device_type', 'Desktop'),
        'timestamp': datetime.utcnow().isoformat()
    })

    txn_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    is_fraud = analysis.get('is_fraud', False)
    status = 'blocked' if is_fraud else 'approved'

    txn = Transaction(
        user_id=current_user.id,
        transaction_id=txn_id,
        card_number=masked_card,
        card_holder=current_user.full_name or current_user.username,
        amount=amount,
        merchant=data.get('merchant', 'Unknown Merchant'),
        category=data.get('category', 'General'),
        location=data.get('location', 'Unknown Location'),
        ip_address=request.remote_addr,
        device_type=data.get('device_type', 'Desktop'),
        is_fraud=is_fraud,
        fraud_score=analysis.get('fraud_score', 0.0),
        status=status,
        risk_factors=analysis.get('risk_factors', []),
        timestamp=datetime.utcnow()
    )
    db.session.add(txn)

    if is_fraud:
        alert = Alert(
            transaction_id=txn_id,
            alert_type='HIGH_FRAUD_RISK',
            severity='Critical',
            message=f"High risk transaction detected ({analysis.get('fraud_score')}% score) for ${amount:,.2f}"
        )
        db.session.add(alert)

    db.session.commit()

    audit_logger.log_event(
        EventType.TRANSACTION_SUBMISSION,
        user_id=current_user.id,
        status='success',
        target_resource=f"Transaction:{txn_id}",
        details={'transaction_id': txn_id, 'amount': amount, 'is_fraud': is_fraud}
    )

    return jsonify(sanitize_numpy_types({
        'message': 'Transaction processed',
        'transaction_id': txn_id,
        'status': status,
        'analysis': analysis,
        'model_version': analysis.get('model_version', 'v2.0.0'),
        'fraud_score': analysis.get('fraud_score'),
        'is_fraud': is_fraud,
        'risk_level': analysis.get('risk_level'),
        'ml_probability': analysis.get('ml_probability'),
        'ml_score': analysis.get('ml_score'),
        'rule_score': analysis.get('rule_score'),
        'score_difference': analysis.get('score_difference'),
        'primary_driver': analysis.get('primary_driver'),
        'risk_factors': analysis.get('risk_factors', [])
    }))


@transactions_bp.route('/api/transactions/<transaction_id>/review', methods=['POST'])
@login_required
def review_transaction(transaction_id):
    """Review and resolve transaction alert status"""
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return jsonify({'error': 'Transaction not found'}), 404

    data = request.get_json() or {}
    new_status = data.get('status', 'reviewed')

    txn.status = new_status
    txn.reviewed_by = current_user.username
    txn.reviewed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': f'Transaction {transaction_id} marked as {new_status}'})


@transactions_bp.route('/api/transactions/history', methods=['GET'])
@login_required
def transaction_history():
    """Get transaction history list"""
    txns = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(50).all()
    return jsonify({
        'transactions': [{
            'id': t.id,
            'transaction_id': t.transaction_id,
            'card_number': mask_card_number(t.card_number),
            'amount': t.amount,
            'merchant': t.merchant,
            'status': t.status,
            'is_fraud': t.is_fraud,
            'fraud_score': t.fraud_score,
            'timestamp': t.timestamp.isoformat() if t.timestamp else None
        } for t in txns]
    })


@transactions_bp.route('/api/transactions/<transaction_id>/details', methods=['GET'])
@login_required
def transaction_details(transaction_id):
    """Get detailed record for transaction"""
    if current_user.role == 'admin':
        txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    else:
        txn = Transaction.query.filter_by(transaction_id=transaction_id, user_id=current_user.id).first()

    if not txn:
        return jsonify({'error': 'Transaction not found'}), 404

    return jsonify({
        'transaction_id': txn.transaction_id,
        'card_number': mask_card_number(txn.card_number),
        'card_holder': txn.card_holder,
        'amount': txn.amount,
        'merchant': txn.merchant,
        'category': txn.category,
        'location': txn.location,
        'ip_address': txn.ip_address,
        'device_type': txn.device_type,
        'is_fraud': txn.is_fraud,
        'fraud_score': txn.fraud_score,
        'status': txn.status,
        'risk_factors': txn.risk_factors or [],
        'timestamp': txn.timestamp.isoformat() if txn.timestamp else None
    })


@transactions_bp.route('/api/transactions/statistics', methods=['GET'])
@login_required
def transaction_statistics():
    """Get transaction statistics breakdown"""
    if current_user.role == 'admin':
        txns = Transaction.query.all()
    else:
        txns = Transaction.query.filter_by(user_id=current_user.id).all()

    total_cnt = len(txns)
    fraud_cnt = sum(1 for t in txns if t.is_fraud)
    total_amt = sum(t.amount for t in txns)
    fraud_amt = sum(t.amount for t in txns if t.is_fraud)

    return jsonify({
        'total_count': total_cnt,
        'fraud_count': fraud_cnt,
        'total_amount': total_amt,
        'fraud_amount': fraud_amt,
        'fraud_rate': round((fraud_cnt / total_cnt * 100) if total_cnt > 0 else 0, 2)
    })


@transactions_bp.route('/api/transactions/export', methods=['GET'])
@login_required
def export_transactions():
    """Export transactions to CSV or PDF based on query filters"""
    import io
    import csv
    from app.services.reporting import query_filtered_transactions_data
    from utils import ReportGenerator

    fmt = request.args.get('format', 'csv').lower()
    txns = query_filtered_transactions_data(request.args.to_dict(), current_user)

    if fmt == 'pdf':
        buffer = io.BytesIO()
        ReportGenerator.generate_pdf('transaction_report', 'Transaction Export Report', txns, filters=request.args.to_dict(), output_path=buffer)
        pdf_bytes = buffer.getvalue()
        response = make_response(pdf_bytes)
        response.headers["Content-Disposition"] = "attachment; filename=transactions_export.pdf"
        response.headers["Content-type"] = "application/pdf"
        return response

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Transaction ID', 'Card Number', 'Amount', 'Merchant', 'Category', 'Status', 'Is Fraud', 'Fraud Score', 'Timestamp'])

    for t in txns:
        writer.writerow([
            t.transaction_id,
            mask_card_number(t.card_number),
            t.amount,
            t.merchant,
            t.category,
            t.status,
            t.is_fraud,
            t.fraud_score,
            t.timestamp.isoformat() if t.timestamp else ''
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=transactions_export.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


@transactions_bp.route('/api/simulate', methods=['POST'])
@login_required
def simulate_transaction():
    """Simulate a transaction run or batch simulation without persisting"""
    data = request.get_json() or {}
    count = data.get('count')

    if count is not None:
        try:
            count = min(max(int(count), 1), 500)
        except (ValueError, TypeError):
            count = 10

        import random
        merchants = [
            ('Apple Store', 'Electronics', 'USA', 1200.00),
            ('Amazon Marketplace', 'Online Shopping', 'USA', 84.50),
            ('Binance Exchange', 'Cryptocurrency', 'Russia', 8500.00),
            ('Local Grocery Mart', 'Groceries', 'USA', 42.10),
            ('Luxury Watch Boutique', 'Luxury', 'France', 4200.00),
            ('Global Wire Services', 'Wire Transfer', 'Nigeria', 12500.00),
            ('Starbucks Coffee', 'General', 'USA', 6.75),
            ('CryptoGift Cards Outlet', 'Gift Cards', 'Romania', 3200.00),
            ('Shell Gas Station', 'General', 'USA', 55.00),
            ('Target Superstore', 'Supermarket', 'USA', 124.80)
        ]
        devices = ['Desktop', 'Mobile Safari', 'Android App', 'TOR Browser VPN', 'Unknown Proxy']

        simulated_results = []
        fraud_count = 0

        for i in range(count):
            m_name, m_cat, m_loc, base_amt = random.choice(merchants)
            amt_jitter = random.uniform(0.7, 1.4)
            sim_amt = round(base_amt * amt_jitter, 2)
            sim_dev = random.choice(devices)
            
            sim_payload = {
                'amount': sim_amt,
                'merchant': m_name,
                'category': m_cat,
                'location': m_loc,
                'device_type': sim_dev,
                'timestamp': datetime.utcnow().isoformat()
            }
            res = fraud_engine.analyze_transaction(sim_payload)
            if res.get('is_fraud', False) or res.get('fraud_score', 0) >= 65:
                fraud_count += 1
            simulated_results.append({
                'id': i + 1,
                'merchant': m_name,
                'category': m_cat,
                'amount': sim_amt,
                'location': m_loc,
                'fraud_score': res.get('fraud_score'),
                'is_fraud': res.get('is_fraud'),
                'risk_level': res.get('risk_level')
            })

        return jsonify(sanitize_numpy_types({
            'message': f'Simulation of {count} transactions completed',
            'count': count,
            'fraud_detected': fraud_count,
            'simulated_transactions': simulated_results[:25]
        }))

    analysis = fraud_engine.analyze_transaction(data)
    return jsonify(sanitize_numpy_types({
        'analysis': analysis,
        'fraud_score': analysis.get('fraud_score'),
        'is_fraud': analysis.get('is_fraud')
    }))


@transactions_bp.route('/api/fraud-rules', methods=['GET'])
@login_required
def get_fraud_rules():
    """Get active fraud detection rules"""
    rules = FraudRule.query.all()
    return jsonify({
        'rules': [{
            'id': r.id,
            'rule_name': r.rule_name,
            'rule_type': r.rule_type,
            'threshold': r.threshold,
            'is_active': r.is_active,
            'description': r.description
        } for r in rules]
    })


@transactions_bp.route('/api/fraud-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_fraud_rule(rule_id):
    """Toggle fraud rule state"""
    rule = FraudRule.query.get(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    rule.is_active = not rule.is_active
    db.session.commit()
    return jsonify({'message': f'Rule {rule.rule_name} {"activated" if rule.is_active else "deactivated"}'})
