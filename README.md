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


### Security
- Passwords are hashed using Werkzeug's `generate_password_hash`
- Session-based authentication
- Protected routes requiring login
- CSRF protection (recommended for production)

