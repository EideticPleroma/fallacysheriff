"""
Tests for SQLite database operations.

Tests tweet processing tracking, duplicate prevention, and poll state.
"""

import os
import sqlite3
import pytest

from app.database import (
    init_db,
    is_processed,
    mark_processed,
    get_connection,
    get_last_seen_id,
    set_last_seen_id,
)


class TestInitDb:
    """Tests for database initialization."""

    def test_init_creates_processed_tweets_table(self, tmp_path):
        """Test that init_db creates the processed_tweets table."""
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_tweets'"
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "processed_tweets"

    def test_init_creates_poll_state_table(self, tmp_path):
        """Test that init_db creates the poll_state table."""
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='poll_state'"
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "poll_state"

    def test_init_creates_parent_directory(self, tmp_path):
        """Test that init_db creates parent directories if needed."""
        db_path = str(tmp_path / "subdir" / "nested" / "test.db")
        init_db(db_path)

        assert os.path.exists(db_path)

    def test_init_idempotent(self, tmp_path):
        """Test that calling init_db multiple times is safe."""
        db_path = str(tmp_path / "test.db")

        # Call multiple times
        init_db(db_path)
        init_db(db_path)
        init_db(db_path)

        # Should still work
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM processed_tweets")
            assert cursor.fetchone()[0] == 0

    def test_init_memory_database(self):
        """Test that :memory: database works."""
        init_db(":memory:")
        # Should not raise


class TestIsProcessed:
    """Tests for checking if tweets are processed."""

    def test_is_processed_returns_false_for_new(self, test_db):
        """Test that new tweet IDs return False."""
        result = is_processed("new_tweet_123", db_path=test_db)
        assert result is False

    def test_is_processed_returns_true_after_mark(self, test_db):
        """Test that marked tweets return True."""
        tweet_id = "tweet_456"
        mark_processed(tweet_id, db_path=test_db)

        result = is_processed(tweet_id, db_path=test_db)
        assert result is True

    def test_is_processed_different_ids(self, test_db):
        """Test that different tweet IDs are tracked separately."""
        mark_processed("tweet_1", db_path=test_db)

        assert is_processed("tweet_1", db_path=test_db) is True
        assert is_processed("tweet_2", db_path=test_db) is False


class TestMarkProcessed:
    """Tests for marking tweets as processed."""

    def test_mark_processed_inserts_record(self, test_db):
        """Test that mark_processed inserts a record."""
        tweet_id = "tweet_789"
        mark_processed(tweet_id, db_path=test_db)

        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT tweet_id FROM processed_tweets WHERE tweet_id = ?",
                (tweet_id,)
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == tweet_id

    def test_mark_processed_stores_timestamp(self, test_db):
        """Test that mark_processed stores a timestamp."""
        tweet_id = "tweet_timestamp"
        mark_processed(tweet_id, db_path=test_db)

        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT processed_at FROM processed_tweets WHERE tweet_id = ?",
                (tweet_id,)
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] is not None
        # Should be ISO format timestamp
        assert "T" in result[0]

    def test_duplicate_insert_ignored(self, test_db):
        """Test that duplicate inserts are ignored (not errored)."""
        tweet_id = "duplicate_tweet"

        # Insert twice
        mark_processed(tweet_id, db_path=test_db)
        mark_processed(tweet_id, db_path=test_db)

        # Should only have one record
        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM processed_tweets WHERE tweet_id = ?",
                (tweet_id,)
            )
            count = cursor.fetchone()[0]

        assert count == 1


class TestGetConnection:
    """Tests for database connection context manager."""

    def test_get_connection_returns_valid_connection(self, test_db):
        """Test that get_connection returns a working connection."""
        with get_connection(db_path=test_db) as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()

        assert result[0] == 1

    def test_get_connection_closes_on_exit(self, test_db):
        """Test that connection is closed after context exit."""
        with get_connection(db_path=test_db) as conn:
            pass

        # Attempting to use closed connection should fail
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


class TestPollState:
    """Tests for poll state (last_seen_id) tracking."""

    def test_get_last_seen_id_returns_none_initially(self, test_db):
        """Test that get_last_seen_id returns None when not set."""
        result = get_last_seen_id(db_path=test_db)
        assert result is None

    def test_set_and_get_last_seen_id(self, test_db):
        """Test setting and getting last_seen_id."""
        tweet_id = "123456789"
        set_last_seen_id(tweet_id, db_path=test_db)

        result = get_last_seen_id(db_path=test_db)
        assert result == tweet_id

    def test_set_last_seen_id_updates(self, test_db):
        """Test that set_last_seen_id updates existing value."""
        set_last_seen_id("111", db_path=test_db)
        set_last_seen_id("222", db_path=test_db)

        result = get_last_seen_id(db_path=test_db)
        assert result == "222"

    def test_set_last_seen_id_stores_timestamp(self, test_db):
        """Test that set_last_seen_id stores a timestamp."""
        set_last_seen_id("123", db_path=test_db)

        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT updated_at FROM poll_state WHERE key = 'last_seen_id'"
            )
            result = cursor.fetchone()

        assert result is not None
        assert "T" in result[0]  # ISO format
