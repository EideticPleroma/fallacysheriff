"""
SQLite database operations for tracking processed tweets and poll state.
Prevents duplicate replies by storing tweet IDs.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from app.config import get_settings


def _get_db_path() -> str:
    """Get database path from settings."""
    return get_settings().database_path


def init_db(db_path: str | None = None) -> None:
    """
    Initialize the database and create tables if they don't exist.

    Args:
        db_path: Optional path override (used for testing)
    """
    path = db_path or _get_db_path()

    # Create parent directory if it doesn't exist (skip for :memory:)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        # Table for tracking processed tweets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_tweets (
                tweet_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)

        # Table for storing poll state (like last_seen_id)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS poll_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()


@contextmanager
def get_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.

    Args:
        db_path: Optional path override (used for testing)

    Yields:
        SQLite connection
    """
    path = db_path or _get_db_path()
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def is_processed(tweet_id: str, db_path: str | None = None) -> bool:
    """
    Check if a tweet has already been processed.

    Args:
        tweet_id: The tweet ID to check
        db_path: Optional path override (used for testing)

    Returns:
        True if tweet was already processed, False otherwise
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM processed_tweets WHERE tweet_id = ?",
            (tweet_id,)
        )
        return cursor.fetchone() is not None


def mark_processed(tweet_id: str, db_path: str | None = None) -> None:
    """
    Mark a tweet as processed.

    Args:
        tweet_id: The tweet ID to mark as processed
        db_path: Optional path override (used for testing)
    """
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_tweets (tweet_id, processed_at) VALUES (?, ?)",
            (tweet_id, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()


def get_last_seen_id(db_path: str | None = None) -> str | None:
    """
    Get the last seen tweet ID for polling.

    Args:
        db_path: Optional path override (used for testing)

    Returns:
        The last seen tweet ID, or None if not set
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT value FROM poll_state WHERE key = 'last_seen_id'"
        )
        row = cursor.fetchone()
        return row[0] if row else None


def set_last_seen_id(tweet_id: str, db_path: str | None = None) -> None:
    """
    Set the last seen tweet ID for polling.

    Args:
        tweet_id: The tweet ID to store
        db_path: Optional path override (used for testing)
    """
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO poll_state (key, value, updated_at) 
            VALUES ('last_seen_id', ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
            """,
            (
                tweet_id,
                datetime.now(timezone.utc).isoformat(),
                tweet_id,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()
