"""
Database management for Personal Expense Tracker.
Handles SQLite schema creation, migrations, and CRUD operations.
"""
import sqlite3
import os
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import auth_service

DB_NAME = "expenses.db"

def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)

@contextmanager
def get_connection():
    """Provides a transactional database connection that always closes cleanly."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "icon": "utensils", "color": "#EF4444", "budget": 500.0},
    {"name": "Groceries", "icon": "shopping-cart", "color": "#F59E0B", "budget": 450.0},
    {"name": "Transportation", "icon": "car", "color": "#3B82F6", "budget": 200.0},
    {"name": "Housing & Utilities", "icon": "bolt", "color": "#6366F1", "budget": 600.0},
    {"name": "Entertainment", "icon": "film", "color": "#8B5CF6", "budget": 150.0},
    {"name": "Shopping", "icon": "bag-shopping", "color": "#EC4899", "budget": 300.0},
    {"name": "Health & Medical", "icon": "heart-pulse", "color": "#10B981", "budget": 150.0},
    {"name": "Travel", "icon": "plane", "color": "#06B6D4", "budget": 250.0},
    {"name": "Education", "icon": "book", "color": "#14B8A6", "budget": 100.0},
    {"name": "Personal Care", "icon": "sparkles", "color": "#F97316", "budget": 100.0},
    {"name": "Others", "icon": "box-archive", "color": "#6B7280", "budget": 100.0},
]

def init_db(seed_sample_data=True):
    """Initializes tables, users, default categories and initial transactions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                recovery_phrase_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Create default admin user if none exists
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            words, phrase = auth_service.generate_recovery_phrase(12)
            pwd_hash = auth_service.hash_password("admin123")
            phrase_hash = auth_service.hash_phrase(phrase)
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, recovery_phrase_hash)
                VALUES (1, 'admin', 'admin@example.com', ?, ?)
            """, (pwd_hash, phrase_hash))
            # Also store initial admin phrase in settings for easy discovery on first run
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_initial_recovery_phrase', ?)", (phrase,))
        
        # Default currency setting
        cursor.execute("SELECT value FROM settings WHERE key = 'currency_code'")
        if not cursor.fetchone():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('currency_code', 'USD')")
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('currency_symbol', '$')")

        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT 'tag',
                color TEXT NOT NULL DEFAULT '#3B82F6',
                monthly_budget REAL NOT NULL DEFAULT 0.0,
                user_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                payment_method TEXT NOT NULL,
                description TEXT NOT NULL,
                notes TEXT,
                user_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Migrate schema if columns or constraints need updating
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'")
        cat_tbl = cursor.fetchone()
        if cat_tbl and "name TEXT UNIQUE" in cat_tbl["sql"]:
            cursor.execute("PRAGMA foreign_keys = OFF")
            cursor.execute("""
                CREATE TABLE categories_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    icon TEXT NOT NULL DEFAULT 'tag',
                    color TEXT NOT NULL DEFAULT '#3B82F6',
                    monthly_budget REAL NOT NULL DEFAULT 0.0,
                    user_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, user_id)
                )
            """)
            cursor.execute("""
                INSERT INTO categories_new (id, name, icon, color, monthly_budget, user_id, created_at)
                SELECT id, name, icon, color, monthly_budget, COALESCE(user_id, 1), created_at FROM categories
            """)
            cursor.execute("DROP TABLE categories")
            cursor.execute("ALTER TABLE categories_new RENAME TO categories")
            cursor.execute("PRAGMA foreign_keys = ON")

        # Bank accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL DEFAULT 'Checking',
                account_number TEXT,
                initial_balance REAL NOT NULL DEFAULT 0.0,
                color TEXT NOT NULL DEFAULT '#3B82F6',
                icon TEXT NOT NULL DEFAULT 'building-columns',
                user_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(categories)")
        cat_columns = [col["name"] for col in cursor.fetchall()]
        if "user_id" not in cat_columns:
            cursor.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER DEFAULT 1")

        cursor.execute("PRAGMA table_info(users)")
        usr_columns = [col["name"] for col in cursor.fetchall()]
        if "totp_secret" not in usr_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT")
        if "two_factor_enabled" not in usr_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0")

        cursor.execute("PRAGMA table_info(expenses)")
        exp_columns = [col["name"] for col in cursor.fetchall()]
        if "user_id" not in exp_columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER DEFAULT 1")
        if "account_id" not in exp_columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL")
        if "receipt_filename" not in exp_columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN receipt_filename TEXT")
        if "is_recurring" not in exp_columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN is_recurring INTEGER DEFAULT 0")

        # Income table (v2.0)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                payment_method TEXT NOT NULL,
                account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL,
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES bank_accounts (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Transfers table (v2.0)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                from_account_id INTEGER NOT NULL,
                to_account_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES bank_accounts (id) ON DELETE CASCADE,
                FOREIGN KEY (to_account_id) REFERENCES bank_accounts (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Subscriptions table (v2.0)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category_id INTEGER,
                account_id INTEGER,
                billing_cycle TEXT NOT NULL DEFAULT 'Monthly',
                billing_day INTEGER NOT NULL DEFAULT 1,
                next_due_date TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                auto_log INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                FOREIGN KEY (account_id) REFERENCES bank_accounts (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Goals table (v2.0)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL CHECK(target_amount > 0),
                current_amount REAL NOT NULL DEFAULT 0.0,
                target_date TEXT,
                color TEXT NOT NULL DEFAULT '#10B981',
                icon TEXT NOT NULL DEFAULT 'bullseye',
                account_id INTEGER,
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES bank_accounts (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Create index for bank accounts and v2 tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_account ON expenses(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_accounts_user ON bank_accounts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_income_user ON income(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_income_date ON income(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_user ON transfers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id)")

        # Seed default bank accounts for user 1 if none exist
        cursor.execute("SELECT COUNT(*) FROM bank_accounts WHERE user_id = 1")
        if cursor.fetchone()[0] == 0:
            default_accounts = [
                ("Main Checking Account", "Checking", "4821", 4500.0, "#0D9488", "building-columns", 1),
                ("High-Yield Savings", "Savings", "9102", 15000.0, "#3B82F6", "piggy-bank", 1),
                ("Digital Wallet / UPI", "Digital Wallet", "7730", 850.0, "#8B5CF6", "mobile-screen", 1),
            ]
            for acc in default_accounts:
                cursor.execute("""
                    INSERT INTO bank_accounts (name, account_type, account_number, initial_balance, color, icon, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, acc)

        # Create indexes for fast querying by date, category and user
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
        
        # Seed categories if none exist
        cursor.execute("SELECT COUNT(*) FROM categories WHERE user_id = 1")
        if cursor.fetchone()[0] == 0:
            for cat in DEFAULT_CATEGORIES:
                cursor.execute("""
                    INSERT INTO categories (name, icon, color, monthly_budget, user_id)
                    VALUES (?, ?, ?, ?, 1)
                """, (cat["name"], cat["icon"], cat["color"], cat["budget"]))
        
        # Seed sample expenses if none exist
        cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id = 1")
        if cursor.fetchone()[0] == 0 and seed_sample_data:
            _seed_sample_expenses(conn)
            
        # Link any unlinked sample expenses to accounts for user 1
        cursor.execute("UPDATE expenses SET account_id = 1 WHERE account_id IS NULL AND payment_method IN ('Debit Card', 'Bank Transfer', 'Credit Card') AND user_id = 1")
        cursor.execute("UPDATE expenses SET account_id = 3 WHERE account_id IS NULL AND payment_method IN ('UPI / Digital Wallet') AND user_id = 1")

        # Seed sample income if none exist
        cursor.execute("SELECT COUNT(*) FROM income WHERE user_id = 1")
        if cursor.fetchone()[0] == 0 and seed_sample_data:
            _seed_sample_income(conn)

        # Seed sample subscriptions if none exist
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id = 1")
        if cursor.fetchone()[0] == 0 and seed_sample_data:
            _seed_sample_subscriptions(conn)

        # Seed sample goals if none exist
        cursor.execute("SELECT COUNT(*) FROM goals WHERE user_id = 1")
        if cursor.fetchone()[0] == 0 and seed_sample_data:
            _seed_sample_goals(conn)
            
        conn.commit()

