from app import app, db
from models import Merchant
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    # Check if sample merchant exists
    if not Merchant.query.filter_by(merchant_id='test123!').first():
        pw_hash = generate_password_hash('password123')
        sample_merchant = Merchant(merchant_id='test123!', password=pw_hash)
        db.session.add(sample_merchant)
        db.session.commit()
        print("Sample merchant created: ID=test123!, Password=password123")
    else:
        print("Sample merchant already exists.")
