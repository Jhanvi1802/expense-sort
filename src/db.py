"""SQLite data layer (stdlib only — no ORM, no external deps).

One file owns the schema and connection so the rest of the app just calls
`get_db()` for a row-dict cursor. Foreign keys are on; every user-owned row
carries a user_id so data is isolated per account.
"""
import os
import sqlite3

DB_PATH = os.environ.get("EXPENSESORT_DB",
                         os.path.join(os.path.dirname(os.path.dirname(__file__)), "expensesort.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  upi_id TEXT,
  phone TEXT,
  photo TEXT,                    -- data URL or empty
  monthly_income REAL DEFAULT 0,
  prefs TEXT DEFAULT '{}',       -- JSON: theme, language, currency
  notif TEXT DEFAULT '{}',       -- JSON: alert toggles
  tax_regime TEXT DEFAULT 'new',
  onboarded INTEGER DEFAULT 0,
  pw_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS statements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  source TEXT,
  uploaded_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  statement_id INTEGER,
  txn_date TEXT,                -- ISO yyyy-mm-dd if known
  month TEXT,                   -- yyyy-mm bucket
  description TEXT NOT NULL,
  merchant_key TEXT,            -- normalized merchant for grouping
  amount REAL NOT NULL,
  balance REAL,                 -- running balance after txn (if from a statement)
  direction TEXT,               -- credit | debit | null
  category TEXT NOT NULL,
  confidence REAL DEFAULT 0,
  is_recurring INTEGER DEFAULT 0,
  tax_section TEXT,             -- 80C | 80D | null
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS budgets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  category TEXT NOT NULL,
  limit_amount REAL NOT NULL,
  UNIQUE(user_id, category),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  kind TEXT DEFAULT 'general',   -- trip | flat | family | general
  created_by INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS group_members (
  group_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  display_name TEXT NOT NULL,
  PRIMARY KEY (group_id, user_id),
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  description TEXT NOT NULL,
  amount REAL NOT NULL,
  paid_by INTEGER NOT NULL,        -- user_id who paid
  method TEXT DEFAULT 'equal',     -- equal | shares | percent | exact
  created_by INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  recurring INTEGER DEFAULT 0,     -- auto-repeat monthly
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expense_shares (
  expense_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  owed REAL NOT NULL,
  PRIMARY KEY (expense_id, user_id),
  FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settlements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  from_user INTEGER NOT NULL,
  to_user INTEGER NOT NULL,
  amount REAL NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  target REAL NOT NULL,
  saved REAL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tax_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  section TEXT NOT NULL,
  label TEXT NOT NULL,
  amount REAL NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS custom_categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  color TEXT DEFAULT '#94a3b8',
  icon TEXT DEFAULT '📦',
  UNIQUE(user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_txn_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_txn_month ON transactions(user_id, month);
CREATE INDEX IF NOT EXISTS ix_members_user ON group_members(user_id);
"""

# columns added after v4.0 — ALTER them into pre-existing databases
_MIGRATIONS = [
    ("users", "phone", "TEXT"),
    ("users", "photo", "TEXT"),
    ("users", "prefs", "TEXT DEFAULT '{}'"),
    ("users", "notif", "TEXT DEFAULT '{}'"),
    ("users", "tax_regime", "TEXT DEFAULT 'new'"),
    ("users", "onboarded", "INTEGER DEFAULT 0"),
    ("transactions", "balance", "REAL"),
]


def _migrate(conn):
    for table, col, decl in _MIGRATIONS:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.commit()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _migrate(conn)
    finally:
        conn.close()


def query(sql, params=(), one=False):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def execute(sql, params=()):
    """Run a write; return lastrowid."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def executemany(sql, seq):
    conn = get_conn()
    try:
        conn.executemany(sql, seq)
        conn.commit()
    finally:
        conn.close()
