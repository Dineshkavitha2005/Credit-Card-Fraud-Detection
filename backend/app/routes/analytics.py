from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, func

from app.models.transaction import Transaction, BlockedCard
from app.models.alert import Alert
from app.models.encryption import mask_card_number

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    """Get high-level metric stats for dashboard cards"""
    if current_user.role == 'admin':
        txns = Transaction.query.all()
    else:
        txns = Transaction.query.filter_by(user_id=current_user.id).all()

    total_cnt = len(txns)
    fraud_cnt = sum(1 for t in txns if t.is_fraud)
    total_amt = sum(t.amount for t in txns)
    fraud_amt = sum(t.amount for t in txns if t.is_fraud)

    return jsonify({
        'total_transactions': total_cnt,
        'fraud_alerts': fraud_cnt,
        'total_volume': round(total_amt, 2),
        'fraud_volume': round(fraud_amt, 2),
        'fraud_rate': round((fraud_cnt / total_cnt * 100) if total_cnt > 0 else 0.0, 2)
    })


@analytics_bp.route('/api/dashboard/overview', methods=['GET'])
@login_required
def dashboard_overview():
    """Get complete dashboard overview: KPI cards, charts, recent transactions & alerts"""
    query = Transaction.query

    if current_user.role != 'admin':
        query = query.filter_by(user_id=current_user.id)

    # Filtering parameters
    search = request.args.get('search', '').strip()
    status_param = request.args.get('status', '').strip()
    is_fraud_param = request.args.get('is_fraud')
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.transaction_id.ilike(pattern),
                Transaction.card_holder.ilike(pattern),
                Transaction.merchant.ilike(pattern),
                Transaction.category.ilike(pattern),
                Transaction.location.ilike(pattern)
            )
        )

    if status_param and status_param != 'all':
        query = query.filter_by(status=status_param)

    if is_fraud_param is not None and is_fraud_param != 'all':
        is_fraud_bool = str(is_fraud_param).lower() in ('true', '1')
        query = query.filter_by(is_fraud=is_fraud_bool)

    if start_date_str:
        try:
            dt_start = datetime.fromisoformat(start_date_str)
            query = query.filter(Transaction.timestamp >= dt_start)
        except Exception:
            pass

    if end_date_str:
        try:
            dt_end = datetime.fromisoformat(end_date_str)
            query = query.filter(Transaction.timestamp <= dt_end)
        except Exception:
            pass

    txns = query.order_by(Transaction.timestamp.desc()).all()

    # KPI Calculation
    total_txns = len(txns)
    total_amount = sum(t.amount for t in txns)
    fraud_txns = sum(1 for t in txns if t.is_fraud)
    fraud_rate = round((fraud_txns / total_txns * 100) if total_txns > 0 else 0.0, 2)
    high_risk_txns = sum(1 for t in txns if (t.fraud_score or 0.0) >= 65.0)
    blocked_txns = sum(1 for t in txns if t.status == 'blocked')
    fraud_saved = sum(t.amount for t in txns if t.is_fraud and t.status in ('blocked', 'declined'))
    blocked_cards_cnt = BlockedCard.query.filter_by(is_active=True).count()
    unread_alerts_cnt = Alert.query.filter_by(is_read=False).count()

    kpi = {
        'total_transactions': total_txns,
        'total_amount': round(total_amount, 2),
        'fraudulent_transactions': fraud_txns,
        'fraud_rate': fraud_rate,
        'high_risk_transactions': high_risk_txns,
        'blocked_transactions': blocked_txns,
        'fraud_amount_saved': round(fraud_saved, 2),
        'blocked_cards': blocked_cards_cnt,
        'unread_alerts': unread_alerts_cnt
    }

    # Charts Calculation
    genuine_cnt = total_txns - fraud_txns
    fraud_vs_genuine = {
        'genuine_count': genuine_cnt,
        'fraud_count': fraud_txns
    }

    # Trends by Day
    days_map = {}
    for t in txns:
        if t.timestamp:
            d_str = t.timestamp.strftime('%Y-%m-%d')
            if d_str not in days_map:
                days_map[d_str] = {'date': d_str, 'total': 0, 'fraud': 0, 'amount': 0.0}
            days_map[d_str]['total'] += 1
            if t.is_fraud:
                days_map[d_str]['fraud'] += 1
            days_map[d_str]['amount'] += t.amount
    trends_by_day = sorted(list(days_map.values()), key=lambda x: x['date'])

    # Trends by Month
    months_map = {}
    for t in txns:
        if t.timestamp:
            m_str = t.timestamp.strftime('%Y-%m')
            if m_str not in months_map:
                months_map[m_str] = {'month': m_str, 'total': 0, 'fraud': 0}
            months_map[m_str]['total'] += 1
            if t.is_fraud:
                months_map[m_str]['fraud'] += 1
    trends_by_month = sorted(list(months_map.values()), key=lambda x: x['month'])

    # Risk Distribution (5 levels)
    r_low = sum(1 for t in txns if (t.fraud_score or 0) < 20)
    r_med = sum(1 for t in txns if 20 <= (t.fraud_score or 0) < 50)
    r_high = sum(1 for t in txns if 50 <= (t.fraud_score or 0) < 80)
    r_crit = sum(1 for t in txns if 80 <= (t.fraud_score or 0) < 100)
    r_extr = sum(1 for t in txns if (t.fraud_score or 0) >= 100)
    risk_distribution = [
        {'level': 'Low (0-20)', 'count': r_low},
        {'level': 'Medium (20-50)', 'count': r_med},
        {'level': 'High (50-80)', 'count': r_high},
        {'level': 'Critical (80-100)', 'count': r_crit},
        {'level': 'Extreme (100+)', 'count': r_extr}
    ]

    # Hourly Pattern (24 hours)
    hours_cnt = [0] * 24
    for t in txns:
        if t.timestamp:
            hours_cnt[t.timestamp.hour] += 1
    hourly_pattern = [{'hour': h, 'count': hours_cnt[h]} for h in range(24)]

    # Amount Distribution (5 ranges)
    a_50 = sum(1 for t in txns if t.amount < 50)
    a_200 = sum(1 for t in txns if 50 <= t.amount < 200)
    a_500 = sum(1 for t in txns if 200 <= t.amount < 500)
    a_1000 = sum(1 for t in txns if 500 <= t.amount < 1000)
    a_above = sum(1 for t in txns if t.amount >= 1000)
    amount_distribution = [
        {'range': '< $50', 'count': a_50},
        {'range': '$50 - $200', 'count': a_200},
        {'range': '$200 - $500', 'count': a_500},
        {'range': '$500 - $1000', 'count': a_1000},
        {'range': '> $1000', 'count': a_above}
    ]

    # Top Categories
    cat_map = {}
    for t in txns:
        cat = t.category or 'General'
        if cat not in cat_map:
            cat_map[cat] = {'category': cat, 'count': 0, 'amount': 0.0}
        cat_map[cat]['count'] += 1
        cat_map[cat]['amount'] += t.amount
    top_categories = sorted(list(cat_map.values()), key=lambda x: x['count'], reverse=True)[:5]

    # High Risk Locations
    loc_map = {}
    for t in txns:
        if t.is_fraud or (t.fraud_score or 0) >= 50:
            loc = t.location or 'Unknown'
            loc_map[loc] = loc_map.get(loc, 0) + 1
    high_risk_locations = [{'location': k, 'count': v} for k, v in sorted(loc_map.items(), key=lambda x: x[1], reverse=True)[:5]]

    charts = {
        'fraud_vs_genuine': fraud_vs_genuine,
        'trends_by_day': trends_by_day,
        'trends_by_month': trends_by_month,
        'risk_distribution': risk_distribution,
        'hourly_pattern': hourly_pattern,
        'amount_distribution': amount_distribution,
        'top_categories': top_categories,
        'high_risk_locations': high_risk_locations
    }

    # Recent Transactions
    recent_transactions = [{
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
    } for t in txns[:10]]

    # Recent Alerts
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(10).all()
    recent_alerts = [{
        'id': a.id,
        'transaction_id': a.transaction_id,
        'alert_type': a.alert_type,
        'severity': a.severity,
        'message': a.message,
        'is_read': a.is_read,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in alerts]

    return jsonify({
        'kpi': kpi,
        'charts': charts,
        'recent_transactions': recent_transactions,
        'recent_alerts': recent_alerts
    })


@analytics_bp.route('/api/analytics/overview', methods=['GET'])
@login_required
def analytics_overview():
    """Get detailed analytics charts data"""
    if current_user.role == 'admin':
        txns = Transaction.query.all()
    else:
        txns = Transaction.query.filter_by(user_id=current_user.id).all()

    categories = {}
    for t in txns:
        cat = t.category or 'General'
        categories[cat] = categories.get(cat, 0.0) + t.amount

    return jsonify({
        'category_breakdown': categories,
        'total_transactions': len(txns)
    })
