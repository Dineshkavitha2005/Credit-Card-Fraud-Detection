# 🛡️ Sentinel Backend Architecture

The **Sentinel** backend is a modular, enterprise-grade Python application providing real-time credit card fraud detection, deterministic feature engineering, machine learning inference, cryptographic card masking, and security audit logging.

---

## 📁 Directory Structure

```text
backend/
├── app/                         # Core Modular Application Package
│   ├── models/                  # SQLAlchemy ORM Database Models
│   │   ├── user.py              # User, UserCard, UserSession, UserIdentity, LoginAttempt
│   │   ├── transaction.py       # Transaction, BlockedCard
│   │   ├── alert.py             # Alert, SuspiciousActivity
│   │   ├── rule.py              # FraudRule (configurable heuristics)
│   │   ├── audit.py             # AuditLog, AdminAction, RateLimitRecord
│   │   ├── report.py            # Report metadata
│   │   └── encryption.py        # Fernet AES card encryption & masking
│   ├── routes/                  # Blueprint Route Handlers
│   │   ├── main.py              # Root, dashboard, landing, healthcheck, sitemap
│   │   ├── auth.py              # Login, register, logout, Google OAuth, 2FA
│   │   ├── transactions.py      # Transaction creation, listing, review, simulation
│   │   ├── cards.py             # User card management & emergency lock
│   │   ├── admin.py             # System admin controls, user management, audit trails
│   │   ├── analytics.py         # Aggregated risk metrics & chart endpoints
│   │   └── reports.py           # On-demand CSV and executive PDF generation
│   ├── services/                # Core Business & Domain Services
│   │   ├── fraud_detection.py   # Hybrid ML + Rule-based scoring engine
│   │   ├── authentication.py    # Multi-step authentication & session tokens
│   │   ├── oauth_service.py     # Google OAuth 2.0 integration
│   │   ├── card_service.py      # Card validation & vault operations
│   │   ├── admin_service.py     # Administrative actions & rule mutations
│   │   └── reporting.py         # Summary analytics & PDF builder
│   ├── config.py                # Environment configurations (Dev, Prod, Testing)
│   ├── extensions.py            # Initialized extensions (db, cors, login_manager, audit_logger)
│   └── __init__.py              # Application factory `create_app()`, error handlers, headers
│
├── core/                        # Infrastructure & Shared Utilities
│   ├── audit_logger.py          # Asynchronous audit engine with automated data sanitization
│   ├── errors.py                # Standardized exception hierarchy (APIError, 4xx, 5xx)
│   ├── validators.py            # Input sanitization, password strength, card Luhn checks
│   ├── utils.py                 # PDF generation, geolocation, email delivery
│   └── __init__.py              # Core package exports
│
├── ml/                          # Machine Learning & Data Pipeline
│   ├── preprocessor.py          # Deterministic feature engineering & risk transformations
│   ├── train_model.py           # Reproducible model training pipeline
│   ├── fraud_model.pkl          # Trained Random Forest classifier artifact
│   ├── scaler.pkl               # Fitted StandardScaler artifact
│   ├── features.pkl             # Canonical feature order schema
│   ├── model_metadata.json      # Model version, classification threshold, AUC metrics
│   ├── preprocessing_config.json # Feature weights and country risk tables
│   ├── creditcard_2023.csv      # Anonymized training & validation dataset
│   └── __init__.py              # ML package exports
│
├── tests/                       # Automated Test Suite (pytest)
├── requirements.txt             # Python dependencies
├── run.py                       # Local development server entry point
├── wsgi.py                      # WSGI production callable
└── gunicorn.conf.py             # Production Gunicorn worker configuration
```

---

## 🚀 Running the Backend

### Standalone Local Development
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start backend server
python run.py
```

### Production Execution (WSGI / Gunicorn)
```bash
gunicorn --config backend/gunicorn.conf.py backend.wsgi:app
```

---

## 🧠 Machine Learning Engine

Sentinel pairs deterministic rule-based checks with a Random Forest classifier trained on transactional patterns.
- **Artifact Resolution**: The engine dynamically locates model artifacts (`fraud_model.pkl`, `scaler.pkl`, `preprocessing_config.json`) within `backend/ml/`.
- **Zero Synthetic Randoms**: Feature engineering is 100% deterministic using PCA components, velocity scoring, and temporal sine/cosine hour cycles.
- **Safe Serialization**: `sanitize_numpy_types()` ensures all model scores and probabilities serialize cleanly to JSON.

---

## 🔒 Security Architecture

1. **Card Number Masking**: Raw primary account numbers (PAN) are never stored in plain text. Stored records are encrypted with Fernet symmetric AES encryption and displayed in masked format (`•••• •••• •••• 1234`).
2. **Audit Logging**: Asynchronous logging thread pool records administrative actions, auth failures, and high-risk anomalies without impacting HTTP request latency.
3. **HTTP Hardening**: Production responses enforce HSTS (`Strict-Transport-Security`), `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and `X-Robots-Tag: noindex` for private endpoints.

