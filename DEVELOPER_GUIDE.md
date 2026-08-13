# Developer Documentation - Transaction History Features

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (transactions.html)              │
│  ┌─────────────────────────────────────────────────────────┐
│  │ Statistics Cards │ Filter Panel │ Transaction Table │    │
│  │                              │                           │
│  │ Modal: Detail View          │  Modal: Export           │
│  └──────────────────┬──────────┬─────────────────────────┐│
├──────────────────────┼──────────┼───────────────────────────┤
│            JavaScript API Call Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ apiCall() function with async/await                 │  │
│  │ Error handling & notification system                │  │
│  └─────────────────────┬────────────────────────────────┘  │
├──────────────────────┬─────────────────────────────────────┤
│                HTTP REST API                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ /api/transactions/history    [GET]                  │  │
│  │ /api/transactions/{id}/details  [GET]               │  │
│  │ /api/transactions/statistics  [GET]                 │  │
│  │ /api/transactions/export      [GET]                 │  │
│  └─────────────────────┬────────────────────────────────┘  │
├──────────────────────┬─────────────────────────────────────┤
│           Flask Backend (app.py)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Route Handlers with @login_required decorator      │  │
│  │ SQLAlchemy ORM + raw SQL queries                    │  │
│  │ User access control & data filtering               │  │
│  └─────────────────────┬────────────────────────────────┘  │
├──────────────────────┬─────────────────────────────────────┤
│              SQLite Database                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ transactions table                                  │  │
│  │ alerts table                                        │  │
│  │ users table                                         │  │
│  │ user_cards table                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoint Specifications

### 1. GET `/api/transactions/history`

**Purpose:** Retrieve paginated, filtered transaction history

**Parameters (Query String):**
```
page              (int)  - Current page (1-based)
per_page          (int)  - Results per page (default: 20, max: 100)
search            (str)  - Free-text search across multiple fields
date_from         (str)  - ISO date format (YYYY-MM-DD)
date_to           (str)  - ISO date format (YYYY-MM-DD)
status            (str)  - fraud|safe|approved|declined
category          (str)  - Merchant category name
amount_min       (float) - Minimum transaction amount
amount_max       (float) - Maximum transaction amount
sort_by           (str)  - timestamp|amount|fraud_score
sort_order        (str)  - ASC|DESC
```

**Implementation Details:**
```python
@app.route('/api/transactions/history')
@login_required
def get_transaction_history():
    # 1. Extract query parameters with defaults
    # 2. Build dynamic SQL WHERE clause
    # 3. Apply user-specific filtering (if not admin)
    # 4. Calculate offset for pagination
    # 5. Execute count query for total
    # 6. Execute paginated data query
    # 7. Parse JSON fields (risk_factors)
    # 8. Return paginated response
```

**Response Schema:**
```json
{
  "transactions": [
    {
      "transaction_id": "TXN20260312...",
      "card_number": "****-****-****-1234",
      "card_holder": "John Doe",
      "amount": 150.50,
      "merchant": "Amazon",
      "category": "Online Shopping",
      "location": "New York, USA",
      "timestamp": "2026-03-12 12:05:30",
      "fraud_score": 25,
      "is_fraud": 0,
      "status": "approved",
      "device_type": "Desktop Chrome",
      "ip_address": "192.168.1.1",
      "risk_factors": ["..."]
    }
  ],
  "total": 1250,
  "page": 1,
  "per_page": 20,
  "total_pages": 63
}
```

**Error Responses:**
```json
// Invalid parameters
{ "error": "Invalid page number" } → 400

// Unauthorized
{ "error": "Authentication required" } → 401

// Server error
{ "error": "Database query failed" } → 500
```

---

### 2. GET `/api/transactions/<transaction_id>/details`

**Purpose:** Retrieve complete transaction details with related alerts

**Path Parameters:**
```
transaction_id (str) - Full transaction ID (e.g., TXN20260312120530)
```

**Implementation Details:**
```python
@app.route('/api/transactions/<transaction_id>/details')
@login_required
def get_transaction_details(transaction_id):
    # 1. Validate transaction_id format
    # 2. Query transaction by ID
    # 3. Verify user access (own card or admin)
    # 4. Query related alerts
    # 5. Parse JSON fields
    # 6. Return detailed response
```

