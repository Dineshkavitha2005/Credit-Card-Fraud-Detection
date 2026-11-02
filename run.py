"""
Credit Card Fraud Detection System - Server Entry Point
"""
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure backend directory is in python module search path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load .env from root or backend if available
for env_candidate in [
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.join(BACKEND_DIR, '.env')
]:
    if os.path.exists(env_candidate):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_candidate, override=False)
            break
        except Exception:
            pass

from app import app, init_db

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print("\n🔒 Credit Card Fraud Detection System")
    print("=" * 45)
    print(f"🌐 Server: http://127.0.0.1:{port}")
    print("👤 Login:  admin / admin123")
    print("=" * 45 + "\n")
    app.run(debug=True, port=port)

