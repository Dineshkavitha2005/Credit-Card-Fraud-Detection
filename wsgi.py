"""
WSGI Application Entry Point for Gunicorn / Production Servers.
Exposes the WSGI application callable for production HTTP servers.
"""
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure backend directory is in python search path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, init_db

# Ensure database schema, security migrations, and default admin account exist
try:
    init_db()
except Exception as e:
    print(f"WSGI startup database initialization warning: {e}", file=sys.stderr)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
