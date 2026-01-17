import sqlite3
from werkzeug.security import check_password_hash
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'fraud_detection.db'
MERCHANT_ID = 'Test123!'
PASSWORD = 'testpass'

if not DB_PATH.exists():
    print(f"DB not found at {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('SELECT merchant_id, password FROM merchants WHERE merchant_id = ?', (MERCHANT_ID,))
row = cur.fetchone()
if not row:
    print('NOT_FOUND')
else:
    mid, hashed = row
    matches = False
    try:
        matches = check_password_hash(hashed, PASSWORD)
    except Exception as e:
        print('ERROR_CHECKING_HASH', e)
    print('FOUND', mid)
    print('PASSWORD_MATCHES', matches)
    print('HASH', hashed)
conn.close()
