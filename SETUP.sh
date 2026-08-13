#!/bin/bash
# FraudShield - Quick Setup Guide

echo "🔐 FraudShield - Secure Database & Authentication Setup"
echo "=================================================="
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing dependencies..."
pip install -r requirements.txt

# Step 2: Run the app
echo ""
echo "🚀 Step 2: Starting the application..."
echo "Navigate to: http://127.0.0.1:5000"
echo ""
echo "🔑 Login Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "⚠️  IMPORTANT: Change the admin password after first login!"
echo ""
python app.py
