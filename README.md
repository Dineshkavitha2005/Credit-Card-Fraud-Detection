# Credit Card Fraud Detection System

A Flask-based web application for real-time credit card fraud detection using machine learning.

## Features

- 🔐 **Secure Authentication**: Merchant login/signup with password hashing
- 📊 **Dashboard**: Overview of transactions and fraud statistics
- 💳 **Transaction Management**: View and analyze transaction history
- 🚨 **Fraud Detection**: Real-time fraud detection using ML model
- 📈 **Insights & Analytics**: Visual charts and fraud ratio analysis
- 🔔 **Live Feed**: Real-time monitoring of fraud alerts
- 👨‍💼 **Admin Portal**: Manage merchants and view fraud logs
- 🔑 **Password Recovery**: Forgot password functionality with email verification

## Tech Stack

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML, Bootstrap, Chart.js
- **ML**: Scikit-learn, Random Forest Classifier
- **Database**: SQLite
- **Security**: Werkzeug password hashing


## Usage

### Default Test Credentials
- **Merchant ID**: `test123!`
- **Password**: `password123`

### Creating New Merchant Account
1. Click "Sign Up" on the homepage
2. Enter Merchant ID and password
3. Confirm password
4. Login with new credentials


## Project Structure

```
├── app.py                          # Main Flask application
├── models.py                       # Database models
├── test_app.py                     # Test suite
├── requirements.txt                # Python dependencies
├── model.pkl                       # Trained ML model
├── preprocessor.pkl                # Data preprocessor
├── credit_card_fraud_dataset.csv   # Training dataset
├── Html/                           # HTML templates
│   ├── index.html                  # Login page
│   ├── signup.html                 # Registration page
│   ├── dashboard.html              # Main dashboard
│   ├── transactions.html           # Transaction list
│   ├── fraud_transactions.html     # Fraud alerts
│   ├── insights.html               # Analytics
│   ├── live.html                   # Real-time feed
│   ├── admin.html                  # Admin panel
│   ├── forgot_password.html        # Password recovery
│   └── reset_password.html         # Password reset
├── static/                         # Static assets
│   ├── bootstrap.min.css
│   ├── bootstrap.min.js
│   └── chart.min.js
├── instance/                       # Database files
│   └── fraud_detection.db
└── scripts/                        # Utility scripts
    ├── init_db.py
    ├── check_merchant.py
    └── dump_merchants.py
```

## Key Features Explained

### Fraud Detection
The system uses a Random Forest Classifier trained on historical transaction data to predict fraud in real-time. Features analyzed include:
- Transaction amount
- Transaction type
- Location
- Merchant ID
- Transaction timestamp

### Security
- Passwords are hashed using Werkzeug's `generate_password_hash`
- Session-based authentication
- Protected routes requiring login
- CSRF protection (recommended for production)

### API Endpoints
- `/api/live_feed` - Real-time fraud detection data
- `/api/fraud_ratio` - Fraud statistics
- `/transaction_details?transaction_id=<id>` - Transaction details

## Configuration

### Production Deployment
Before deploying to production:

1. **Change Secret Key** in `app.py`:
   ```python
   app.secret_key = 'your-secure-secret-key-here'
   ```

2. **Use Production Database**:
   Replace SQLite with PostgreSQL or MySQL for better performance

3. **Set Debug to False**:
   ```python
   app.run(debug=False)
   ```


## Testing

The application includes comprehensive tests:
- Database integrity tests
- Route accessibility tests
- Authentication tests
- Edge case handling



