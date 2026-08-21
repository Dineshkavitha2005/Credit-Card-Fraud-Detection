#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🛡️  Credit Card Fraud Detection System - Starting Up"
echo "=========================================================="

# Ensure data and instance directories exist
mkdir -p /app/data
mkdir -p /app/instance/reports

# Export default SQLite location if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="sqlite:////app/data/fraud_detection.db"
fi

echo "ℹ️  Environment: ${FLASK_ENV:-production}"
echo "ℹ️  Database URI: ${DATABASE_URL}"
echo "ℹ️  Port: ${PORT:-5000}"

# Run database schema migrations & initialization
echo "🔄 Checking database initialization and security migrations..."
python -c "
import sys
try:
    from app import init_db
    init_db()
    print('✅ Database initialization complete.')
except Exception as e:
    print(f'❌ Database initialization failed: {e}', file=sys.stderr)
    sys.exit(1)
"

echo "=========================================================="
echo "🚀 Launching Application Server"
echo "=========================================================="

# Execute the container CMD
exec "$@"
