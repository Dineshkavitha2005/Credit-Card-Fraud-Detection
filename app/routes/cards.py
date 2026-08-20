from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, audit_logger, EventType
from app.models.user import UserCard
from app.models.transaction import BlockedCard
from app.models.encryption import CardEncryption, mask_card_number
from validators import validate_card_number

cards_bp = Blueprint('cards', __name__)

@cards_bp.route('/api/cards', methods=['GET'])
@login_required
def get_user_cards():
    """Get active credit cards for current user"""
    cards = UserCard.query.filter_by(user_id=current_user.id, is_active=True).all()
    result = []
    for card in cards:
        raw_num = card.card_number
        try:
            decrypted = CardEncryption.decrypt_card_number(raw_num)
        except Exception:
            decrypted = raw_num
        masked = mask_card_number(decrypted)
        result.append({
            'id': card.id,
            'card_holder': card.card_holder,
            'card_number': masked,
            'card_type': card.card_type,
            'expiry_month': card.expiry_month,
            'expiry_year': card.expiry_year,
            'card_nickname': card.card_nickname,
            'is_primary': card.is_primary,
            'daily_limit': card.daily_limit,
            'monthly_limit': card.monthly_limit
        })
    return jsonify({'cards': result})


@cards_bp.route('/api/cards', methods=['POST'])
@login_required
def add_user_card():
    """Add a new user card"""
    data = request.get_json() or {}
    card_number = data.get('card_number', '').replace(' ', '').replace('-', '')
    card_holder = data.get('card_holder', '').strip()
    expiry_month = data.get('expiry_month')
    expiry_year = data.get('expiry_year')
    cvv = data.get('cvv', '').strip()
    card_nickname = data.get('card_nickname', '').strip()

    card_err = validate_card_number(card_number)
    if card_err:
        return jsonify({'error': card_err}), 400

    if not card_holder:
        return jsonify({'error': 'Cardholder name is required'}), 400

    encrypted_num = CardEncryption.encrypt_card_number(card_number)
    encrypted_cvv = CardEncryption.encrypt_card_number(cvv) if cvv else None

    # If first card, mark as primary
    existing_cnt = UserCard.query.filter_by(user_id=current_user.id, is_active=True).count()
    is_primary = (existing_cnt == 0)

    card = UserCard(
        user_id=current_user.id,
        card_number=encrypted_num,
        card_holder=card_holder,
        expiry_month=int(expiry_month or 12),
        expiry_year=int(expiry_year or 2030),
        cvv=encrypted_cvv,
        card_nickname=card_nickname,
        is_primary=is_primary
    )
    db.session.add(card)
    db.session.commit()

    return jsonify({'message': 'Card added successfully', 'card_id': card.id})


@cards_bp.route('/api/cards/<int:card_id>', methods=['DELETE'])
@login_required
def delete_user_card(card_id):
    """Soft delete user card"""
    card = UserCard.query.filter_by(id=card_id, user_id=current_user.id).first()
    if not card:
        return jsonify({'error': 'Card not found'}), 404

    card.is_active = False
    db.session.commit()
    return jsonify({'message': 'Card removed successfully'})


@cards_bp.route('/api/cards/<int:card_id>/primary', methods=['POST'])
@login_required
def set_primary_card(card_id):
    """Set specified card as primary card"""
    card = UserCard.query.filter_by(id=card_id, user_id=current_user.id).first()
    if not card:
        return jsonify({'error': 'Card not found'}), 404

    UserCard.query.filter_by(user_id=current_user.id).update({'is_primary': False})
    card.is_primary = True
    db.session.commit()

    return jsonify({'message': 'Primary card updated'})


@cards_bp.route('/api/cards/block', methods=['POST'])
@login_required
def block_card():
    """Block card route"""
    data = request.get_json() or {}
    card_num = data.get('card_number', '')
    masked = mask_card_number(card_num)

    blocked = BlockedCard.query.filter_by(card_number=masked).first()
    if not blocked:
        blocked = BlockedCard(
            card_number=masked,
            reason=data.get('reason', 'User requested block'),
            blocked_by=current_user.username,
            is_active=True
        )
        db.session.add(blocked)
        db.session.commit()

    return jsonify({'message': f'Card {masked} blocked successfully'})


@cards_bp.route('/api/cards/unblock', methods=['POST'])
@login_required
def unblock_card():
    """Unblock card route"""
    data = request.get_json() or {}
    card_num = data.get('card_number', '')
    masked = mask_card_number(card_num)

    blocked = BlockedCard.query.filter_by(card_number=masked).first()
    if blocked:
        blocked.is_active = False
        db.session.commit()

    return jsonify({'message': f'Card {masked} unblocked successfully'})


@cards_bp.route('/api/blocked-cards', methods=['GET'])
@login_required
def list_blocked_cards():
    """Get list of blocked cards"""
    blocked_cards = BlockedCard.query.filter_by(is_active=True).all()
    return jsonify({
        'blocked_cards': [{
            'id': b.id,
            'card_number': b.card_number,
            'reason': b.reason,
            'blocked_by': b.blocked_by,
            'blocked_at': b.blocked_at.isoformat() if b.blocked_at else None
        } for b in blocked_cards]
    })
