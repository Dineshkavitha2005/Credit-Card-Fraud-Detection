"""
Comprehensive Configuration Security & Validation Test Suite.
Verifies that:
1. ProductionConfig strictly rejects missing, short (<16 chars), and unsafe placeholder SECRET_KEYs.
2. DevelopmentConfig strictly requires an explicit secret and rejects unsafe placeholders without silent fallbacks.
3. TestingConfig strictly requires an explicit TEST_SECRET_KEY / SECRET_KEY and rejects unsafe placeholders without in-memory fallbacks.
4. Base Config and create_app enforce strict validation across all runtime environments.
5. No hidden or silent in-memory fallback secret generation occurs.
"""

import os
import unittest
from unittest.mock import patch
from app.config import (
    Config, DevelopmentConfig, ProductionConfig, TestingConfig,
    UNSAFE_SECRET_KEYS, is_unsafe_secret
)
from app import create_app


class TestConfigurationSecurity(unittest.TestCase):
    """Test suite for configuration security and secret key validation."""

    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    # ─── 1. Helper Function is_unsafe_secret Tests ─────────────────────────

    def test_is_unsafe_secret_detects_empty_and_placeholders(self):
        """Test is_unsafe_secret returns True for empty, short, and placeholder keys."""
        # Empty / None
        self.assertTrue(is_unsafe_secret(""))
        self.assertTrue(is_unsafe_secret(None))
        self.assertTrue(is_unsafe_secret("   "))

        # Known placeholders
        for unsafe in UNSAFE_SECRET_KEYS:
            self.assertTrue(is_unsafe_secret(unsafe), f"Failed to detect placeholder: {unsafe}")

        # Short strings (< 16 characters)
        self.assertTrue(is_unsafe_secret("short_key"))
        self.assertTrue(is_unsafe_secret("123456789012345"))  # 15 chars

        # Valid strong strings (>= 16 characters, not placeholder)
        self.assertFalse(is_unsafe_secret("strong-secure-secret-key-for-environment-2026"))
        self.assertFalse(is_unsafe_secret("a" * 32))
        self.assertFalse(is_unsafe_secret("0123456789abcdef0123456789abcdef"))

    # ─── 2. ProductionConfig Validation Tests ───────────────────────────────

    def test_production_config_rejects_missing_secret(self):
        """Test ProductionConfig.validate() raises ValueError when SECRET_KEY is missing or empty."""
        with patch.dict(os.environ, {'SECRET_KEY': '', 'FLASK_ENV': 'production'}, clear=True):
            class EmptyProdConfig(ProductionConfig):
                SECRET_KEY = ''

            with self.assertRaises(ValueError) as ctx:
                EmptyProdConfig.validate()
            self.assertIn("Production configuration requires a strong, explicit SECRET_KEY", str(ctx.exception))

    def test_production_config_rejects_unsafe_placeholders(self):
        """Test ProductionConfig.validate() rejects all known default/unsafe placeholders."""
        for placeholder in ['your_secret_key_here', 'change_this_secret_key_in_production', 'default-unsafe-key', 'secret']:
            class PlaceholderProdConfig(ProductionConfig):
                SECRET_KEY = placeholder

            with self.assertRaises(ValueError):
                PlaceholderProdConfig.validate()

    def test_production_config_rejects_short_secret(self):
        """Test ProductionConfig.validate() rejects keys shorter than 16 characters."""
        class ShortProdConfig(ProductionConfig):
            SECRET_KEY = "too_short_key"

        with self.assertRaises(ValueError):
            ShortProdConfig.validate()

    def test_production_config_accepts_valid_secret(self):
        """Test ProductionConfig.validate() succeeds with a secure secret and PostgreSQL URI."""
        class ValidProdConfig(ProductionConfig):
            SECRET_KEY = "production-super-secure-session-signing-secret-key-64hex"
            SQLALCHEMY_DATABASE_URI = "postgresql://fraud_user:secret_pass@localhost:5432/fraud_db"

        # Should not raise any exception
        ValidProdConfig.validate()
        self.assertEqual(ValidProdConfig.DEBUG, False)
        self.assertEqual(ValidProdConfig.SESSION_COOKIE_SECURE, True)

    def test_production_config_rejects_missing_database_url(self):
        """Test ProductionConfig.validate() strictly rejects missing DATABASE_URL."""
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            class MissingDbProdConfig(ProductionConfig):
                SECRET_KEY = "production-super-secure-session-signing-secret-key-64hex"
                SQLALCHEMY_DATABASE_URI = ""

            with self.assertRaises(ValueError) as ctx:
                MissingDbProdConfig.validate()
            self.assertIn("Production configuration requires a PostgreSQL database", str(ctx.exception))

    def test_production_config_rejects_sqlite_database_url(self):
        """Test ProductionConfig.validate() strictly refuses to start if DATABASE_URL points to SQLite."""
        for sqlite_uri in ['sqlite:///fraud_detection.db', 'sqlite:////app/data/fraud_detection.db', 'sqlite:///:memory:']:
            class SqliteProdConfig(ProductionConfig):
                SECRET_KEY = "production-super-secure-session-signing-secret-key-64hex"
                SQLALCHEMY_DATABASE_URI = sqlite_uri

            with self.assertRaises(ValueError) as ctx:
                SqliteProdConfig.validate()
            self.assertIn("refuses to start with SQLite", str(ctx.exception))

    def test_production_config_rejects_non_postgres_database_url(self):
        """Test ProductionConfig.validate() rejects non-PostgreSQL URIs."""
        for bad_uri in ['mysql://user:pass@localhost/db', 'mongodb://localhost:27017/db']:
            class BadDbProdConfig(ProductionConfig):
                SECRET_KEY = "production-super-secure-session-signing-secret-key-64hex"
                SQLALCHEMY_DATABASE_URI = bad_uri

            with self.assertRaises(ValueError) as ctx:
                BadDbProdConfig.validate()
            self.assertIn("requires a PostgreSQL database URI", str(ctx.exception))

    # ─── 3. DevelopmentConfig Validation Tests ──────────────────────────────

    def test_development_config_rejects_missing_secret(self):
        """Test DevelopmentConfig.validate() raises ValueError when no secret is configured."""
        with patch.dict(os.environ, {'SECRET_KEY': '', 'DEV_SECRET_KEY': ''}, clear=True):
            class EmptyDevConfig(DevelopmentConfig):
                SECRET_KEY = ''

            with self.assertRaises(ValueError) as ctx:
                EmptyDevConfig.validate()
            self.assertIn("Development configuration requires an explicit SECRET_KEY or DEV_SECRET_KEY", str(ctx.exception))

    def test_development_config_rejects_unsafe_placeholder(self):
        """Test DevelopmentConfig.validate() rejects unsafe placeholder secrets without silent fallback."""
        class PlaceholderDevConfig(DevelopmentConfig):
            SECRET_KEY = 'your_secret_key_here'

        with self.assertRaises(ValueError):
            PlaceholderDevConfig.validate()

    def test_development_config_accepts_explicit_secret(self):
        """Test DevelopmentConfig.validate() succeeds with a valid development secret."""
        class ValidDevConfig(DevelopmentConfig):
            SECRET_KEY = "dev-explicit-configured-secret-key-32bytes"

        ValidDevConfig.validate()
        self.assertEqual(ValidDevConfig.DEBUG, True)

    # ─── 4. TestingConfig Validation Tests ──────────────────────────────────

    def test_testing_config_rejects_missing_secret(self):
        """Test TestingConfig.validate() raises ValueError when neither TEST_SECRET_KEY nor SECRET_KEY is set."""
        with patch.dict(os.environ, {'SECRET_KEY': '', 'TEST_SECRET_KEY': ''}, clear=True):
            class EmptyTestConfig(TestingConfig):
                SECRET_KEY = ''

            with self.assertRaises(ValueError) as ctx:
                EmptyTestConfig.validate()
            self.assertIn("Testing configuration requires an explicit TEST_SECRET_KEY or SECRET_KEY", str(ctx.exception))

    def test_testing_config_rejects_unsafe_placeholder(self):
        """Test TestingConfig.validate() rejects unsafe placeholder secrets without in-memory fallback."""
        class PlaceholderTestConfig(TestingConfig):
            SECRET_KEY = 'default-unsafe-key'

        with self.assertRaises(ValueError):
            PlaceholderTestConfig.validate()

    def test_testing_config_accepts_valid_test_secret(self):
        """Test TestingConfig.validate() succeeds with a valid test secret key."""
        class ValidTestConfig(TestingConfig):
            SECRET_KEY = "test-explicit-deterministic-secret-key-32bytes"

        ValidTestConfig.validate()
        self.assertEqual(ValidTestConfig.TESTING, True)
        self.assertEqual(ValidTestConfig.SQLALCHEMY_DATABASE_URI, 'sqlite:///:memory:')

    # ─── 5. No In-Memory Fallback Verification ─────────────────────────────

    def test_no_silent_in_memory_token_fallback(self):
        """Verify that omitting SECRET_KEY does NOT create an ephemeral in-memory token."""
        # Ensure environment has no keys
        with patch.dict(os.environ, {'SECRET_KEY': '', 'DEV_SECRET_KEY': '', 'TEST_SECRET_KEY': ''}, clear=True):
            class MissingKeyConfig(Config):
                SECRET_KEY = ''

            # Must raise ValueError, NOT silently generate secrets.token_hex(32)
            with self.assertRaises(ValueError):
                MissingKeyConfig.validate()

    def test_create_app_rejects_unsafe_configuration(self):
        """Verify create_app factory immediately raises ValueError for unsafe configuration."""
        class BadConfig(Config):
            SECRET_KEY = 'your_secret_key_here'

        with self.assertRaises(ValueError):
            create_app(BadConfig)

    def test_create_app_rejects_production_with_sqlite(self):
        """Verify create_app factory strictly refuses to start in production if DATABASE_URL is SQLite."""
        class SqliteProdAppConfig(ProductionConfig):
            SECRET_KEY = "production-super-secure-session-signing-secret-key-64hex"
            SQLALCHEMY_DATABASE_URI = "sqlite:///local_leak.db"

        with self.assertRaises(ValueError) as ctx:
            create_app(SqliteProdAppConfig)
        self.assertIn("refuses to start with SQLite", str(ctx.exception))

    def test_development_config_permits_sqlite(self):
        """Verify DevelopmentConfig permits SQLite by default."""
        class DevConfig(DevelopmentConfig):
            SECRET_KEY = "dev-explicit-configured-secret-key-32bytes"

        DevConfig.validate()
        self.assertIn("sqlite", DevConfig.SQLALCHEMY_DATABASE_URI.lower())



if __name__ == '__main__':
    unittest.main()
