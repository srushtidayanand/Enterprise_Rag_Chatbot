import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enterprise_rag.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            token TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            confidence REAL DEFAULT 0.0,
            response_time_ms INTEGER DEFAULT 0,
            sources_count INTEGER DEFAULT 0,
            feedback INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            sources TEXT,
            confidence REAL DEFAULT 0.0,
            response_time_ms INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)

    # Seed demo users
    for username, password, role in [
        ("john",  "password123", "employee"),
        ("alice", "password123", "hr"),
        ("bob",   "password123", "manager"),
        ("admin", "admin123",    "admin"),
    ]:
        c.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, _hash(password), role),
        )

    conn.commit()
    conn.close()


init_db()
