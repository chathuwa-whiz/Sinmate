"""
SQLite-backed Persistent Fact Store & Conversation History for Sinmate.

Stores:
- Structured user facts (e.g., daily schedule, emotional context, relationship facts)
- Recent conversational turns
- Interaction timestamps for proactive heartbeat analysis
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional


class MemoryStore:
    """Manages SQLite persistent memory."""

    def __init__(self, db_path: str = "sinmate_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            # Facts & Summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    importance INTEGER DEFAULT 1
                )
            """)
            # System events table (for silence and activity tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT
                )
            """)
            conn.commit()

    def log_interaction(self, role: str, persona: str, message: str):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.cursor().execute(
                "INSERT INTO conversations (timestamp, role, persona, message) VALUES (?, ?, ?, ?)",
                (timestamp, role, persona, message)
            )
            conn.commit()

    def add_user_fact(self, category: str, fact: str, importance: int = 1):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.cursor().execute(
                "INSERT INTO user_facts (created_at, category, fact, importance) VALUES (?, ?, ?, ?)",
                (timestamp, category, fact, importance)
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, role, persona, message FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {"timestamp": r[0], "role": r[1], "persona": r[2], "message": r[3]}
                for r in reversed(rows)
            ]

    def get_user_facts_summary(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, fact FROM user_facts ORDER BY importance DESC LIMIT 15")
            rows = cursor.fetchall()
            if not rows:
                return "No stored facts yet."
            return "\n".join([f"- [{cat}]: {fact}" for cat, fact in rows])