**Response Schema:**
```json
{
  "transaction": {
    "id": 1,
    "transaction_id": "TXN20260312...",
    "user_id": 5,
    "card_number": "****-****-****-1234",
    "card_holder": "John Doe",
    "amount": 150.50,
    "merchant": "Amazon",
    "category": "Online Shopping",
    "location": "New York, USA",
    "device_type": "Desktop Chrome",
    "ip_address": "192.168.1.1",
    "is_fraud": 0,
    "fraud_score": 25,
    "status": "approved",
    "risk_factors": ["High amount", "New device"],
    "timestamp": "2026-03-12 12:05:30",
    "reviewed_by": null,
    "reviewed_at": null
  },
  "alerts": [
    {
      "id": 1,
      "transaction_id": "TXN20260312...",
      "alert_type": "fraud_detection",
      "severity": "medium",
      "message": "Suspicious transaction...",
      "is_read": 0,
      "created_at": "2026-03-12 12:05:35"
    }
  ]
}
```

**Error Responses:**
```json
// Transaction not found
{ "error": "Transaction not found" } → 404

// Access denied
{ "error": "Access denied" } → 403
```

---

### 3. GET `/api/transactions/statistics`

**Purpose:** Get aggregated statistics for transactions

**Implementation Details:**
```python
@app.route('/api/transactions/statistics')
@login_required
def get_transaction_statistics():
    # 1. Filter by user's cards (if not admin)
    # 2. Calculate total count, amount
    # 3. Calculate fraud count, amount, rate
    # 4. Group by category with fraud metrics
    # 5. Group by status
    # 6. Calculate averages
    # 7. Return aggregated stats
```

**Response Schema:**
```json
{
  "total_transactions": 1250,
  "total_amount": 125000.50,
  "fraud_count": 12,
  "fraud_amount": 3450.25,
  "fraud_rate": 0.96,
  "average_amount": 100.00,
  "by_category": [
    {
      "category": "Online Shopping",
      "count": 450,
      "fraud_count": 5,
      "total_amount": 45000.00
    },
    {
      "category": "Retail",
      "count": 280,
      "fraud_count": 2,
      "total_amount": 28000.00
    }
  ],
  "by_status": [
    {
      "status": "approved",
      "count": 1200,
      "total_amount": 120000.00
    },
    {
      "status": "declined",
      "count": 50,
      "total_amount": 5000.00
    }
  ]
}
```

---

### 4. GET `/api/transactions/export`

**Purpose:** Export filtered transactions as CSV

**Parameters (Query String):**
```
date_from  (str) - ISO date format
date_to    (str) - ISO date format
status     (str) - fraud|safe|approved|declined
```

**Implementation Details:**
```python
@app.route('/api/transactions/export', methods=['GET'])
@login_required
def export_transactions():
    # 1. Apply date and status filters
    # 2. Query all matching transactions
    # 3. Create CSV writer
    # 4. Write headers (field names)
    # 5. Write data rows
    # 6. Generate filename with timestamp
    # 7. Return CSV content and filename
```

**Response Schema:**
```json
{
  "csv": "transaction_id,card_number,...\nTXN123,...\n...",
  "filename": "transactions_20260312_120530.csv"
}
```

**CSV Format:**
```csv
transaction_id,card_number,card_holder,amount,merchant,category,location,timestamp,fraud_score,is_fraud,status,device_type,ip_address,risk_factors
TXN20260312120530,****-****-****-1234,John Doe,150.50,Amazon,Online Shopping,New York USA,2026-03-12 12:05:30,25,0,approved,Desktop Chrome,192.168.1.1,"[""High amount""]"
```

---

## Frontend Implementation Details

### Key Functions

#### `loadTransactions()`
Fetches transactions from API with current filters applied.

```javascript
async function loadTransactions() {
    const search = document.getElementById('search-input').value;
    const dateFrom = document.getElementById('date-from').value;
    // ... more params
    const params = new URLSearchParams({
        page: currentPage,
        per_page: PAGE_SIZE,
        // ... all params
    });
    
    const data = await apiCall(`/api/transactions/history?${params}`);
    renderTransactions(data.transactions);
    renderPagination(data.page, data.total_pages);
}
```

#### `renderTransactions(transactions)`
Renders transaction data into HTML table rows.

```javascript
function renderTransactions(transactions) {
    // Determine risk level color
    // Format dates and amounts
    // Create table rows with action buttons
    // Set innerHTML to tbody
}
```

#### `showTransactionDetail(transactionId)`
Fetches and displays detailed transaction info in modal.

```javascript
async function showTransactionDetail(transactionId) {
    const data = await apiCall(`/api/transactions/${transactionId}/details`);
    // Build detailed HTML
    // Handle risk factors display
    // Display related alerts
    // Show in modal
}
```

#### `exportTransactions()`
Triggers CSV download with applied filters.

