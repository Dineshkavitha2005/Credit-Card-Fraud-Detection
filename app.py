
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import joblib
import pandas as pd
import logging
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from functools import lru_cache
import random
from models import db, Merchant, Transaction, FraudLog
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='Html')
# Use environment variable for secret key, fallback to default for development
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['TEMPLATES_FOLDER'] = 'Html'  # Set custom templates folder
db_path = os.path.join(basedir, 'instance', 'fraud_detection.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Paths to the updated model, preprocessor, and dataset
model_path = 'model.pkl'
preprocessor_path = 'preprocessor.pkl'
dataset_path = 'credit_card_fraud_dataset.csv'

# Load the updated model and preprocessor
model = joblib.load(model_path)
preprocessor, feature_names = joblib.load(preprocessor_path)

# Load the dataset
df = pd.read_csv(dataset_path)

# merchant credentials are stored in the database (models.Merchant)

# Dynamically load column names from the dataset
all_columns = df.columns.tolist()
all_columns.remove('IsFraud')  # Exclude the target column

print("=== Feature Names from Dataset ===")
print(all_columns)

# Configure logging
logging.basicConfig(filename='fraud_detection.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def preprocess_input(data, preprocessor):
    """
    Preprocess the input data using the preprocessor.
    """
    df = pd.DataFrame([data])
    try:
        df = df[feature_names]
    except KeyError as e:
        raise ValueError(f"Input features do not match expected features: {e}")
    transformed = preprocessor.transform(df)
    return transformed

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route for the homepage.
    """
    # If user is already logged in and not explicitly requesting login page, redirect to dashboard
    if 'merchant_id' in session and not request.args.get('show_login'):
        return redirect(url_for('dashboard'))

    recent_predictions = []  # Replace with logic to fetch recent predictions
    if request.method == 'POST':
        try:
            # Get MerchantID and Password from the form
            merchant_id = request.form.get('MerchantID')
            password = request.form.get('Password')

            if not merchant_id or not merchant_id.strip():
                raise ValueError("MerchantID is required.")
            if not password:
                raise ValueError("Password is required.")

            # merchant_id is now a string, no conversion needed

            # Validate MerchantID and Password using database
            merchant = Merchant.query.filter_by(merchant_id=merchant_id).first()
            if not merchant:
                flash("Invalid MerchantID or Password.", "error")
                return render_template('index.html', error="Invalid MerchantID or Password.")

            # verify hashed password
            if not check_password_hash(merchant.password, password):
                flash("Invalid MerchantID or Password.", "error")
                return render_template('index.html', error="Invalid MerchantID or Password.")

            # Store merchant_id in session
            session['merchant_id'] = merchant_id

            return redirect(url_for('dashboard'))
        except ValueError as ve:
            logging.error(f"Input Error: {ve}")
            flash(str(ve), "error")
            return render_template('index.html', error=str(ve))
        except Exception as e:
            logging.error(f"Exception Occurred: {e}")
            flash("An error occurred. Please try again.", "error")
            return render_template('index.html', error="An error occurred. Please try again.")
    return render_template('index.html', feature_names=all_columns, recent_predictions=recent_predictions)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Multi-step route for merchant signup.
    Step 1: Get username and email
    Step 2: Confirm/customize merchant ID
    Step 3: Set password
    """
    # If user is already logged in, redirect to dashboard
    if 'merchant_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Support single-step signup (current UI) by accepting merchant ID + password directly
        simple_flow = not request.form.get('step')
        merchant_id_direct = request.form.get('MerchantID')
        password_direct = request.form.get('Password')
        confirm_direct = request.form.get('ConfirmPassword')

        if simple_flow and merchant_id_direct and password_direct:
            try:
                merchant_id_clean = merchant_id_direct.strip()
                if not merchant_id_clean:
                    raise ValueError("Merchant ID is required.")
                if password_direct != confirm_direct:
                    raise ValueError("Passwords do not match.")
                if len(password_direct) < 6:
                    raise ValueError("Password must be at least 6 characters long.")

                # Default username/email fallbacks for minimal form
                username = (request.form.get('Username') or merchant_id_clean).strip()
                email_raw = (request.form.get('Email') or f"{merchant_id_clean}@example.com").strip()
                if '@' not in email_raw:
                    email_raw = f"{email_raw}@example.com"
                local_part, _, domain_part = email_raw.partition('@')
                base_email_local = local_part or merchant_id_clean
                email_domain = domain_part or 'example.com'

                # Uniqueness checks
                if Merchant.query.filter_by(merchant_id=merchant_id_clean).first():
                    flash("Merchant ID already exists. Please choose a different one.", "error")
                    return render_template('signup.html', step=1, error="Merchant ID already exists.")

                username_base = username
                suffix = 1
                while Merchant.query.filter_by(username=username).first():
                    username = f"{username_base}{suffix}"
                    suffix += 1

                email_candidate = f"{base_email_local}@{email_domain}"
                email_suffix = 1
                while Merchant.query.filter_by(email=email_candidate).first():
                    email_candidate = f"{base_email_local}{email_suffix}@{email_domain}"
                    email_suffix += 1

                pw_hash = generate_password_hash(password_direct)
                new_merchant = Merchant(
                    merchant_id=merchant_id_clean,
                    username=username,
                    email=email_candidate,
                    password=pw_hash
                )
                db.session.add(new_merchant)
                db.session.commit()

                session['merchant_id'] = merchant_id_clean
                flash("Signup successful! Welcome to your dashboard.", "success")
                return redirect(url_for('dashboard'))

            except ValueError as ve:
                logging.error(f"Input Error: {ve}")
                flash(str(ve), "error")
                return render_template('signup.html', step=1, error=str(ve))
            except Exception as e:
                logging.error(f"Exception Occurred: {e}")
                flash("An error occurred. Please try again.", "error")
                return render_template('signup.html', step=1, error="An error occurred. Please try again.")

        step = request.form.get('step', '1')

        if step == '1':
            # Step 1: Get username and email
            try:
                username = request.form.get('Username')
                email = request.form.get('Email')

                if not username or not username.strip():
                    raise ValueError("Username is required.")
                if not email or not email.strip():
                    raise ValueError("Email is required.")
                if '@' not in email or '.' not in email:
                    raise ValueError("Please enter a valid email address.")

                # Check if username or email already exists
                existing_username = Merchant.query.filter_by(username=username).first()
                if existing_username:
                    flash("Username already exists. Please choose a different one.", "error")
                    return render_template('signup.html', error="Username already exists.")

                existing_email = Merchant.query.filter_by(email=email).first()
                if existing_email:
                    flash("Email already exists. Please use a different email.", "error")
                    return render_template('signup.html', error="Email already exists.")

                # Auto-generate merchant ID
                username_part = username.lower().replace(' ', '')[:4]
                email_part = email.split('@')[0][:4]
                auto_merchant_id = f"{username_part}{email_part}"

                # Ensure uniqueness
                counter = 1
                original_id = auto_merchant_id
                while Merchant.query.filter_by(merchant_id=auto_merchant_id).first():
                    auto_merchant_id = f"{original_id}{counter}"
                    counter += 1

                # Store in session for next steps
                session['signup_username'] = username
                session['signup_email'] = email
                session['suggested_merchant_id'] = auto_merchant_id

                return render_template('signup.html', step=2, suggested_merchant_id=auto_merchant_id)

            except ValueError as ve:
                logging.error(f"Input Error: {ve}")
                flash(str(ve), "error")
                return render_template('signup.html', step=1, error=str(ve))

        elif step == '2':
            # Step 2: Confirm merchant ID
            try:
                merchant_id = request.form.get('MerchantID')
                action = request.form.get('action')

                if action == 'customize':
                    # User wants to customize, go back to step 2 with current value
                    return render_template('signup.html', step=2, suggested_merchant_id=merchant_id, customize=True)

                if not merchant_id or not merchant_id.strip():
                    raise ValueError("Merchant ID is required.")

                # Check if merchant ID already exists
                existing_merchant = Merchant.query.filter_by(merchant_id=merchant_id).first()
                if existing_merchant:
                    flash("Merchant ID already exists. Please choose a different one.", "error")
                    return render_template('signup.html', step=2, suggested_merchant_id=merchant_id, error="Merchant ID already exists.")

                # Store confirmed merchant ID
                session['signup_merchant_id'] = merchant_id

                return render_template('signup.html', step=3)

            except ValueError as ve:
                logging.error(f"Input Error: {ve}")
                flash(str(ve), "error")
                return render_template('signup.html', step=2, suggested_merchant_id=request.form.get('MerchantID', ''), error=str(ve))

        elif step == '3':
            # Step 3: Set password
            try:
                password = request.form.get('Password')
                confirm_password = request.form.get('ConfirmPassword')

                if not password:
                    raise ValueError("Password is required.")
                if password != confirm_password:
                    raise ValueError("Passwords do not match.")
                if len(password) < 6:
                    raise ValueError("Password must be at least 6 characters long.")

                # Get data from session
                username = session.get('signup_username')
                email = session.get('signup_email')
                merchant_id = session.get('signup_merchant_id')

                if not all([username, email, merchant_id]):
                    flash("Session expired. Please start signup again.", "error")
                    return redirect(url_for('signup'))

                # Create new merchant
                pw_hash = generate_password_hash(password)
                new_merchant = Merchant(
                    merchant_id=merchant_id,
                    username=username,
                    email=email,
                    password=pw_hash
                )
                db.session.add(new_merchant)
                db.session.commit()

                # Clear session data
                session.pop('signup_username', None)
                session.pop('signup_email', None)
                session.pop('signup_merchant_id', None)
                session.pop('suggested_merchant_id', None)

                # Store merchant_id in session for auto-login
                session['merchant_id'] = merchant_id

                flash("Signup successful! Welcome to your dashboard.", "success")
                return redirect(url_for('dashboard'))

            except ValueError as ve:
                logging.error(f"Input Error: {ve}")
                flash(str(ve), "error")
                return render_template('signup.html', step=3, error=str(ve))
            except Exception as e:
                logging.error(f"Exception Occurred: {e}")
                flash("An error occurred. Please try again.", "error")
                return render_template('signup.html', step=3, error="An error occurred. Please try again.")

    # GET request - start with step 1
    return render_template('signup.html', step=1)

@app.route('/dashboard')
def dashboard():
    """
    Dashboard route showing account details and overview for logged-in merchant.
    """
    if 'merchant_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    merchant_id = session['merchant_id']

    # Get merchant details
    merchant = Merchant.query.filter_by(merchant_id=merchant_id).first()

    # Get transaction statistics
    total_transactions = Transaction.query.filter_by(merchant_id=merchant_id).count()
    fraud_transactions = Transaction.query.filter_by(merchant_id=merchant_id).all()
    fraud_count = 0
    for tx in fraud_transactions:
        tx_data = {
            'TransactionID': tx.transaction_id,
            'TransactionDate': tx.transaction_date,
            'Amount': tx.amount,
            'MerchantID': tx.merchant_id,
            'TransactionType': tx.transaction_type,
            'Location': tx.location,
            'IsFraud': tx.is_fraud
        }
        prediction = model.predict(preprocessor.transform(pd.DataFrame([tx_data])))[0]
        if prediction == 1:
            fraud_count += 1

    # Calculate fraud ratio
    fraud_ratio = (fraud_count / total_transactions * 100) if total_transactions > 0 else 0

    return render_template('dashboard.html',
                         merchant_id=merchant_id,
                         merchant=merchant,
                         total_transactions=total_transactions,
                         fraud_count=fraud_count,
                         fraud_ratio=round(fraud_ratio, 2))

@app.route('/transactions')
def transactions():
    """
    Route to display transactions for a specific MerchantID.
    """
    if 'merchant_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    merchant_id = session['merchant_id']
    # Build filtered query
    query = Transaction.query.filter_by(merchant_id=merchant_id)

    # Parse filters from query params
    transaction_id = request.args.get('transaction_id', '').strip()
    transaction_type = request.args.get('transaction_type', '').strip()
    location = request.args.get('location', '').strip()
    fraud_status = request.args.get('fraud_status', 'all').strip().lower()  # all | fraud | no_fraud
    min_amount = request.args.get('min_amount', '').strip()
    max_amount = request.args.get('max_amount', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    # Apply filters safely
    if transaction_id:
        try:
            query = query.filter(Transaction.transaction_id == int(transaction_id))
        except ValueError:
            flash("Transaction ID must be a number.", "error")

    if transaction_type:
        query = query.filter(Transaction.transaction_type.ilike(f"%{transaction_type}%"))

    if location:
        query = query.filter(Transaction.location.ilike(f"%{location}%"))

    if fraud_status in {"fraud", "no_fraud"}:
        query = query.filter(Transaction.is_fraud.is_(fraud_status == "fraud"))

    if min_amount:
        try:
            query = query.filter(Transaction.amount >= float(min_amount))
        except ValueError:
            flash("Minimum amount must be a number.", "error")

    if max_amount:
        try:
            query = query.filter(Transaction.amount <= float(max_amount))
        except ValueError:
            flash("Maximum amount must be a number.", "error")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Transaction.transaction_date >= start_dt)
        except ValueError:
            flash("Start date must be YYYY-MM-DD.", "error")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Transaction.transaction_date <= end_dt)
        except ValueError:
            flash("End date must be YYYY-MM-DD.", "error")

    # Limit results to keep view responsive
    transactions = query.order_by(Transaction.transaction_date.desc()).limit(200).all()

    transactions_data = []
    for tx in transactions:
        transactions_data.append({
            'TransactionID': tx.transaction_id,
            'Amount': tx.amount,
            'Date': tx.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if tx.transaction_date else '',
            'MerchantID': tx.merchant_id,
            'TransactionType': tx.transaction_type,
            'Location': tx.location,
            'FraudStatus': 'Fraud' if tx.is_fraud else 'No Fraud'
        })

    filters = {
        'transaction_id': transaction_id,
        'transaction_type': transaction_type,
        'location': location,
        'fraud_status': fraud_status,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render_template(
        'transactions.html',
        merchant_id=merchant_id,
        transactions=transactions_data,
        filters=filters,
        total=len(transactions_data)
    )

@app.route('/result')
def result():
    """
    Route to display the prediction result.
    """
    prediction = request.args.get('prediction', 'No result available')
    return render_template('result.html', prediction=prediction)

@lru_cache(maxsize=None)
def get_fraud_ratio():
    fraud_count = df['IsFraud'].sum()
    total_count = len(df)
    return fraud_count / total_count if total_count > 0 else 0

@lru_cache(maxsize=None)
def get_feature_importance():
    if hasattr(model, 'feature_importances_'):
        importance_dict = dict(zip(feature_names, model.feature_importances_))
        # Sort by importance and take top 10
        sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        return dict(sorted_importance)
    else:
        # Fallback if no feature importances
        return {col: 1.0 / len(feature_names) for col in feature_names[:10]}

@app.route('/insights')
def insights():
    """
    Route to display model insights.
    """
    fraud_ratio = get_fraud_ratio()
    feature_importance = get_feature_importance()
    return render_template('insights.html', fraud_ratio=fraud_ratio, feature_importance=feature_importance)

@app.route('/api/live_feed')
def api_live_feed():
    """
    API endpoint for live fraud detection feed.
    """
    # Simulate live data by randomly selecting transactions
    sample_size = min(10, len(df))
    sample_transactions = df.sample(n=sample_size, random_state=random.randint(0, 1000))

    live_feed = []
    for _, row in sample_transactions.iterrows():
        transaction_data = row.drop('IsFraud').to_dict()
        prediction = model.predict(preprocessor.transform(pd.DataFrame([transaction_data])))[0]
        result = 'Fraud Detected' if prediction == 1 else 'No Fraud Detected'
        live_feed.append({
            'TransactionID': int(row['TransactionID']),
            'Amount': float(row['Amount']),
            'Result': result
        })

    return jsonify(live_feed)

@app.route('/live')
def live_detection():
    """
    Route to display live detection feed.
    """
    live_feed = []  # Initial empty feed, will be populated via AJAX
    return render_template('live.html', live_feed=live_feed)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """
    Admin portal for uploading datasets and retraining the model.
    """
    if request.method == 'POST':
        file = request.files['dataset']
        file.save('uploaded_dataset.csv')  # Save the uploaded dataset
        df = pd.read_csv('uploaded_dataset.csv')
        X = df.drop('IsFraud', axis=1)
        y = df['IsFraud']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        new_model = RandomForestClassifier(random_state=42)
        new_model.fit(X_train, y_train)
        joblib.dump(new_model, model_path)
        return "Dataset uploaded and model retrained successfully!"
    return render_template('admin.html')

@app.route('/transaction_details')
def transaction_details():
    """
    Route to display full details of a specific transaction.
    """
    if 'merchant_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    transaction_id = request.args.get('transaction_id')
    if not transaction_id:
        return "Transaction ID required", 400

    # Query transaction from database
    transaction = Transaction.query.filter_by(transaction_id=int(transaction_id), merchant_id=session['merchant_id']).first()

    if not transaction:
        return "Transaction not found", 404

    # Add fraud status
    tx_data = {
        'TransactionID': transaction.transaction_id,
        'TransactionDate': transaction.transaction_date,
        'Amount': transaction.amount,
        'MerchantID': transaction.merchant_id,
        'TransactionType': transaction.transaction_type,
        'Location': transaction.location,
        'IsFraud': transaction.is_fraud
    }
    prediction = model.predict(preprocessor.transform(pd.DataFrame([tx_data])))[0]
    tx_data['FraudStatus'] = 'Fraud' if prediction == 1 else 'No Fraud'

    return render_template('transaction_details.html', transaction=tx_data)

@app.route('/fraud_transactions')
def fraud_transactions():
    """
    Route to display only fraud transactions (Transaction ID and Date).
    """
    if 'merchant_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    merchant_id = session['merchant_id']

    # Query transactions from database and filter fraud ones
    transactions = Transaction.query.filter_by(merchant_id=merchant_id).all()
    fraud_transactions_data = []
    for tx in transactions:
        tx_data = {
            'TransactionID': tx.transaction_id,
            'TransactionDate': tx.transaction_date,
            'Amount': tx.amount,
            'MerchantID': tx.merchant_id,
            'TransactionType': tx.transaction_type,
            'Location': tx.location,
            'IsFraud': tx.is_fraud
        }
        prediction = model.predict(preprocessor.transform(pd.DataFrame([tx_data])))[0]
        if prediction == 1:
            tx_data['FraudStatus'] = 'Fraud'
            fraud_transactions_data.append(tx_data)

    return render_template(
        'fraud_transactions.html',
        merchant_id=merchant_id,
        fraud_transactions=fraud_transactions_data
    )

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Route for forgot password functionality.
    """
    if request.method == 'POST':
        try:
            email = request.form.get('Email')

            if not email or not email.strip():
                raise ValueError("Email is required.")

            # Check if email exists
            merchant = Merchant.query.filter_by(email=email).first()
            if not merchant:
                flash("If this email exists, a reset code has been sent to your email.", "info")
                return render_template('forgot_password.html')

            # Generate a simple reset code (in production, use proper email service)
            import random
            import string
            reset_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            # Store reset code in session (in production, store in database with expiration)
            session['reset_email'] = email
            session['reset_code'] = reset_code

            # In production, send email with reset code
            print(f"Reset code for {email}: {reset_code}")

            flash("If this email exists, a reset code has been sent to your email.", "info")
            return redirect(url_for('reset_password'))

        except ValueError as ve:
            logging.error(f"Input Error: {ve}")
            flash(str(ve), "error")
            return render_template('forgot_password.html', error=str(ve))
        except Exception as e:
            logging.error(f"Exception Occurred: {e}")
            flash("An error occurred. Please try again.", "error")
            return render_template('forgot_password.html', error="An error occurred. Please try again.")

    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """
    Route for resetting password with reset code.
    """
    if request.method == 'POST':
        try:
            reset_code = request.form.get('ResetCode')
            new_password = request.form.get('NewPassword')
            confirm_password = request.form.get('ConfirmPassword')

            if not reset_code:
                raise ValueError("Reset code is required.")
            if not new_password:
                raise ValueError("New password is required.")
            if new_password != confirm_password:
                raise ValueError("Passwords do not match.")

            # Check if reset code is valid
            if 'reset_code' not in session or 'reset_email' not in session:
                flash("Invalid or expired reset code.", "error")
                return render_template('reset_password.html', error="Invalid or expired reset code.")

            if reset_code != session['reset_code']:
                flash("Invalid reset code.", "error")
                return render_template('reset_password.html', error="Invalid reset code.")

            email = session['reset_email']

            # Update password
            merchant = Merchant.query.filter_by(email=email).first()
            if not merchant:
                flash("Merchant not found.", "error")
                return render_template('reset_password.html', error="Merchant not found.")

            pw_hash = generate_password_hash(new_password)
            merchant.password = pw_hash
            db.session.commit()

            # Clear reset session
            session.pop('reset_code', None)
            session.pop('reset_email', None)

            flash("Password reset successful! Please log in with your new password.", "success")
            return redirect(url_for('index'))

        except ValueError as ve:
            logging.error(f"Input Error: {ve}")
            flash(str(ve), "error")
            return render_template('reset_password.html', error=str(ve))
        except Exception as e:
            logging.error(f"Exception Occurred: {e}")
            flash("An error occurred. Please try again.", "error")
            return render_template('reset_password.html', error="An error occurred. Please try again.")

    # Check if user has valid reset session
    if 'reset_code' not in session or 'reset_email' not in session:
        flash("Please request a password reset first.", "error")
        return redirect(url_for('forgot_password'))

    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    """
    Route to log out the user.
    """
    session.pop('merchant_id', None)
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting Flask app. Access it at: http://127.0.0.1:5000")
    app.run(debug=True)
