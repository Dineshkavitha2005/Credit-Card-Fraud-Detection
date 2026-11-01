from datetime import datetime
from app.extensions import db
from app.models.user import UserCard
from app.models.transaction import BlockedCard
from app.models.encryption import CardEncryption, mask_card_number

class CardService:
    """Service for managing user credit cards and card blocking."""

    @staticmethod
    def get_user_cards(user_id):
        """Fetch active user cards with decrypted card numbers."""
        cards = UserCard.query.filter_by(user_id=user_id, is_active=True).all()
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
        return result

    @staticmethod
    def block_card(card_number, reason=None, blocked_by='system'):
        """Block a credit card for security/fraud reasons."""
        masked = mask_card_number(card_number)
        blocked = BlockedCard.query.filter_by(card_number=masked).first()
        if not blocked:
            blocked = BlockedCard(
                card_number=masked,
                reason=reason or 'Automated fraud protection block',
                blocked_by=blocked_by,
                is_active=True
            )
            db.session.add(blocked)
            db.session.commit()
        return blocked
