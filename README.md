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

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Lohithravi69/NM_Lohith_DS.git
   cd NM_Lohith_DS
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python init_db.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the app**
   Open your browser and navigate to: `http://127.0.0.1:5000`

## Usage

### Default Test Credentials
- **Merchant ID**: `test123!`
- **Password**: `password123`

### Creating New Merchant Account
1. Click "Sign Up" on the homepage
2. Enter Merchant ID and password
3. Confirm password
4. Login with new credentials

### Running Tests
```bash
python test_app.py
```

## Project Structure

```
NM_Lohith_DS/
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

4. **Use WSGI Server**:
   Deploy with Gunicorn or uWSGI instead of Flask's development server

## Testing

The application includes comprehensive tests:
- Database integrity tests
- Route accessibility tests
- Authentication tests
- Edge case handling

All tests pass successfully ✅

## Future Enhancements

- [ ] Email integration for password reset
- [ ] Export transactions to CSV/PDF
- [ ] Advanced analytics and reporting
- [ ] Multi-factor authentication
- [ ] API rate limiting
- [ ] Automated fraud alerts via email/SMS

## License

This project is developed for educational purposes.

## Contributors

- Lohith (Developer)

## Support

For issues or questions, please open an issue on GitHub.

---

**Note**: This is a demonstration project. For production use, implement additional security measures and testing.
