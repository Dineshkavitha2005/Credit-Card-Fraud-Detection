from flask import Flask
import sys
from pathlib import Path
import os

# Ensure repository root is on sys.path so imports work when run from scripts/
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from models import db

basedir = os.path.abspath(repo_root)
db_path = os.path.join(basedir, 'instance', 'fraud_detection.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print(f'Database and tables ensured: {db_path}')
