# Quick Start Guide - Transaction History Features

## What's New?

Your Credit Card Fraud Detection System now includes **advanced transaction history features** with powerful searching, filtering, and export capabilities.

---

## How to Use

### 📊 View Transaction History

1. Click **"Transactions"** in the sidebar
2. The page automatically loads with statistics at the top:
   - Total transactions count
   - Total spending amount
   - Fraud cases detected
   - Fraud rate percentage

### 🔍 Search Transactions

**Simple Search:**
- Type in the search box to find by:
  - Merchant name (e.g., "Amazon")
  - Card holder name
  - Transaction ID (e.g., "TXN20260312...")

**Advanced Filters:**
1. Click filter fields to expand options
2. Set date range (from/to dates)
3. Select status: Fraud | Safe | Approved | Declined
4. Choose merchant category
5. Filter by amount range ($100 - $5000)
6. Sort by: Date, Amount, or Risk Score
7. Click **Reset** to clear all filters

### 📋 View Transaction Details

1. Find the transaction in the table
2. Click the **eye icon** (👁️) in Actions column
3. Modal opens showing:
   - Full transaction information
   - Card details
   - Risk factors (if any)
   - Security alerts (if any)
   - Risk score and status

### 📥 Export Transactions

1. (Optional) Apply filters to narrow results
2. Click **Export** button
3. CSV file downloads with filename like:
   ```
   transactions_20260312_120530.csv
   ```
4. Open in Excel/Google Sheets for analysis

---

## Understanding the Data

### Status Badges

| Badge | Meaning |
|-------|---------|
| ⚠️ **Fraud** | Transaction detected as fraudulent |
| ✓ **Approved** | Safe transaction approved |
| ✗ **Declined** | Transaction was declined |

### Risk Score

- **0-40%**: 🟢 Low Risk (Safe)
- **40-65%**: 🟡 Medium Risk (Watch)
- **65-80%**: 🔴 High Risk (Alert)
- **80-100%**: 🔴 Critical Risk (Block)

### Categories

- Online Shopping
- Retail
- Restaurant
- Gas Station
- Travel
- Electronics
- Grocery
- Subscription
- And more...

---

## Common Tasks

### Find All Fraud Transactions
1. Filter Status → "⚠️ Fraud Detected"
2. Adjust date range if needed
3. View details to see why flagged

### Analyze Spending by Category
1. Leave all filters default
2. Look at the "by_category" section
3. See fraud rate per category

### Monthly Expense Report
1. Set date range → First to last day of month
2. Click Export
3. Open CSV in Excel
4. Create pivot table if desired

### Review High-Value Transactions
1. Set Amount Min → 1000
2. Sort by Amount
3. Review each transaction for legitimacy

### Check Specific Merchant
1. Search → Type merchant name
2. See all transactions from that merchant
3. Note fraud patterns

---

## API Reference (for Developers)

### Get Transaction History
```
GET /api/transactions/history
?page=1&per_page=20&status=fraud&date_from=2026-03-01
```

### Get Transaction Details
```
GET /api/transactions/TXN20260312120530/details
```

### Get Statistics
```
GET /api/transactions/statistics
```

### Export CSV
```
GET /api/transactions/export?date_from=2026-03-01&date_to=2026-03-31
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Search |
| Esc | Close modal |
| ↑/↓ | Navigate results |

---

## Tips & Tricks

✅ **Do:**
- Regularly check transaction history for unusual patterns
- Export monthly reports for accounting
- Use date ranges to isolate time periods
- Review fraud alerts within 24 hours

❌ **Don't:**
- Share exported CSV files without encryption
- Ignore high-risk transactions below fraud threshold
- Rely solely on fraud score (manual review important)
- Export data on public WiFi

---

## Troubleshooting

**Missing Transactions?**
- Check date range filter
- Verify card is added to account
- Try resetting all filters

**Export Not Working?**
- Try smaller date range
- Check browser download permissions
- Clear browser cache

**Slow Loading?**
- Reduce date range
- Limit search to fewer categories
- Try different sorting

---

## Support Resources

- Full documentation: `TRANSACTION_HISTORY_FEATURES.md`
- Report issues in error console (F12)
- Check system logs for server errors

---

**Last Updated:** March 12, 2026
**Version:** 1.0
