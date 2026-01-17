import sqlite3
import os

db_path = 'instance/fraud_detection.db'
if not os.path.exists(db_path):
    print('DB file not found:', db_path)
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute('SELECT merchant_id FROM merchants')
        rows = cur.fetchall()
        print('merchants:', rows)
    except Exception as e:
        print('Error reading merchants table:', e)
    finally:
        conn.close()
