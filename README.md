# 🛡️ Sentinel — Credit Card Fraud Detection System

Enterprise-grade real-time credit card fraud detection web application featuring machine learning inference, heuristics scoring, an executive analytics dashboard, live transaction monitoring, and automated security alerting.

---

## 🏛️ Project Architecture: Separated Frontend & Backend

The repository is cleanly separated into independent **`frontend/`** and **`backend/`** folders, alongside operational configurations and centralized documentation in **`docs/`**:

```text
Credit-Card-Fraud-Detection/
├── frontend/                     # Dedicated Frontend Workspace
│   ├── static/                   # Static Client Assets
│   │   ├── css/                  # Stylesheets (sentinel.css, landing.css, ui-states.css)
│   │   ├── js/                   # Vanilla JS modules (sentinel.js, landing-motion.js, ui-states.js)
│   │   ├── img/                  # High-DPI favicons, logos, brand assets, preview graphics
│   │   └── site.webmanifest      # PWA Web Manifest
│   ├── templates/                # Jinja2 HTML Templates (auth, dashboard, admin, seo, base)
│   └── README.md                 # Frontend design system & component documentation
│
├── backend/                      # Dedicated Backend Workspace
│   ├── app/                      # Application Package (Factory, Blueprints, Extensions)
│   │   ├── models/               # SQLAlchemy ORM Models (User, Transaction, Alert, Audit, Rule)
│   │   ├── routes/               # Blueprint Controllers (auth, admin, transactions, analytics)
│   │   ├── services/             # Core Business Logic (fraud_detection, authentication, reports)
│   │   ├── config.py             # Environment Configurations (Dev, Prod, Testing)
│   │   ├── extensions.py         # Extensions (db, cors, login_manager, audit_logger)
│   │   └── __init__.py           # Flask App Factory with security headers & dynamic asset pathing
│   ├── core/                     # Shared Infrastructure Modules
│   │   ├── audit_logger.py       # Asynchronous Audit Logging Engine
│   │   ├── errors.py             # Exception Hierarchy & JSON Error Formatters
│   │   ├── validators.py         # Input Sanitization, Password Strength & Luhn Checks
│   │   └── utils.py              # Geolocation, PDF Reports & Email Service
│   ├── ml/                       # Machine Learning & Data Pipeline
│   │   ├── preprocessor.py       # Deterministic Feature Engineering
│   │   ├── train_model.py        # Model Training & Threshold Calibration Pipeline
│   │   ├── fraud_model.pkl       # Trained Random Forest Classifier
│   │   ├── scaler.pkl            # Fitted StandardScaler
│   │   ├── features.pkl          # Feature Alignment Schema
│   │   ├── model_metadata.json   # Model Metrics, Versioning & Classification Threshold
│   │   ├── preprocessing_config.json # Category & Country Risk Dictionaries
│   │   └── creditcard_2023.csv    # Training / Benchmark Dataset
│   ├── tests/                    # Backend Pytest Suite
│   ├── requirements.txt          # Python Dependencies
│   ├── run.py                    # Standalone Backend Runner
│   ├── wsgi.py                   # Production WSGI Application Callable
│   ├── gunicorn.conf.py          # Production Gunicorn Worker Configuration
│   └── README.md                 # Backend architecture & security documentation
│
├── docs/                         # Centralized Guides & Documentation
│   ├── DATABASE_SETUP.md         # Database provisioning & PostgreSQL migrations
│   ├── DEVELOPER_GUIDE.md        # Comprehensive developer workflow & standards
│   ├── DOCKER_GUIDE.md           # Production Docker deployment & orchestration
│   ├── IMPLEMENTATION_DETAILS.md # Deep-dive technical implementation notes
│   ├── IMPLEMENTATION_SUMMARY.md # Feature release notes & executive overview
│   ├── SECURITY_SETUP.md         # Cryptographic card vault & defense-in-depth setup
│   ├── TRANSACTION_HISTORY_FEATURES.md # Transaction ledger capabilities
│   └── TRANSACTION_HISTORY_QUICKSTART.md # Getting started with transactions
│
├── nginx/                        # Nginx Reverse Proxy with TLS termination & rate limiting
├── scripts/                      # Operational Scripts (assets, audits, database backups)
├── tests/                        # Root-level test suite & node test runner
├── Dockerfile                    # Multi-stage hardened production Docker container
├── docker-compose.yml            # Local development Docker stack
├── docker-compose.prod.yml       # Production TLS-terminated Docker stack
├── entrypoint.sh                 # Database migration & startup entrypoint
├── run.py                        # Root convenience launcher (`python run.py`)
├── wsgi.py                       # Root WSGI alias
├── requirements.txt              # Root requirements file
├── pytest.ini                    # Pytest test discovery configuration
└── README.md                     # Project overview and quick start guide
```

---

## ⚡ Quick Start

### 🐳 Option A: Docker Deployment (Recommended)

Run the containerized stack with Gunicorn, non-root security, persistent data volumes, and health monitoring:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start services
docker compose up --build -d

# 3. View live logs
docker compose logs -f
```

- **Web UI:** `http://127.0.0.1:5000`
- **Health Check:** `http://127.0.0.1:5000/health`
- **Default Admin:** `admin` / `admin123`
- *For advanced Docker orchestration, volume backups, and PostgreSQL clustering, see [DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md).*

---

### 💻 Option B: Local Setup

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Run the Application
You can run directly from the root:
```bash
python run.py
```
Or run directly from the backend directory:
```bash
cd backend
python run.py
```

#### 3. Open in Browser
Navigate to **http://127.0.0.1:5000** and log in with `admin` / `admin123`.

---

## 🧪 Running Tests

### Python Backend Suite (Pytest)
```bash
pytest
```

### Node.js Frontend Suite (Theme Engine & Request Cancellation)
```bash
node tests/test_theme_node.js
node tests/test_cancellation_node.js
```

---

## 🧠 Fraud Detection Engine

Sentinel employs a **Hybrid Scoring Engine** combining machine learning inference with heuristic rules:

| Component | Weight | Key Capabilities |
| :--- | :--- | :--- |
| **Random Forest ML Classifier** | **70%** | Analyzes PCA transaction features (`V1`-`V28`), logarithmic amounts, and normalized transaction velocity. |
| **Heuristic Rules Engine** | **30%** | Evaluates geographic risk, night transaction hours (12AM-5AM), CNP categories (crypto, gift cards), and velocity thresholds. |

### Calibrated Risk Classification
- **LOW (< 40)**: Approved automatically.
- **MEDIUM (40 - 64)**: Approved; alert flagged for monitoring.
- **HIGH (65 - 79)**: Declined; flagged for security review.
- **CRITICAL (>= 80)**: Declined; card locked immediately, critical alert raised.

---

## 📚 Documentation Reference

Detailed documentation is organized in the [`docs/`](docs/) directory:
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Database Setup & Migrations](docs/DATABASE_SETUP.md)
- [Docker Production Deployment](docs/DOCKER_GUIDE.md)
- [Security & Card Vault Architecture](docs/SECURITY_SETUP.md)
- [Frontend Architecture](frontend/README.md)
- [Backend Architecture](backend/README.md)

---

## 📄 License
MIT
