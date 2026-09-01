#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🛡️  Credit Card Fraud Detection System - Starting Up"
echo "=========================================================="

# Ensure instance directories exist
mkdir -p /app/data
mkdir -p /app/instance/reports

echo "ℹ️  Port: ${PORT:-5000}"

# Verify database requirements and wait for database readiness
python -c "
import os, sys, time, re
from sqlalchemy import create_engine, text

flask_env = os.getenv('FLASK_ENV', 'production').lower()
db_url = os.getenv('DATABASE_URL', '').strip()

masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', db_url) if db_url else '(none)'
print(f'ℹ️  Environment: {flask_env}')
print(f'ℹ️  Database URI: {masked_url}')

if flask_env == 'production':
    if not db_url:
        print('❌ FATAL: Production configuration requires DATABASE_URL to be set to a PostgreSQL database.', file=sys.stderr)
        sys.exit(1)
    if 'sqlite' in db_url.lower():
        print('❌ FATAL: Production configuration strictly refuses to run on SQLite. PostgreSQL is required.', file=sys.stderr)
        sys.exit(1)

if 'postgresql' in db_url.lower() or 'postgres' in db_url.lower():
    if db_url.startswith('postgres://'):
        db_url = 'postgresql://' + db_url[len('postgres://'):]
    print('⏳ Waiting for PostgreSQL database readiness...')
    timeout = 60
    start = time.time()
    connected = False
    last_err = None
    engine = create_engine(db_url, pool_pre_ping=True)
    while time.time() - start < timeout:
        try:
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            connected = True
            break
        except Exception as e:
            last_err = e
            time.sleep(1)
    if not connected:
        print(f'❌ PostgreSQL readiness check failed after {timeout}s: {last_err}', file=sys.stderr)
        sys.exit(1)
    print('✅ PostgreSQL database is ready and accepting connections.')
"

# Run database schema migrations & initialization
echo "🔄 Checking database initialization and security migrations..."
python -c "
import sys
try:
    from app import init_db
    init_db()
    print('✅ Database initialization and migrations complete.')
except Exception as e:
    print(f'❌ Database initialization failed: {e}', file=sys.stderr)
    sys.exit(1)
"

echo "=========================================================="
echo "🚀 Launching Application Server"
echo "=========================================================="

# Execute the container CMD
exec "$@"
