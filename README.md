# FraudShield - Credit Card Fraud Detection System

A real-time credit card fraud detection web application with admin analytics dashboard, transaction monitoring, and automated security alerts.

## Features

- **Real-time Fraud Detection** — ML-enhanced rule-based scoring engine that analyzes transactions instantly
- **Admin Analytics Dashboard** — Rich charts and statistics showing fraud trends, risk distributions, and geographic patterns
- **Transaction Monitoring** — Live transaction feed with search, filter, and detailed inspection capabilities
- **Security Alerts** — Automatic alerts for suspicious transactions with severity levels (Critical, High, Medium)
- **Card Blocking** — Instantly block/unblock compromised cards to prevent further fraud
- **Configurable Rules** — Toggle fraud detection rules and adjust thresholds from the settings panel
- **Transaction Simulation** — Built-in simulator to generate test data for demo and testing purposes

## Tech Stack

- **Backend:** Python Flask
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Charts:** Chart.js
- **Database:** SQLite
- **Icons:** Font Awesome 6

## Quick Start

### 🐳 Option A: Docker Deployment (Recommended for Production)

Run the containerized application with Gunicorn, non-root security, persistent volumes, and health monitoring:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start services
docker compose up --build -d

# 3. View live logs
docker compose logs -f

# 4. Stop services (preserving data)
docker compose down
```

- **Web UI:** `http://127.0.0.1:5000`
- **Health Check:** `http://127.0.0.1:5000/health`
- **Default Admin:** `admin` / `admin123`
- *For advanced Docker orchestration, volume backups, and PostgreSQL clustering, see [DOCKER_GUIDE.md](DOCKER_GUIDE.md).*

---

### 💻 Option B: Local Python Setup

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Run the Application
```bash
python app.py
```

#### 3. Open in Browser & Login
Navigate to **http://127.0.0.1:5000** (`admin` / `admin123`).


## How the Fraud Detection Engine Works

The system uses a **Hybrid Scoring Engine** (70% ML + 30% Rules):

### 1. Machine Learning Model (70% Weight)
The core intelligence is powered by a **Random Forest Classifier** trained on 100,000+ transactions from the `creditcard_2023.csv` dataset. It analyzes:
- **PCA Features (V1-V28):** Captured relationships between transaction metadata.
- **Transaction Amount:** Pattern matching for outlier amounts.
- **Efficiency:** The model achieved **99.98% Accuracy** on the training set.

### 2. Heuristic Rules (30% Weight)
A rule-based layer adds expert knowledge to catch common fraud patterns:
- **International Risk:** Flagging high-risk countries like Nigeria, Russia, etc.
- **Velocity Checks:** Identifying multiple high-value transactions in short windows.
- **Card-Not-Present Risk:** Higher scores for CNP-prone categories like Crypto or Gift Cards.
- **Device Security:** Flagging VPNs, Tor, and unknown devices.

### 3. Final Risk Assessment
- **Score (0-100):** Weighted average of ML and Rule scores.
- **Risk Levels:**
    - **CRITICAL (Score >= 80):** Immediate alert and automated blocking.
    - **HIGH (Score >= 65):** Flagged for manual review.
    - **MEDIUM (Score >= 40):** Notification sent to security.
    - **LOW (Score < 40):** Approved transaction.
|--------|--------|-------------|
| Amount Score | 25% | Flags unusually high transaction amounts |
| Velocity Score | 20% | Detects rapid successive transactions on same card |
| Pattern Score | 20% | Identifies high-risk merchant categories |
| Geo Score | 15% | Flags transactions from high-risk countries |
| Time Score | 10% | Detects transactions during unusual hours (12AM-5AM) |
| Device Score | 10% | Identifies suspicious devices (VPN, Tor, Unknown) |

**Risk Levels:**
- **Low** (0-39%) — Transaction approved
- **Medium** (40-64%) — Alert generated, transaction approved
- **High** (65-79%) — Transaction declined, alert triggered
- **Critical** (80-100%) — Transaction blocked, critical alert raised

## Pages

| Page | Description |
|------|-------------|
| `/dashboard` | Overview stats, weekly trends, recent transactions and alerts |
| `/transactions` | Full transaction list with search, filters, and detail view |
| `/analytics` | Charts for fraud categories, risk distribution, hourly/monthly trends, locations |
| `/alerts` | Security alert feed with severity indicators |
| `/settings` | Fraud rules configuration, blocked cards management, data simulation |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/transactions` | List transactions (paginated, filterable) |
| POST | `/api/transactions/process` | Process new transaction through fraud engine |
| POST | `/api/transactions/:id/review` | Review a flagged transaction |
| GET | `/api/analytics/overview` | Analytics data for all charts |
| GET | `/api/alerts` | Get all security alerts |
| POST | `/api/alerts/:id/read` | Mark alert as read |
| POST | `/api/cards/block` | Block a card |
| POST | `/api/cards/unblock` | Unblock a card |
| GET | `/api/blocked-cards` | List blocked cards |
| POST | `/api/simulate` | Generate simulated transactions |
| GET | `/api/fraud-rules` | Get fraud detection rules |
| POST | `/api/fraud-rules/:id/toggle` | Toggle a fraud rule on/off |

## License

MIT
