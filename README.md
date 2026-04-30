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



### Security
- Passwords are hashed using Werkzeug's `generate_password_hash`
- Session-based authentication
- Protected routes requiring login
- CSRF protection (recommended for production)

