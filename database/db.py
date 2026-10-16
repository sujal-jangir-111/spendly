import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    """Return a SQLite connection with dict-like rows and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Safe to call multiple times."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    """Insert a demo user and sample expenses. Does nothing if users already exist."""
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    today = date.today()
    sample_expenses = [
        (250.0, "Food", 1, "Groceries"),
        (120.0, "Transport", 3, "Metro card recharge"),
        (1500.0, "Bills", 5, "Electricity bill"),
        (450.0, "Health", 8, "Pharmacy"),
        (300.0, "Entertainment", 11, "Movie tickets"),
        (899.0, "Shopping", 14, "T-shirt"),
        (200.0, "Other", 18, "Gift"),
        (180.0, "Food", 22, "Lunch out"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, amount, category, today.replace(day=day).isoformat(), description)
            for amount, category, day, description in sample_expenses
        ],
    )
    conn.commit()
    conn.close()
