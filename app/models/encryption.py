import os
from cryptography.fernet import Fernet

def mask_card_number(card_number):
    """Mask credit card number to format **** **** **** 1234"""
    if not card_number:
        return ""
    clean = str(card_number).replace(" ", "").replace("-", "").strip()
    if clean.startswith("****") or clean.startswith("••••"):
        return card_number
    if len(clean) < 4:
        return "**** **** **** ****"
    last4 = clean[-4:]
    return f"**** **** **** {last4}"


class CardEncryption:
    """Utility class for card encryption/decryption"""
    
    UNSAFE_KEYS = {
        'default-unsafe-key',
        'use_Fernet.generate_key()',
        'your_secret_key_here',
        'change_this_secret_key_in_production',
        'secret',
        'key',
        '123456',
        'password'
    }

    @staticmethod
    def validate_key():
        """Validate encryption key from environment. Raise ValueError if unsafe or missing."""
        key = os.getenv('CARD_ENCRYPTION_KEY', '').strip()
        if not key:
            raise ValueError("CARD_ENCRYPTION_KEY environment variable is missing.")
        if key in CardEncryption.UNSAFE_KEYS or len(key) < 16:
            raise ValueError("CARD_ENCRYPTION_KEY is unsafe, insecure, or using a default placeholder.")
        return key

    @staticmethod
    def get_cipher():
        """Get validated Fernet cipher instance"""
        validated_key = CardEncryption.validate_key()
        import base64
        try:
            key_bytes = validated_key.encode('utf-8')
            return Fernet(key_bytes)
        except Exception:
            import hashlib
            derived = base64.urlsafe_b64encode(hashlib.sha256(validated_key.encode('utf-8')).digest())
            return Fernet(derived)

    @staticmethod
    def encrypt_card_number(card_number):
        """Encrypt credit card number using Fernet key"""
        if not card_number:
            return card_number
        cipher = CardEncryption.get_cipher()
        return cipher.encrypt(str(card_number).encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_card_number(encrypted_card):
        """Decrypt credit card number using Fernet key"""
        if not encrypted_card:
            return encrypted_card
        cipher = CardEncryption.get_cipher()
        try:
            return cipher.decrypt(str(encrypted_card).encode('utf-8')).decode('utf-8')
        except Exception:
            return encrypted_card
