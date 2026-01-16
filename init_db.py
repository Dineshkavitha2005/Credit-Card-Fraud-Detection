#!/usr/bin/env python
"""Initialize the SQLite database with all required tables."""

import sys
from pathlib import Path

# Add the repo root to path so we can import models and app
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))

try:
    from app import app, db
    print("Importing app and db...")
    
    with app.app_context():
        print("Creating all tables in fraud_detection.db...")
        db.create_all()
        print("✓ Database initialized successfully!")
        print(f"  DB location: {repo_root / 'fraud_detection.db'}")
        
        # List tables
        from sqlalchemy import text
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"  Tables created: {', '.join(tables)}")
except Exception as e:
    print(f"✗ Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