```javascript
async function exportTransactions() {
    const params = getFilterParams();
    const data = await apiCall(`/api/transactions/export?${params}`);
    // Create blob
    // Trigger download
    // Show success notification
}
```

### Debouncing Pattern

```javascript
let searchTimeout;

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadTransactions();
    }, 300); // Wait 300ms after typing stops
}
```

---

## Database Schema

### Transactions Table
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE,
    card_number VARCHAR(255),
    card_holder VARCHAR(120),
    amount FLOAT,
    merchant VARCHAR(120),
    category VARCHAR(50),
    location VARCHAR(100),
    device_type VARCHAR(100),
    ip_address VARCHAR(50),
    is_fraud BOOLEAN,
    fraud_score FLOAT,
    status VARCHAR(20),
    risk_factors TEXT (JSON),
    timestamp DATETIME,
    -- Indexes for performance
    INDEX (transaction_id),
    INDEX (card_number),
    INDEX (timestamp),
    INDEX (is_fraud),
    INDEX (status)
);
```

### Alerts Table
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    transaction_id VARCHAR(50),
    alert_type VARCHAR(50),
    severity VARCHAR(20),
    message TEXT,
    is_read BOOLEAN,
    created_at DATETIME,
    -- Foreign key
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
```

---

## Performance Considerations

### Query Optimization
1. **Indexes** - Added on frequently filtered columns
2. **Pagination** - Limit and offset for large datasets
3. **Count Queries** - Separate count() queries avoid data transfer overhead
4. **Prepared Statements** - Prevent SQL injection + optimize parsing

### Frontend Optimization
1. **Debouncing** - Search input waits 300ms to reduce API calls
2. **Lazy Loading** - Detail modal fetches data on-demand
3. **DOM Updates** - Minimal innerHTML replacements
4. **Event Delegation** - Single event listener pattern for tables

### Caching Strategy
- Statistics loaded once per page load
- Transactions cached in memory per page
- Filters trigger fresh queries (no cache needed)

---

## Error Handling

### Server-Side
```python
try:
    # Database query
    transactions = conn.execute(query, params).fetchall()
except sqlite3.Error as e:
    return jsonify({'error': 'Database error'}), 500
finally:
    conn.close()  # Always close connection
```

### Client-Side
```javascript
try {
    const data = await apiCall('/api/transactions/history');
} catch (e) {
    console.error('Error:', e);
    notify('Failed to load transactions', 'error');
}
```

---

## Security Implementation

### Authentication
- `@login_required` decorator on all endpoints
- User ID from session
- Verified in queries

### Authorization
```python
if user and user.role != 'admin':
    user_card_numbers = [card.card_number for card in user.cards]
    query += f' AND card_number IN ({placeholders})'
    params.extend(user_card_numbers)
```

### SQL Injection Prevention
- Parameterized queries with `?` placeholders
- No string concatenation with user input
- Input validation on parameters

### XSS Prevention
- Jinja2 auto-escaping in templates
- JSON.stringify() for object serialization
- textContent instead of innerHTML where possible

---

## Testing Guide

### Unit Tests (Recommended)
```python
def test_get_transaction_history_with_filters():
    with app.test_client() as client:
        response = client.get(
            '/api/transactions/history',
            query_string={'status': 'fraud', 'per_page': 10}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'transactions' in data
        assert data['per_page'] == 10
```

### Integration Tests
Test full flow from UI to database and back.

### Manual Testing Checklist
- [ ] Load page with existing transactions
- [ ] Test each filter individually
- [ ] Test multiple filters together
- [ ] Verify pagination works
- [ ] Check export generates valid CSV
- [ ] Test modal detail view
- [ ] Verify user sees only their transactions
- [ ] Test admin sees all transactions
- [ ] Check responsiveness on mobile

---

## Deployment Checklist

- [ ] Database schema migrations applied
- [ ] Indexes created on transaction table
- [ ] Environment variables configured
- [ ] Static files (CSS/JS) cached properly
- [ ] Error logging configured
- [ ] Performance monitoring enabled
- [ ] Backup strategy in place
- [ ] Documentation updated

---

## Version History

**v1.0 (2026-03-12)**
- Initial release with transaction history features
- 4 new API endpoints
- Redesigned transactions page
- CSV export functionality
- Statistics dashboard
- Advanced filtering system

---

## Related Files

- Backend: `app.py` (lines 1250-1384)
- Frontend: `templates/transactions.html` (complete redesign)
- Documentation: `TRANSACTION_HISTORY_FEATURES.md`
- Quick Guide: `TRANSACTION_HISTORY_QUICKSTART.md`

---

**Last Updated:** March 12, 2026 | **Maintainer:** Development Team
