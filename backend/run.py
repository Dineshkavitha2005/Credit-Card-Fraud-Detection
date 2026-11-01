"""
Backend Standalone Server Runner
Launches the Flask application directly from the backend directory.
"""
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, '..'))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, init_db

def main():
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    print("\n🔒 Credit Card Fraud Detection System - Backend Server")
    print("=" * 55)
    print(f"🌐 Server: http://127.0.0.1:{port}")
    print("👤 Login:  admin / admin123")
    print("=" * 55 + "\n")
    app.run(debug=debug, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()

