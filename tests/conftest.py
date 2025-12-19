"""
Pytest fixtures for FallacySheriff tests.

Provides mock clients, test database, and FastAPI test client.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, AsyncMock

from fastapi.testclient import TestClient

from app.config import Settings, override_settings
from app.database import init_db
from app.rss_client import RSSMention


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables before any imports."""
    os.environ.setdefault("TWITTER_CONSUMER_KEY", "test_consumer_key")
    os.environ.setdefault("TWITTER_CONSUMER_SECRET", "test_consumer_secret")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN", "test_access_token")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN_SECRET", "test_access_token_secret")
    os.environ.setdefault("TWITTER_BEARER_TOKEN", "test_bearer_token")
    os.environ.setdefault("BOT_USER_ID", "123456789")
    os.environ.setdefault("BOT_USERNAME", "FallacySheriff")
    os.environ.setdefault("RSSHUB_URL", "http://localhost:1200")
    os.environ.setdefault("GROK_API_KEY", "test_grok_key")
    os.environ.setdefault("POLL_INTERVAL_MINUTES", "5")
    os.environ.setdefault("DATABASE_PATH", ":memory:")


@pytest.fixture
def test_settings():
    """Create test settings with in-memory database."""
    settings = Settings(
        twitter_consumer_key="test_consumer_key",
        twitter_consumer_secret="test_consumer_secret",
        twitter_access_token="test_access_token",
        twitter_access_token_secret="test_access_token_secret",
        twitter_bearer_token="test_bearer_token",
        bot_user_id="123456789",
        bot_username="FallacySheriff",
        rsshub_url="http://localhost:1200",
        rsshub_access_key=None,
        grok_api_key="test_grok_key",
        poll_interval_minutes=5,
        database_path=":memory:",
    )
    override_settings(settings)
    return settings


@pytest.fixture
def test_db(test_settings, tmp_path):
    """Create a temporary test database."""
    db_path = str(tmp_path / "test_tweets.db")
    init_db(db_path)
    return db_path


@pytest.fixture
def mock_twitter_client():
    """Create a mock Tweepy client for posting replies."""
    mock_client = MagicMock()

    # Mock create_tweet response (only function we still use)
    mock_create_data = {"id": "123456789"}
    mock_create_response = MagicMock()
    mock_create_response.data = mock_create_data
    mock_client.create_tweet.return_value = mock_create_response

    return mock_client


@pytest.fixture
def mock_grok_client():
    """Create a mock OpenAI client for Grok API (legacy non-JSON response)."""
    mock_client = MagicMock()

    # Mock chat completion response (legacy format)
    mock_message = MagicMock()
    mock_message.content = (
        "Bandwagon Fallacy\n"
        "Pro: Popular opinion can sometimes reflect wisdom.\n"
        "Con: Popularity doesn't equal truth.\n"
        "More: yourlogicalfallacyis.com/bandwagon"
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_grok_client_json():
    """Create a mock OpenAI client for Grok API with JSON response."""
    mock_client = MagicMock()

    # Mock chat completion response with JSON format
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "confidence": 95,
        "fallacy_detected": True,
        "fallacy_name": "Bandwagon Fallacy",
        "reply": "Bandwagon Fallacy\\nPro: Popular opinion can sometimes reflect wisdom.\\nCon: Popularity doesn't equal truth.\\nMore: yourlogicalfallacyis.com/bandwagon"
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def client(test_settings):
    """Create FastAPI test client with mocked scheduler and poll_mentions."""
    from unittest.mock import patch, AsyncMock

    # Mock the scheduler and initial poll to avoid database issues during startup
    with patch("app.main.AsyncIOScheduler") as mock_scheduler_class, \
         patch("app.main.poll_mentions", new_callable=AsyncMock) as mock_poll:

        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_class.return_value = mock_scheduler

        from app.main import app

        with TestClient(app) as test_client:
            yield test_client


# RSS-based mention fixtures

@pytest.fixture
def sample_rss_mention():
    """Sample RSS mention data with trigger phrase."""
    return RSSMention(
        tweet_id="1234567890",
        text="@FallacySheriff fallacyme",
        author_username="some_user",
        published="2025-01-01T12:00:00Z",
        link="https://twitter.com/some_user/status/1234567890",
        in_reply_to_tweet_id="9876543210",
        in_reply_to_username="fallacy_poster",
    )


@pytest.fixture
def sample_rss_mention_no_trigger():
    """Sample RSS mention without trigger phrase."""
    return RSSMention(
        tweet_id="1234567890",
        text="@FallacySheriff hello there",
        author_username="some_user",
        published="2025-01-01T12:00:00Z",
        link="https://twitter.com/some_user/status/1234567890",
        in_reply_to_tweet_id="9876543210",
        in_reply_to_username="fallacy_poster",
    )


@pytest.fixture
def sample_rss_mention_not_reply():
    """Sample RSS mention that's not a reply."""
    return RSSMention(
        tweet_id="1234567890",
        text="@FallacySheriff fallacyme",
        author_username="some_user",
        published="2025-01-01T12:00:00Z",
        link="https://twitter.com/some_user/status/1234567890",
        in_reply_to_tweet_id=None,
        in_reply_to_username=None,
    )


# Legacy dict-based fixtures (for backwards compatibility if needed)

@pytest.fixture
def sample_mention():
    """Sample mention data from polling (legacy dict format)."""
    return {
        "id": "1234567890",
        "text": "@FallacySheriff fallacyme",
        "author_id": "111222333",
        "in_reply_to_tweet_id": "9876543210",
        "parent_tweet_text": "Everyone knows AI is bad for the environment!",
    }


@pytest.fixture
def sample_mention_no_trigger():
    """Sample mention without trigger phrase (legacy dict format)."""
    return {
        "id": "1234567890",
        "text": "@FallacySheriff hello there",
        "author_id": "111222333",
        "in_reply_to_tweet_id": "9876543210",
        "parent_tweet_text": None,
    }


@pytest.fixture
def sample_mention_not_reply():
    """Sample mention that's not a reply (legacy dict format)."""
    return {
        "id": "1234567890",
        "text": "@FallacySheriff fallacyme",
        "author_id": "111222333",
        "in_reply_to_tweet_id": None,
        "parent_tweet_text": None,
    }