def _seed_sample_income(conn):
    """Seeds realistic current and past month income streams."""
    cursor = conn.cursor()
    today = date.today()
    first_of_month = today.replace(day=1).isoformat()
    mid_month = (today.replace(day=1) + timedelta(days=14)).isoformat()
    
    # Previous month first day
    prev_month_date = (today.replace(day=1) - timedelta(days=5)).replace(day=1).isoformat()
    
    sample_income = [
        (first_of_month, "Tech Lead Monthly Salary", 5200.0, "Bank Transfer", 1, "Direct payroll deposit"),
        (mid_month, "Freelance UI Consulting", 850.0, "UPI / Digital Wallet", 3, "Mobile web design deliverables"),
        (prev_month_date, "Tech Lead Monthly Salary", 5200.0, "Bank Transfer", 1, "Direct payroll deposit"),
    ]
    for inc in sample_income:
        cursor.execute("""
            INSERT INTO income (date, source, amount, payment_method, account_id, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, inc)

def _seed_sample_subscriptions(conn):
    """Seeds typical digital subscriptions and recurring bills."""
    cursor = conn.cursor()
    today = date.today()
    sample_subs = [
        ("Netflix Premium 4K", 19.99, 5, 1, "Monthly", 5, (today + timedelta(days=5)).isoformat(), "Family streaming plan", 0),
        ("Spotify Music Family", 16.99, 5, 1, "Monthly", 12, (today + timedelta(days=12)).isoformat(), "HiFi audio streaming", 0),
        ("Amazon Prime Annual", 14.99, 6, 1, "Monthly", 18, (today + timedelta(days=18)).isoformat(), "Prime shopping & shipping", 0),
        ("Gym & Fitness Club", 49.00, 7, 1, "Monthly", 24, (today + timedelta(days=24)).isoformat(), "Monthly gym membership", 0),
    ]
    for sub in sample_subs:
        cursor.execute("""
            INSERT INTO subscriptions (name, amount, category_id, account_id, billing_cycle, billing_day, next_due_date, notes, auto_log, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, sub)

def _seed_sample_goals(conn):
    """Seeds financial milestones and savings pockets."""
    cursor = conn.cursor()
    sample_goals = [
        ("Emergency Fund (6 Months)", 12000.0, 7500.0, "2027-06-30", "#10B981", "shield-halved", 2, "Essential living expenses safety cushion"),
        ("Tokyo Vacation 2027", 3500.0, 1400.0, "2027-04-15", "#3B82F6", "plane", 2, "Flights, hotels and bullet train passes"),
        ("New MacBook Pro Setup", 2200.0, 1100.0, "2027-01-31", "#8B5CF6", "laptop", 1, "M-series workstation replacement"),
    ]
    for g in sample_goals:
        cursor.execute("""
            INSERT INTO goals (name, target_amount, current_amount, target_date, color, icon, account_id, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, g)

def _seed_sample_expenses(conn):
    """Populates realistic historical and current month expenses for instant demonstration."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories")
    cat_map = {row["name"]: row["id"] for row in cursor.fetchall()}
    
    today = date.today()
    sample_records = [
        # Current month
        (0, "Groceries", 64.50, "Credit Card", "Weekly supermarket run", "Fresh produce & pantry"),
        (1, "Food & Dining", 24.00, "Debit Card", "Lunch with colleagues", "Burrito bowl"),
        (1, "Transportation", 15.00, "UPI / Digital Wallet", "Metro recharge", "Commute card refill"),
        (2, "Housing & Utilities", 85.20, "Bank Transfer", "Electricity bill", "Monthly utility payment"),
        (3, "Food & Dining", 12.50, "Cash", "Morning specialty coffee & pastry", "Local cafe"),
        (4, "Shopping", 49.99, "Credit Card", "Wireless ergonomic mouse", "Home office accessory"),
        (5, "Entertainment", 16.99, "Credit Card", "Streaming subscription", "Family plan"),
        (6, "Health & Medical", 35.00, "Debit Card", "Pharmacy vitamins & medicines", "Health supplements"),
        (7, "Food & Dining", 42.80, "Credit Card", "Dinner at Italian bistro", "Pasta & dessert"),
        (8, "Groceries", 78.40, "Credit Card", "Organic grocery haul", "Whole foods & dairy"),
        (9, "Transportation", 32.50, "Credit Card", "Gas station fill-up", "Half tank fuel"),
        (10, "Personal Care", 25.00, "Cash", "Barber haircut", "Monthly grooming"),
        (11, "Food & Dining", 18.75, "UPI / Digital Wallet", "Fast casual lunch", "Salad bar"),
        (12, "Education", 29.00, "Credit Card", "Online programming book", "Python guide"),
        (13, "Travel", 120.00, "Credit Card", "Weekend train ticket", "Intercity travel booking"),
        (14, "Others", 19.50, "Cash", "Postal shipping & packaging", "Parcel dispatch"),
        
        # Previous month data for comparative charts
        (32, "Groceries", 95.00, "Credit Card", "Large monthly grocery haul", ""),
        (33, "Housing & Utilities", 110.00, "Bank Transfer", "Water and gas utilities", ""),
        (35, "Food & Dining", 55.00, "Credit Card", "Weekend dinner", "Steakhouse"),
        (38, "Transportation", 45.00, "Debit Card", "Gas station", ""),
        (40, "Entertainment", 60.00, "Credit Card", "Concert tickets", ""),
        (45, "Shopping", 120.00, "Credit Card", "Winter jacket", "Seasonal discount"),
        (48, "Health & Medical", 40.00, "Cash", "Dental checkup co-pay", ""),
    ]
    
    for days_ago, cat_name, amount, payment, desc, notes in sample_records:
        if cat_name in cat_map:
            expense_date = (today - timedelta(days=days_ago)).isoformat()
            cursor.execute("""
                INSERT INTO expenses (date, category_id, amount, payment_method, description, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (expense_date, cat_map[cat_name], amount, payment, desc, notes))

def get_setting(key, default=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key, value):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

def get_currency():
    return {
        "code": get_setting("currency_code", "USD"),
        "symbol": get_setting("currency_symbol", "$")
    }

def set_currency(code, symbol):
    set_setting("currency_code", code)
    set_setting("currency_symbol", symbol)

# ==================== User & Authentication Operations ====================

def create_user(username, password, email=""):
    """
    Creates a new user account, generates 12 recovery keywords,
    hashes the credentials, and initializes default categories.
    Returns: dict with user_id, username, recovery_words, recovery_phrase
    """
    clean_username = username.strip()
    clean_email = (email or "").strip()
    
    if len(clean_username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
        
    words, phrase = auth_service.generate_recovery_phrase(12)
    pwd_hash = auth_service.hash_password(password)
    phrase_hash = auth_service.hash_phrase(phrase)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, recovery_phrase_hash)
                VALUES (?, ?, ?, ?)
            """, (clean_username, clean_email, pwd_hash, phrase_hash))
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{clean_username}' is already taken. Please choose another.")
            
        # Seed default categories for this new user
        for cat in DEFAULT_CATEGORIES:
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name, icon, color, monthly_budget, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (cat["name"], cat["icon"], cat["color"], cat["budget"], user_id))

        # Seed default bank accounts for this new user
        default_accounts = [
            ("Main Checking", "Checking", "1001", 3000.0, "#0D9488", "building-columns", user_id),
            ("High-Yield Savings", "Savings", "2002", 8000.0, "#3B82F6", "piggy-bank", user_id),
            ("Digital Wallet / UPI", "Digital Wallet", "3003", 500.0, "#8B5CF6", "mobile-screen", user_id),
        ]
        for acc in default_accounts:
            cursor.execute("""
                INSERT INTO bank_accounts (name, account_type, account_number, initial_balance, color, icon, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, acc)
            
        return {
            "id": user_id,
            "username": clean_username,
            "recovery_words": words,
            "recovery_phrase": phrase
        }

def get_user_by_id(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_username(username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def authenticate_user(username, password):
    """Verifies credentials. Returns user dict on success, None on failure."""
    user = get_user_by_username(username)
    if not user:
        return None
    if auth_service.verify_password(user["password_hash"], password):
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    return None

def recover_user_password(username, candidate_phrase, new_password):
    """
    Verifies candidate recovery phrase and resets password.
    Raises ValueError on invalid credentials or phrase mismatch.
    """
    user = get_user_by_username(username)
    if not user:
        raise ValueError("User not found.")
        
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters long.")
        
    if not auth_service.verify_phrase(user["recovery_phrase_hash"], candidate_phrase):
        raise ValueError("Invalid recovery keywords. Please verify the phrase and try again.")
        
    new_pwd_hash = auth_service.hash_password(new_password)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_pwd_hash, user["id"]))
        conn.commit()
    return True

# ==================== Bank Account & Combined Balance Operations ====================

def get_bank_accounts(user_id=1):
    """
    Returns all bank accounts for a user with:
      - initial_balance
      - total_spent (sum of expenses linked to this bank account)
      - total_income (sum of income deposited into this bank account)
      - transfers_in / transfers_out
      - current_balance = initial_balance + total_income - total_spent + (transfers_in - transfers_out)
      - expense_count & income_count
    """
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*,
                   COALESCE((SELECT SUM(amount) FROM expenses WHERE account_id = b.id AND user_id = ?), 0) AS total_spent,
                   COALESCE((SELECT COUNT(id) FROM expenses WHERE account_id = b.id AND user_id = ?), 0) AS expense_count,
                   COALESCE((SELECT SUM(amount) FROM income WHERE account_id = b.id AND user_id = ?), 0) AS total_income,
                   COALESCE((SELECT COUNT(id) FROM income WHERE account_id = b.id AND user_id = ?), 0) AS income_count,
                   COALESCE((SELECT SUM(amount) FROM transfers WHERE to_account_id = b.id AND user_id = ?), 0) AS transfers_in,
                   COALESCE((SELECT SUM(amount) FROM transfers WHERE from_account_id = b.id AND user_id = ?), 0) AS transfers_out
            FROM bank_accounts b
            WHERE b.user_id = ?
            ORDER BY b.id ASC
        """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
        accounts = [dict(r) for r in cursor.fetchall()]
        for a in accounts:
            a["initial_balance"] = round(a["initial_balance"], 2)
            a["total_spent"] = round(a["total_spent"], 2)
            a["total_income"] = round(a["total_income"], 2)
            a["transfers_in"] = round(a["transfers_in"], 2)
            a["transfers_out"] = round(a["transfers_out"], 2)
            a["net_transfers"] = round(a["transfers_in"] - a["transfers_out"], 2)
            a["current_balance"] = round(
                a["initial_balance"] + a["total_income"] - a["total_spent"] + a["net_transfers"], 2
            )
        return accounts

def get_combined_balance(user_id=1):
    """
    Aggregates balances of all different bank accounts into one combined net financial balance!
    Returns:
      - total_initial_balance
      - total_spent
      - total_income
      - total_current_balance (net combined balance across all accounts)
      - net_savings = total_income - total_spent
      - account_count
      - breakdown_by_type
    """
    accounts = get_bank_accounts(user_id=user_id)
    total_initial = sum(a["initial_balance"] for a in accounts)
    total_spent = sum(a["total_spent"] for a in accounts)
    total_income = sum(a["total_income"] for a in accounts)
    total_current = sum(a["current_balance"] for a in accounts)
    
    types_breakdown = {}
    for a in accounts:
        t = a["account_type"]
        types_breakdown[t] = types_breakdown.get(t, 0.0) + a["current_balance"]
        
    return {
        "total_initial": round(total_initial, 2),
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "total_current": round(total_current, 2),
        "net_savings": round(total_income - total_spent, 2),
        "account_count": len(accounts),
        "types_breakdown": {k: round(v, 2) for k, v in types_breakdown.items()},
        "accounts": accounts
    }

def add_bank_account(name, account_type, initial_balance, account_number="", color="#3B82F6", icon="building-columns", user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Bank account name is required.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bank_accounts (name, account_type, account_number, initial_balance, color, icon, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clean_name, account_type.strip(), (account_number or "").strip(), float(initial_balance or 0.0), color.strip(), icon.strip(), user_id))
        conn.commit()
        return cursor.lastrowid

def update_bank_account(account_id, name, account_type, initial_balance, account_number="", color="#3B82F6", icon="building-columns", user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Bank account name is required.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bank_accounts
            SET name = ?, account_type = ?, account_number = ?, initial_balance = ?, color = ?, icon = ?
            WHERE id = ? AND user_id = ?
        """, (clean_name, account_type.strip(), (account_number or "").strip(), float(initial_balance or 0.0), color.strip(), icon.strip(), account_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_bank_account(account_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE expenses SET account_id = NULL WHERE account_id = ? AND user_id = ?", (account_id, user_id))
        cursor.execute("DELETE FROM bank_accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_bank_account_by_id(account_id, user_id=1):
    user_id = user_id or 1
    accounts = get_bank_accounts(user_id=user_id)
    for a in accounts:
        if a["id"] == account_id:
            return a
    return None

# ==================== Category Operations ====================

def get_categories(user_id=1):
    """Returns all categories with their budget and current month spend for a specific user."""
    user_id = user_id or 1
    current_month = date.today().strftime("%Y-%m")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, 
                   COALESCE(SUM(e.amount), 0) AS current_month_spent,
                   COUNT(e.id) AS total_expense_count
            FROM categories c
            LEFT JOIN expenses e ON c.id = e.category_id 
                                 AND strftime('%Y-%m', e.date) = ? 
                                 AND e.user_id = ?
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.name ASC
        """, (current_month, user_id, user_id))
        return [dict(row) for row in cursor.fetchall()]

def get_category_by_id(cat_id, user_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
        else:
            cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_category(name, icon, color, monthly_budget, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categories (name, icon, color, monthly_budget, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), icon.strip(), color.strip(), float(monthly_budget or 0.0), user_id))
        conn.commit()
        return cursor.lastrowid

def update_category(cat_id, name, icon, color, monthly_budget, user_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                UPDATE categories 
                SET name = ?, icon = ?, color = ?, monthly_budget = ?
                WHERE id = ? AND user_id = ?
            """, (name.strip(), icon.strip(), color.strip(), float(monthly_budget or 0.0), cat_id, user_id))
        else:
            cursor.execute("""
                UPDATE categories 
                SET name = ?, icon = ?, color = ?, monthly_budget = ?
                WHERE id = ?
            """, (name.strip(), icon.strip(), color.strip(), float(monthly_budget or 0.0), cat_id))
        conn.commit()
        return cursor.rowcount > 0

def update_category_budget(cat_id, monthly_budget, user_id=1):
    """Updates the monthly budget for a single category."""
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE categories
            SET monthly_budget = ?
            WHERE id = ? AND user_id = ?
        """, (max(0.0, float(monthly_budget or 0.0)), int(cat_id), user_id))
        conn.commit()
        return cursor.rowcount > 0

def update_monthly_budgets(category_budgets, user_id=1):
    """
    Updates budgets for multiple categories in a single atomic transaction.
    category_budgets: dict of {category_id: amount} or list of dicts.
    """
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        updated_count = 0
        if isinstance(category_budgets, dict):
            items = category_budgets.items()
        elif isinstance(category_budgets, list):
            items = [(item["id"], item.get("budget", item.get("monthly_budget", 0))) for item in category_budgets]
        else:
            items = []

        for cat_id, budget in items:
            cursor.execute("""
                UPDATE categories
                SET monthly_budget = ?
                WHERE id = ? AND user_id = ?
            """, (max(0.0, float(budget or 0.0)), int(cat_id), user_id))
            updated_count += cursor.rowcount
        conn.commit()
        return updated_count

def set_total_monthly_budget(new_total, user_id=1):
    """
    Sets an overall monthly budget and proportionally distributes it
    across existing categories for the user.
    """
    user_id = user_id or 1
    new_total = max(0.0, float(new_total or 0.0))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, monthly_budget FROM categories WHERE user_id = ? ORDER BY id ASC", (user_id,))
        cats = [dict(r) for r in cursor.fetchall()]
        if not cats:
            return 0

        current_total = sum(c["monthly_budget"] for c in cats)
        n = len(cats)
        
        if current_total > 0:
            # Scale proportionally
            for c in cats:
                ratio = c["monthly_budget"] / current_total
                scaled_budget = round(new_total * ratio, 2)
                cursor.execute("UPDATE categories SET monthly_budget = ? WHERE id = ? AND user_id = ?", (scaled_budget, c["id"], user_id))
        else:
            # Distribute equally
            equal_share = round(new_total / n, 2)
            for c in cats:
                cursor.execute("UPDATE categories SET monthly_budget = ? WHERE id = ? AND user_id = ?", (equal_share, c["id"], user_id))
                
        conn.commit()
        return n

def delete_category(cat_id, user_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        # Check if expenses exist for this category
        if user_id:
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE category_id = ? AND user_id = ?", (cat_id, user_id))
        else:
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE category_id = ?", (cat_id,))
            
        if cursor.fetchone()[0] > 0:
            raise ValueError("Cannot delete category with associated expenses. Please reassign or delete them first.")
            
        if user_id:
            cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
        else:
            cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        return cursor.rowcount > 0

# ==================== Expense Operations ====================

def add_expense(expense_date, category_id, amount, payment_method, description, notes="", user_id=1, account_id=None, receipt_filename=None, is_recurring=0):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (date, category_id, amount, payment_method, description, notes, user_id, account_id, receipt_filename, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (expense_date, int(category_id), float(amount), payment_method.strip(), description.strip(), (notes or "").strip(), user_id, account_id, receipt_filename, int(is_recurring or 0)))
        conn.commit()
        return cursor.lastrowid

def update_expense(expense_id, expense_date, category_id, amount, payment_method, description, notes="", user_id=None, account_id=None, receipt_filename=None, is_recurring=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        fields = ["date = ?", "category_id = ?", "amount = ?", "payment_method = ?", "description = ?", "notes = ?", "account_id = ?"]
        params = [expense_date, int(category_id), float(amount), payment_method.strip(), description.strip(), (notes or "").strip(), account_id]
        if receipt_filename is not None:
            fields.append("receipt_filename = ?")
            params.append(receipt_filename)
        if is_recurring is not None:
            fields.append("is_recurring = ?")
            params.append(int(is_recurring))
        
        where = "WHERE id = ?"
        params.append(expense_id)
        if user_id:
            where += " AND user_id = ?"
            params.append(user_id)
            
        cursor.execute(f"UPDATE expenses SET {', '.join(fields)} {where}", params)
        conn.commit()
        return cursor.rowcount > 0

def delete_expense(expense_id, user_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
        else:
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_expense_by_id(expense_id, user_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT e.*, c.name as category_name, c.icon as category_icon, c.color as category_color,
                   b.name as account_name, b.color as account_color, b.account_type as account_type
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
            LEFT JOIN bank_accounts b ON e.account_id = b.id
            WHERE e.id = ?
        """
        params = [expense_id]
        if user_id:
            query += " AND e.user_id = ?"
            params.append(user_id)
            
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def get_expenses(start_date=None, end_date=None, category_id=None, payment_method=None, search=None, limit=None, offset=0, user_id=1, account_id=None):
    """Filtered list of expenses for a specific user with joined category and bank account info."""
    user_id = user_id or 1
    conditions = ["e.user_id = ?"]
    params = [user_id]
    
    if start_date:
        conditions.append("e.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("e.date <= ?")
        params.append(end_date)
    if category_id:
        conditions.append("e.category_id = ?")
        params.append(category_id)
    if account_id:
        conditions.append("e.account_id = ?")
        params.append(account_id)
    if payment_method:
        conditions.append("e.payment_method = ?")
        params.append(payment_method)
    if search:
        conditions.append("(e.description LIKE ? OR e.notes LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
        
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    query = f"""
        SELECT e.*, c.name as category_name, c.icon as category_icon, c.color as category_color,
               b.name as account_name, b.color as account_color, b.account_type as account_type
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        LEFT JOIN bank_accounts b ON e.account_id = b.id
        {where_clause}
        ORDER BY e.date DESC, e.id DESC
    """
    
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def count_expenses(start_date=None, end_date=None, category_id=None, payment_method=None, search=None, user_id=1):
    user_id = user_id or 1
    conditions = ["user_id = ?"]
    params = [user_id]
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    if category_id:
        conditions.append("category_id = ?")
        params.append(category_id)
    if payment_method:
        conditions.append("payment_method = ?")
        params.append(payment_method)
    if search:
        conditions.append("(description LIKE ? OR notes LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
        
    where_clause = f"WHERE {' AND '.join(conditions)}"
    query = f"SELECT COUNT(*) FROM expenses {where_clause}"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]

# ==================== Reporting & Analytics Operations ====================

def get_monthly_metrics(month_str=None, user_id=1):
    user_id = user_id or 1
    if not month_str:
        month_str = date.today().strftime("%Y-%m")
        
    year, month = map(int, month_str.split("-"))
    if month == 1:
        prev_month_str = f"{year - 1}-12"
    else:
        prev_month_str = f"{year:04d}-{month - 1:02d}"
        
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Current month total and count
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total,
                   COUNT(id) as count,
                   COALESCE(MAX(amount), 0) as max_expense
            FROM expenses
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
        """, (month_str, user_id))
        cur_row = cursor.fetchone()
        total_spend = cur_row["total"]
        expense_count = cur_row["count"]
        largest_expense = cur_row["max_expense"]
        
        # Previous month total
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
        """, (prev_month_str, user_id))
        prev_month_spend = cursor.fetchone()["total"]
        
        # Total Monthly Budget
        cursor.execute("SELECT COALESCE(SUM(monthly_budget), 0) as total_budget FROM categories WHERE user_id = ?", (user_id,))
        total_budget = cursor.fetchone()["total_budget"]
        
        # Top Category this month
        cursor.execute("""
            SELECT c.name, SUM(e.amount) as cat_spend
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
            WHERE strftime('%Y-%m', e.date) = ? AND e.user_id = ?
            GROUP BY c.id
            ORDER BY cat_spend DESC
            LIMIT 1
        """, (month_str, user_id))
        top_cat_row = cursor.fetchone()
        top_category = top_cat_row["name"] if top_cat_row else "None"
        
        today = date.today()
        if today.strftime("%Y-%m") == month_str:
            days_counted = max(1, today.day)
        else:
            import calendar
            days_counted = calendar.monthrange(year, month)[1]
            
        daily_average = total_spend / days_counted if days_counted > 0 else 0.0
        
        return {
            "month": month_str,
            "prev_month": prev_month_str,
            "total_spend": round(total_spend, 2),
            "prev_month_spend": round(prev_month_spend, 2),
            "total_budget": round(total_budget, 2),
            "top_category": top_category,
            "largest_expense": round(largest_expense, 2),
            "expense_count": expense_count,
            "daily_average": round(daily_average, 2),
        }

def get_category_breakdown(month_str=None, user_id=1):
    user_id = user_id or 1
    if not month_str:
        month_str = date.today().strftime("%Y-%m")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.icon, c.color, c.monthly_budget,
                   COALESCE(SUM(e.amount), 0) as spent,
                   COUNT(e.id) as transaction_count
            FROM categories c
            LEFT JOIN expenses e ON c.id = e.category_id 
                                 AND strftime('%Y-%m', e.date) = ? 
                                 AND e.user_id = ?
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY spent DESC, c.name ASC
        """, (month_str, user_id, user_id))
        rows = [dict(r) for r in cursor.fetchall()]
        
        total_spent = sum(r["spent"] for r in rows)
        for r in rows:
            r["spent"] = round(r["spent"], 2)
            r["percentage_of_total"] = round((r["spent"] / total_spent * 100), 1) if total_spent > 0 else 0.0
            r["budget_utilization"] = round((r["spent"] / r["monthly_budget"] * 100), 1) if r["monthly_budget"] > 0 else 0.0
            r["remaining_budget"] = round(r["monthly_budget"] - r["spent"], 2)
        return rows

def get_daily_spending_trend(month_str=None, user_id=1):
    user_id = user_id or 1
    if not month_str:
        month_str = date.today().strftime("%Y-%m")
        
    year, month = map(int, month_str.split("-"))
    import calendar
    _, num_days = calendar.monthrange(year, month)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%d', date) as day, SUM(amount) as total
            FROM expenses
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
            GROUP BY day
            ORDER BY day ASC
        """, (month_str, user_id))
        spending_by_day = {int(row["day"]): row["total"] for row in cursor.fetchall()}
        
        labels = [f"{day:02d}" for day in range(1, num_days + 1)]
        values = [round(spending_by_day.get(day, 0.0), 2) for day in range(1, num_days + 1)]
        
        return {
            "labels": labels,
            "values": values,
            "month": month_str
        }

def get_monthly_history(num_months=6, user_id=1):
    user_id = user_id or 1
    today = date.today()
    months = []
    
    for i in range(num_months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        results = []
        for m in months:
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM expenses
                WHERE strftime('%Y-%m', date) = ? AND user_id = ?
            """, (m, user_id))
            total = cursor.fetchone()["total"]
            
            dt = datetime.strptime(m, "%Y-%m")
            label = dt.strftime("%b %Y")
            results.append({
                "month_code": m,
                "label": label,
                "total": round(total, 2)
            })
            
        return results

def get_payment_method_breakdown(month_str=None, user_id=1):
    user_id = user_id or 1
    if not month_str:
        month_str = date.today().strftime("%Y-%m")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT payment_method, SUM(amount) as total, COUNT(id) as count
            FROM expenses
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
            GROUP BY payment_method
            ORDER BY total DESC
        """, (month_str, user_id))
        return [dict(r) for r in cursor.fetchall()]

def get_available_months(user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT strftime('%Y-%m', date) as m FROM expenses WHERE user_id = ? ORDER BY m DESC", (user_id,))
        months = [r["m"] for r in cursor.fetchall() if r["m"]]
        current = date.today().strftime("%Y-%m")
        if current not in months:
            months.insert(0, current)
        return months

# ==================== Income & Cash Flow Operations (v2.0) ====================

def add_income(date_str, source, amount, payment_method, account_id=None, notes="", user_id=1):
    user_id = user_id or 1
    clean_source = source.strip()
    if not clean_source:
        raise ValueError("Income source is required.")
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Income amount must be greater than zero.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO income (date, source, amount, payment_method, account_id, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date_str, clean_source, amt, payment_method.strip(), account_id, (notes or "").strip(), user_id))
        conn.commit()
        return cursor.lastrowid

def get_income_list(user_id=1, start_date=None, end_date=None, limit=100, offset=0):
    user_id = user_id or 1
    conditions = ["i.user_id = ?"]
    params = [user_id]
    if start_date:
        conditions.append("i.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("i.date <= ?")
        params.append(end_date)
    where = f"WHERE {' AND '.join(conditions)}"
    
    query = f"""
        SELECT i.*, b.name as account_name, b.color as account_color, b.account_type as account_type
        FROM income i
        LEFT JOIN bank_accounts b ON i.account_id = b.id
        {where}
        ORDER BY i.date DESC, i.id DESC
    """
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def get_income(user_id=1, month_str=None, start_date=None, end_date=None, limit=100, offset=0):
    """Convenience alias for get_income_list supporting month_str parameter."""
    if month_str and not start_date and not end_date:
        start_date = f"{month_str}-01"
        end_date = f"{month_str}-31"
    return get_income_list(user_id=user_id, start_date=start_date, end_date=end_date, limit=limit, offset=offset)

def get_income_by_id(income_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, b.name as account_name, b.color as account_color
            FROM income i
            LEFT JOIN bank_accounts b ON i.account_id = b.id
            WHERE i.id = ? AND i.user_id = ?
        """, (income_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_income(income_id, date_str, source, amount, payment_method, account_id=None, notes="", user_id=1):
    user_id = user_id or 1
    clean_source = source.strip()
    if not clean_source:
        raise ValueError("Income source is required.")
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Income amount must be greater than zero.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE income
            SET date = ?, source = ?, amount = ?, payment_method = ?, account_id = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (date_str, clean_source, amt, payment_method.strip(), account_id, (notes or "").strip(), income_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_income(income_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM income WHERE id = ? AND user_id = ?", (income_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_total_income(user_id=1, month_str=None):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        if month_str:
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM income WHERE user_id = ? AND strftime('%Y-%m', date) = ?", (user_id, month_str))
        else:
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM income WHERE user_id = ?", (user_id,))
        return round(cursor.fetchone()[0], 2)

# ==================== Account Transfer Operations (v2.0) ====================

def add_transfer(date_str, from_account_id, to_account_id, amount, notes="", user_id=1):
    user_id = user_id or 1
    if int(from_account_id) == int(to_account_id):
        raise ValueError("Cannot transfer funds to the exact same account.")
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Transfer amount must be greater than zero.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transfers (date, from_account_id, to_account_id, amount, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date_str, int(from_account_id), int(to_account_id), amt, (notes or "").strip(), user_id))
        conn.commit()
        return cursor.lastrowid

def get_transfers(user_id=1, limit=50, offset=0):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*,
                   b1.name as from_account_name, b1.color as from_account_color,
                   b2.name as to_account_name, b2.color as to_account_color
            FROM transfers t
            JOIN bank_accounts b1 ON t.from_account_id = b1.id
            JOIN bank_accounts b2 ON t.to_account_id = b2.id
            WHERE t.user_id = ?
            ORDER BY t.date DESC, t.id DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        return [dict(r) for r in cursor.fetchall()]

def delete_transfer(transfer_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transfers WHERE id = ? AND user_id = ?", (transfer_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

# ==================== Cash Flow & Net Savings Calculation (v2.0) ====================

def get_cash_flow_summary(user_id=1, month_str=None):
    user_id = user_id or 1
    if not month_str:
        month_str = date.today().strftime("%Y-%m")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Monthly income
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(id) as count
            FROM income
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """, (user_id, month_str))
        inc_row = cursor.fetchone()
        total_income = round(inc_row["total"], 2)
        income_count = inc_row["count"]
        
        # Monthly expenses
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(id) as count
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """, (user_id, month_str))
        exp_row = cursor.fetchone()
        total_expenses = round(exp_row["total"], 2)
        expense_count = exp_row["count"]
        
        net_cash_flow = round(total_income - total_expenses, 2)
        savings_rate = round((net_cash_flow / total_income * 100), 1) if total_income > 0 else 0.0
        
        return {
            "month": month_str,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_cash_flow": net_cash_flow,
            "savings_rate": savings_rate,
            "income_count": income_count,
            "expense_count": expense_count,
        }

# ==================== Recurring Subscriptions & Bills Operations (v2.0) ====================

def add_subscription(name, amount, category_id=None, account_id=None, billing_cycle='Monthly', billing_day=1, next_due_date=None, notes="", auto_log=0, user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Subscription name is required.")
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Subscription amount must be positive.")
    if not next_due_date:
        next_due_date = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subscriptions (name, amount, category_id, account_id, billing_cycle, billing_day, next_due_date, notes, auto_log, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (clean_name, amt, category_id, account_id, billing_cycle, int(billing_day or 1), next_due_date, (notes or "").strip(), int(auto_log or 0), user_id))
        conn.commit()
        return cursor.lastrowid

def get_subscriptions(user_id=1, active_only=False):
    user_id = user_id or 1
    conditions = ["s.user_id = ?"]
    params = [user_id]
    if active_only:
        conditions.append("s.is_active = 1")
    where = f"WHERE {' AND '.join(conditions)}"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT s.*,
                   c.name as category_name, c.color as category_color, c.icon as category_icon,
                   b.name as account_name, b.color as account_color
            FROM subscriptions s
            LEFT JOIN categories c ON s.category_id = c.id
            LEFT JOIN bank_accounts b ON s.account_id = b.id
            {where}
            ORDER BY s.next_due_date ASC, s.name ASC
        """, params)
        rows = [dict(r) for r in cursor.fetchall()]
        today = date.today()
        for r in rows:
            try:
                due_dt = datetime.strptime(r["next_due_date"], "%Y-%m-%d").date()
                r["days_until_due"] = (due_dt - today).days
            except Exception:
                r["days_until_due"] = 0
        return rows

def get_subscription_by_id(sub_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*,
                   c.name as category_name, c.color as category_color,
                   b.name as account_name, b.color as account_color
            FROM subscriptions s
            LEFT JOIN categories c ON s.category_id = c.id
            LEFT JOIN bank_accounts b ON s.account_id = b.id
            WHERE s.id = ? AND s.user_id = ?
        """, (sub_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_subscription(sub_id, name, amount, category_id=None, account_id=None, billing_cycle='Monthly', billing_day=1, next_due_date=None, is_active=1, notes="", auto_log=0, user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Subscription name is required.")
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Subscription amount must be positive.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE subscriptions
            SET name = ?, amount = ?, category_id = ?, account_id = ?, billing_cycle = ?, billing_day = ?, next_due_date = ?, is_active = ?, notes = ?, auto_log = ?
            WHERE id = ? AND user_id = ?
        """, (clean_name, amt, category_id, account_id, billing_cycle, int(billing_day or 1), next_due_date, int(is_active), (notes or "").strip(), int(auto_log or 0), sub_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_subscription(sub_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def mark_subscription_paid(sub_id, user_id=1):
    """
    Logs an expense record for the subscription and advances its next_due_date.
    """
    sub = get_subscription_by_id(sub_id, user_id=user_id)
    if not sub:
        raise ValueError("Subscription not found.")
        
    today = date.today().isoformat()
    # Log expense
    cat_id = sub["category_id"] or 1
    add_expense(
        expense_date=today,
        category_id=cat_id,
        amount=sub["amount"],
        payment_method="Bank Transfer",
        description=f"Subscription: {sub['name']}",
        notes=f"Auto-logged subscription payment for {sub['name']}",
        user_id=user_id,
        account_id=sub["account_id"],
        is_recurring=1
    )
    
    # Calculate next due date
    try:
        current_due = datetime.strptime(sub["next_due_date"], "%Y-%m-%d").date()
    except Exception:
        current_due = date.today()
        
    cycle = sub.get("billing_cycle", "Monthly").capitalize()
    if cycle == "Weekly":
        next_dt = current_due + timedelta(days=7)
    elif cycle == "Yearly":
        try:
            next_dt = current_due.replace(year=current_due.year + 1)
        except ValueError:
            next_dt = current_due + timedelta(days=365)
    elif cycle == "Quarterly":
        next_dt = current_due + timedelta(days=91)
    else:  # Monthly default
        # Add ~1 month safely
        next_month = current_due.month + 1
        year = current_due.year
        if next_month > 12:
            next_month = 1
            year += 1
        day = min(sub.get("billing_day", 1), 28)
        next_dt = date(year, next_month, day)
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE subscriptions SET next_due_date = ? WHERE id = ? AND user_id = ?", (next_dt.isoformat(), sub_id, user_id))
        conn.commit()
    return next_dt.isoformat()

def get_upcoming_subscriptions(user_id=1, days=30):
    subs = get_subscriptions(user_id=user_id, active_only=True)
    return [s for s in subs if 0 <= s.get("days_until_due", 999) <= days]

# ==================== Financial Goals & Savings Pockets Operations (v2.0) ====================

def add_goal(name, target_amount, current_amount=0.0, target_date=None, color='#10B981', icon='bullseye', account_id=None, notes="", user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Goal name is required.")
    target = float(target_amount)
    if target <= 0:
        raise ValueError("Goal target amount must be positive.")
    current = max(0.0, float(current_amount or 0.0))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (name, target_amount, current_amount, target_date, color, icon, account_id, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (clean_name, target, current, target_date, color.strip(), icon.strip(), account_id, (notes or "").strip(), user_id))
        conn.commit()
        return cursor.lastrowid

def get_goals(user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, b.name as account_name, b.color as account_color
            FROM goals g
            LEFT JOIN bank_accounts b ON g.account_id = b.id
            WHERE g.user_id = ?
            ORDER BY g.target_date ASC, g.id ASC
        """, (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        today = date.today()
        for r in rows:
            target = r["target_amount"]
            current = r["current_amount"]
            r["remaining_amount"] = round(max(0.0, target - current), 2)
            r["progress_percentage"] = round(min(100.0, (current / target * 100)), 1) if target > 0 else 0.0
            r["is_completed"] = 1 if current >= target else 0
            if r.get("target_date"):
                try:
                    tgt_dt = datetime.strptime(r["target_date"], "%Y-%m-%d").date()
                    days = (tgt_dt - today).days
                    r["days_remaining"] = max(0, days)
                    months_left = max(1, round(days / 30))
                    r["suggested_monthly_savings"] = round(r["remaining_amount"] / months_left, 2)
                except Exception:
                    r["days_remaining"] = None
                    r["suggested_monthly_savings"] = None
            else:
                r["days_remaining"] = None
                r["suggested_monthly_savings"] = None
        return rows

def get_goal_by_id(goal_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, b.name as account_name, b.color as account_color
            FROM goals g
            LEFT JOIN bank_accounts b ON g.account_id = b.id
            WHERE g.id = ? AND g.user_id = ?
        """, (goal_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        r = dict(row)
        target = r["target_amount"]
        current = r["current_amount"]
        r["remaining_amount"] = round(max(0.0, target - current), 2)
        r["progress_percentage"] = round(min(100.0, (current / target * 100)), 1) if target > 0 else 0.0
        return r

def update_goal(goal_id, name, target_amount, current_amount, target_date=None, color='#10B981', icon='bullseye', account_id=None, notes="", user_id=1):
    user_id = user_id or 1
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Goal name is required.")
    target = float(target_amount)
    if target <= 0:
        raise ValueError("Goal target amount must be positive.")
    current = max(0.0, float(current_amount or 0.0))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE goals
            SET name = ?, target_amount = ?, current_amount = ?, target_date = ?, color = ?, icon = ?, account_id = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (clean_name, target, current, target_date, color.strip(), icon.strip(), account_id, (notes or "").strip(), goal_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def contribute_to_goal(goal_id, amount, from_account_id=None, user_id=1):
    user_id = user_id or 1
    amt = float(amount)
    if amt <= 0:
        raise ValueError("Contribution amount must be positive.")
    goal = get_goal_by_id(goal_id, user_id=user_id)
    if not goal:
        raise ValueError("Goal not found.")
    new_amount = round(goal["current_amount"] + amt, 2)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE goals SET current_amount = ? WHERE id = ? AND user_id = ?", (new_amount, goal_id, user_id))
        conn.commit()
    return new_amount

def delete_goal(goal_id, user_id=1):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

# ==================== Two-Factor Authentication Security (v2.0) ====================

def update_user_2fa(user_id, enabled, secret=None):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        if enabled:
            cursor.execute("UPDATE users SET two_factor_enabled = 1, totp_secret = ? WHERE id = ?", (secret, user_id))
        else:
            cursor.execute("UPDATE users SET two_factor_enabled = 0, totp_secret = NULL WHERE id = ?", (user_id,))
        conn.commit()
        return True

def get_user_2fa_info(user_id):
    user_id = user_id or 1
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT two_factor_enabled, totp_secret, username, email FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
