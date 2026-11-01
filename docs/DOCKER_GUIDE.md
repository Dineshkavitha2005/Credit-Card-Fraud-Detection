# 🐳 Production Docker & Containerization Guide
## Credit Card Fraud Detection System

This guide outlines the production container architecture, deployment commands, security hardening, data persistence, and operational workflows for the containerized **Credit Card Fraud Detection System**.

---

## 📑 Table of Contents
1. [Architecture Overview](#-architecture-overview)
2. [Prerequisites](#-prerequisites)
3. [Quick Start (Docker Compose)](#-quick-start-docker-compose)
4. [Standard Docker Compose Operations](#-standard-docker-compose-operations)
5. [Standalone Docker Commands](#-standalone-docker-commands)
6. [Environment Configuration Reference](#-environment-configuration-reference)
7. [Storage & Volume Persistence](#-storage--volume-persistence)
8. [Health Checks & Observability](#-health-checks--observability)
9. [Security Hardening](#-security-hardening)
10. [Performance Tuning & Concurrency](#-performance-tuning--concurrency)
11. [Optional PostgreSQL Database Setup](#-optional-postgresql-database-setup)
12. [Troubleshooting & Common Scenarios](#-troubleshooting--common-scenarios)

---

## 🏛️ Architecture Overview

The system is packaged as an OCI-compliant container running on top of **Python 3.11 Debian Bookworm Slim**, utilizing **Gunicorn** as a production-grade multi-threaded WSGI application server with **Flask** and **Scikit-Learn** inference engines.

```
                    +---------------------------------------+
                    |             Host / Gateway            |
                    |           (Port 5000 / HTTPS)         |
                    +-------------------+-------------------+
                                        |
+---------------------------------------v---------------------------------------+
| Docker Container: fraud_detection_app                                          |
|                                                                               |
|  +-------------------------------------------------------------------------+  |
|  | Gunicorn WSGI Server (4 workers, 2 threads, gthread)                    |  |
|  | - stdout/stderr logging                                                 |  |
|  | - memory recycling (max_requests=1000)                                  |  |
|  +------------------------------------+------------------------------------+  |
|                                       |                                       |
|  +------------------------------------v------------------------------------+  |
|  | Flask Application Instance (App Factory, Non-root user: appuser)        |  |
|  | - Auth, Transactions, Cards, Admin, Analytics, Reports Blueprints       |  |
|  | - ML Fraud Engine (Deterministic preprocessor & Scaler)                |  |
|  | - Health Probe Endpoint (/health & /api/health)                         |  |
|  +-------------------+--------------------------------+--------------------+  |
|                      |                                |                       |
+----------------------|--------------------------------|-----------------------+
                       |                                |
        +--------------v-------------+    +-------------v--------------+
        |  Docker Volume: app_data   |    | Docker Volume: reports_data|
        |  (/app/data/fraud_db.db)   |    |  (/app/instance/reports)   |
        +----------------------------+    +----------------------------+
```

---

## 📋 Prerequisites

- **Docker**: Version 20.10.0+ or newer
- **Docker Compose**: Version 2.0.0+ (`docker compose`)

Verify your installation:
```bash
docker --version
docker compose version
```

---

## 🚀 Quick Start (Docker Compose)

### 1. Configure Environment Variables
Copy the production environment template:
```bash
cp .env.example .env
```
*(Optional)* Generate fresh cryptographic secrets for production:
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate CARD_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Build and Launch
```bash
docker compose up --build -d
```

The application will be live and healthy at:
- **Web UI**: `http://localhost:5000`
- **Default Admin Account**: `admin` / `admin123`
- **Health Check Endpoint**: `http://localhost:5000/health`

---

## 🛠️ Standard Docker Compose Operations

### 1. Build Containers
Build or rebuild the application image from source:
```bash
docker compose build
```
To force a clean build without Docker cache:
```bash
docker compose build --no-cache
```

### 2. Start Services
Start services in detached background mode:
```bash
docker compose up -d
```
To build and start simultaneously:
```bash
docker compose up --build -d
```

### 3. Stop Services
Stop and remove active containers while preserving named volumes:
```bash
docker compose down
```
To stop containers AND remove persistent data volumes (⚠️ **Caution: Clears Database and Reports**):
```bash
docker compose down -v
```

### 4. View Container Logs
Stream real-time structured logs from all services:
```bash
docker compose logs -f
```
To view the last 100 lines for the application service only:
```bash
docker compose logs -f --tail=100 app
```

### 5. Restart Services
Restart the application container (useful after configuration changes):
```bash
docker compose restart
```
To restart only the web application:
```bash
docker compose restart app
```

---

## 📦 Standalone Docker Commands

If running directly with `docker run` without Docker Compose:

### 1. Build Docker Image
```bash
docker build -t credit-card-fraud-detection:latest .
```

### 2. Create Named Volumes for Persistence
```bash
docker volume create fraud_app_data
docker volume create fraud_reports_data
```

### 3. Run Container
```bash
docker run -d \
  --name fraud_detection_app \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  -v fraud_app_data:/app/data \
  -v fraud_reports_data:/app/instance/reports \
  credit-card-fraud-detection:latest
```

### 4. Inspect Container Health
```bash
docker inspect --format='{{json .State.Health}}' fraud_detection_app
```

---

## ⚙️ Environment Configuration Reference

All settings can be configured via environment variables or in `.env`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Environment mode (`production`, `development`, `testing`) |
| `PORT` | `5000` | HTTP port inside container and exposed to host |
| `SECRET_KEY` | *(Required)* | 64-character hex key for Flask session signing and CSRF tokens |
| `CARD_ENCRYPTION_KEY` | *(Required)* | 32-byte Fernet base64 key for credit card AES-128-CBC encryption |
| `DATABASE_URL` | `sqlite:////app/data/fraud_detection.db` | SQLAlchemy database connection URI |
| `WORKERS` | `4` | Number of Gunicorn worker processes |
| `THREADS` | `2` | Number of threads per Gunicorn worker process |
| `WORKER_CLASS` | `gthread` | Gunicorn worker class (`gthread` / `sync`) |
| `TIMEOUT` | `120` | Maximum request processing timeout in seconds |
| `GRACEFUL_TIMEOUT`| `30` | Graceful worker shutdown period in seconds |
| `LOG_LEVEL` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`) |
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP host for fraud alert notifications |
| `SMTP_PORT` | `587` | SMTP port (STARTTLS: 587, SSL: 465) |
| `SENDER_EMAIL` | `noreply@fraudshield.com` | System alert sender email address |
| `SENDER_PASSWORD` | *(Optional)* | SMTP application authentication password |

---

## 💾 Storage & Volume Persistence

Docker volumes guarantee that critical data survives container upgrades, rebuilds, and restarts.

### Managed Volumes:
1. **`app_data` (`/app/data`)**:
   - Stores the persistent SQLite database file `fraud_detection.db`.
   - Contains users, cards, transactions, alerts, fraud rules, sessions, and audit logs.
2. **`reports_data` (`/app/instance/reports`)**:
   - Stores generated audit reports in PDF and CSV format.
3. **ML Model Files**:
   - Packaged directly into the image: `fraud_model.pkl`, `scaler.pkl`, `features.pkl`, `model_metadata.json`, and `preprocessing_config.json`.

### Backup and Restore

#### Backup Database Volume:
```bash
docker run --rm \
  -v fraud_detection_app_data:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/fraud_db_backup_$(date +%Y%m%d).tar.gz -C /source .
```

#### Restore Database Volume:
```bash
docker run --rm \
  -v fraud_detection_app_data:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/fraud_db_backup_YYYYMMDD.tar.gz -C /target
```

---

## 🩺 Health Checks & Observability

### 1. Endpoints
The container exposes dedicated health monitoring endpoints:
- `GET /health`
- `GET /api/health`

**Sample Response (HTTP 200 OK):**
```json
{
  "status": "healthy",
  "service": "credit-card-fraud-detection",
  "database": "connected"
}
```

If the database becomes unreachable, it returns **HTTP 503 Service Unavailable** with error diagnostics:
```json
{
  "status": "degraded",
  "service": "credit-card-fraud-detection",
  "database": "unhealthy: unable to open database file"
}
```

### 2. Docker Health Check Configuration
Configured in both `Dockerfile` and `docker-compose.yml`:
- **Interval**: Every 30 seconds
- **Timeout**: 5 seconds
- **Retries**: 3 consecutive failures before marking container `unhealthy`
- **Start Period**: 15–20 seconds warm-up window for ML model loading

Check container health status:
```bash
docker ps --filter "name=fraud_detection_app"
```

---

## 🔒 Security Hardening

This container setup implements multi-layered enterprise security controls:

1. **Non-Root Execution**:
   - Runs under dedicated unprivileged user `appuser` (UID: 1001, GID: 1001).
   - Container has no root privileges, reducing attack surface.
2. **Data Minimization via `.dockerignore`**:
   - Large training datasets (`creditcard_2023.csv` 325MB) are excluded.
   - Virtual environments, `.git`, `.pytest_cache`, and temporary files are omitted.
3. **Cardholder Data Encryption**:
   - Sensitive credit card numbers are encrypted using AES-128-CBC via Fernet (`CARD_ENCRYPTION_KEY`).
   - Plaintext card numbers are never stored unmasked in database or logs.
4. **Secret Key Protection**:
   - Sessions and CSRF protection enforce strict non-default secret keys in production.
5. **Memory Leak Protection**:
   - Gunicorn recycles workers every `MAX_REQUESTS` (1000 ± 50) to prevent memory accumulation from Scikit-Learn / Pandas operations.

---

## ⚡ Performance Tuning & Concurrency

### Sizing Formula:
- **Workers**: `(2 * CPU Cores) + 1` (default: 4)
- **Threads per Worker**: `2` (default: 2)
- **Total Concurrent Handlers**: `Workers * Threads = 8 simultaneous requests`

Adjust via `.env`:
```env
WORKERS=8
THREADS=4
TIMEOUT=120
```

---

## 🐘 Optional PostgreSQL Database Setup

For high-throughput enterprise deployments, a PostgreSQL service is defined in `docker-compose.yml` under the `postgres` profile.

### 1. Launch with PostgreSQL Profile
```bash
docker compose --profile postgres up -d
```

### 2. Configure `.env` for PostgreSQL
```env
DATABASE_URL=postgresql://fraud_user:fraud_password_secure_2026@postgres:5432/fraud_db
```

---

## ❓ Troubleshooting & Common Scenarios

### Container Exits Immediately with Code 1
- **Check logs**: `docker compose logs app`
- **Likely Cause**: Insecure or missing `SECRET_KEY` or `CARD_ENCRYPTION_KEY` in `.env`.
- **Fix**: Verify `.env` exists and contains valid 64-hex and Fernet keys.

### Permission Denied on `/app/data`
- **Cause**: Volume mounted with root ownership.
- **Fix**: The `entrypoint.sh` and Dockerfile ensure `appuser` owns `/app/data`. If using bind mounts, run: `sudo chown -R 1001:1001 ./data`.

### Port 5000 Already in Use
- **Fix**: Change port in `.env` (e.g. `PORT=8080`) and run `docker compose up -d`.

---

## ✅ Deployment Checklist

- [x] Copied `.env.example` to `.env` with production keys
- [x] Ran `docker compose build`
- [x] Executed `docker compose up -d`
- [x] Verified `curl http://localhost:5000/health` returns `200 OK`
- [x] Verified login with `admin` / `admin123` at `http://localhost:5000`
- [x] Checked container logs with `docker compose logs -f`
