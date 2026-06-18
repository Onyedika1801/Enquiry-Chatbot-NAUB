"""
Database layer using SQLite (zero external dependencies).
Handles conversation logs and admin knowledge base management.
"""

import sqlite3
import os
import json
import hashlib
import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "naub_chatbot.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                intent TEXT,
                category TEXT,
                similarity_score REAL,
                matched INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                message_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_logs_session ON conversation_logs(session_id);
            CREATE INDEX IF NOT EXISTS idx_logs_intent ON conversation_logs(intent);
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON conversation_logs(timestamp);
        """)

        # Create default admin user if none exists
        existing = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
        if existing == 0:
            pw_hash = hashlib.sha256("naub@admin2024".encode()).hexdigest()
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("admin", pw_hash, _now())
            )


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


# ─── Session Management ────────────────────────────────────────────────────────

def get_or_create_session(session_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE sessions SET last_active = ? WHERE id = ?",
                (_now(), session_id)
            )
            return dict(row)
        else:
            now = _now()
            conn.execute(
                "INSERT INTO sessions (id, started_at, last_active, message_count) VALUES (?, ?, ?, 0)",
                (session_id, now, now)
            )
            return {"id": session_id, "started_at": now, "last_active": now, "message_count": 0}


def increment_session_count(session_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1, last_active = ? WHERE id = ?",
            (_now(), session_id)
        )


# ─── Conversation Logging ──────────────────────────────────────────────────────

def log_conversation(session_id: str, user_message: str, bot_response: str,
                     intent: str, category: str, score: float, matched: bool):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO conversation_logs
               (session_id, user_message, bot_response, intent, category, similarity_score, matched, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_message, bot_response, intent, category, score, int(matched), _now())
        )
    increment_session_count(session_id)


def get_session_history(session_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT user_message, bot_response, intent, timestamp
               FROM conversation_logs WHERE session_id = ?
               ORDER BY id ASC LIMIT 50""",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Admin Analytics ───────────────────────────────────────────────────────────

def get_analytics() -> dict:
    with get_db() as conn:
        total_messages = conn.execute("SELECT COUNT(*) FROM conversation_logs").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        matched_count = conn.execute("SELECT COUNT(*) FROM conversation_logs WHERE matched = 1").fetchone()[0]
        fallback_count = conn.execute("SELECT COUNT(*) FROM conversation_logs WHERE matched = 0").fetchone()[0]

        top_intents = conn.execute(
            """SELECT intent, COUNT(*) as count FROM conversation_logs
               WHERE matched = 1 GROUP BY intent ORDER BY count DESC LIMIT 10"""
        ).fetchall()

        recent_logs = conn.execute(
            """SELECT session_id, user_message, intent, similarity_score, timestamp
               FROM conversation_logs ORDER BY id DESC LIMIT 20"""
        ).fetchall()

        daily_stats = conn.execute(
            """SELECT substr(timestamp, 1, 10) as date, COUNT(*) as count
               FROM conversation_logs GROUP BY date ORDER BY date DESC LIMIT 7"""
        ).fetchall()

    accuracy = round((matched_count / total_messages * 100), 1) if total_messages > 0 else 0

    return {
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "matched_count": matched_count,
        "fallback_count": fallback_count,
        "accuracy": accuracy,
        "top_intents": [dict(r) for r in top_intents],
        "recent_logs": [dict(r) for r in recent_logs],
        "daily_stats": [dict(r) for r in daily_stats],
    }


# ─── Admin Auth ────────────────────────────────────────────────────────────────

def verify_admin(username: str, password: str) -> bool:
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM admin_users WHERE username = ? AND password_hash = ?",
            (username, pw_hash)
        ).fetchone()
    return row is not None
