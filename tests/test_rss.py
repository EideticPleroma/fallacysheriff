"""
Tests for RSS client module.

Tests RSS feed parsing, mention extraction, and tweet chain fetching.
"""

from unittest.mock import patch, MagicMock

import pytest

from app.rss_client import (
    RSSMention,
    TweetData,
    fetch_mentions_rss,
    fetch_tweet_data,
    fetch_tweet_chain,
    _extract_tweet_id_from_link,
    _extract_username_from_link,
    _extract_text_from_entry,
    _extract_reply_info_from_entry,
)


class TestExtractTweetIdFromLink:
    """Tests for _extract_tweet_id_from_link helper."""

    def test_extracts_id_from_twitter_url(self):
        """Test extraction from twitter.com URL."""
        url = "https://twitter.com/someuser/status/1234567890"
        assert _extract_tweet_id_from_link(url) == "1234567890"

    def test_extracts_id_from_x_url(self):
        """Test extraction from x.com URL."""
        url = "https://x.com/someuser/status/9876543210"
        assert _extract_tweet_id_from_link(url) == "9876543210"

    def test_returns_none_for_invalid_url(self):
        """Test returns None for non-Twitter URLs."""
        url = "https://example.com/page"
        assert _extract_tweet_id_from_link(url) is None

    def test_handles_url_with_query_params(self):
        """Test extraction from URL with query parameters."""
        url = "https://twitter.com/user/status/1234567890?ref=123"
        assert _extract_tweet_id_from_link(url) == "1234567890"


class TestExtractUsernameFromLink:
    """Tests for _extract_username_from_link helper."""

    def test_extracts_username_from_twitter_url(self):
        """Test extraction from twitter.com URL."""
        url = "https://twitter.com/someuser/status/1234567890"
        assert _extract_username_from_link(url) == "someuser"

    def test_extracts_username_from_x_url(self):
        """Test extraction from x.com URL."""
        url = "https://x.com/anotheruser/status/9876543210"
        assert _extract_username_from_link(url) == "anotheruser"

    def test_returns_none_for_invalid_url(self):
        """Test returns None for non-Twitter URLs."""
        url = "https://example.com/page"
        assert _extract_username_from_link(url) is None


class TestExtractTextFromEntry:
    """Tests for _extract_text_from_entry helper."""

    def test_extracts_from_summary(self):
        """Test extraction from summary field."""
        entry = MagicMock()
        entry.summary = "This is the tweet text"
        del entry.description
        del entry.content

        result = _extract_text_from_entry(entry)
        assert result == "This is the tweet text"

    def test_strips_html_tags(self):
        """Test that HTML tags are stripped."""
        entry = MagicMock()
        entry.summary = "<p>Tweet with <a href='#'>link</a></p>"
        del entry.description
        del entry.content

        result = _extract_text_from_entry(entry)
        assert "<" not in result
        assert ">" not in result

    def test_unescapes_html_entities(self):
        """Test that HTML entities are unescaped."""
        entry = MagicMock()
        entry.summary = "Tom &amp; Jerry &gt; everything"
        del entry.description
        del entry.content

        result = _extract_text_from_entry(entry)
        assert "&amp;" not in result
        assert "&gt;" not in result
        assert "Tom & Jerry > everything" == result


class TestExtractReplyInfo:
    """Tests for _extract_reply_info_from_entry helper."""

    def test_extracts_reply_from_link_in_content(self):
        """Test extraction of reply-to info from embedded link."""
        entry = MagicMock()
        entry.summary = 'Replying to <a href="https://twitter.com/original_user/status/111222333">tweet</a>'
        del entry.description
        del entry.content

        tweet_id, username = _extract_reply_info_from_entry(entry)

        assert tweet_id == "111222333"
        assert username == "original_user"

    def test_extracts_username_from_replying_to_text(self):
        """Test extraction of username from 'Replying to @user' text."""
        entry = MagicMock()
        entry.summary = "Replying to @someuser This is my reply"
        del entry.description
        del entry.content

        tweet_id, username = _extract_reply_info_from_entry(entry)

        # Tweet ID not available, but username is
        assert tweet_id is None
        assert username == "someuser"

    def test_returns_none_for_no_reply_info(self):
        """Test returns None when no reply info found."""
        entry = MagicMock()
        entry.summary = "Just a regular tweet"
        del entry.description
        del entry.content

        tweet_id, username = _extract_reply_info_from_entry(entry)

        assert tweet_id is None
        assert username is None


class TestFetchMentionsRss:
    """Tests for fetch_mentions_rss function."""

    @patch("app.rss_client.feedparser.parse")
    @patch("app.rss_client.get_settings")
    def test_fetches_and_parses_feed(self, mock_settings, mock_parse):
        """Test that feed is fetched and parsed correctly."""
        mock_settings.return_value.rsshub_url = "http://localhost:1200"
        mock_settings.return_value.rsshub_access_key = None
        mock_settings.return_value.bot_username = "FallacySheriff"

        mock_entry = MagicMock()
        mock_entry.link = "https://twitter.com/user123/status/999888777"
        mock_entry.summary = "@FallacySheriff fallacyme"
        mock_entry.published = "2025-01-01T12:00:00Z"
        del mock_entry.description
        del mock_entry.content

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        result = fetch_mentions_rss()

        assert len(result) == 1
        assert result[0].tweet_id == "999888777"
        assert result[0].author_username == "user123"

    @patch("app.rss_client.feedparser.parse")
    @patch("app.rss_client.get_settings")
    def test_handles_feed_parse_error(self, mock_settings, mock_parse):
        """Test graceful handling of feed parse errors."""
        mock_settings.return_value.rsshub_url = "http://localhost:1200"
        mock_settings.return_value.rsshub_access_key = None
        mock_settings.return_value.bot_username = "FallacySheriff"

        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_parse.return_value = mock_feed

        result = fetch_mentions_rss()

        assert result == []

    @patch("app.rss_client.feedparser.parse")
    @patch("app.rss_client.get_settings")
    def test_adds_access_key_if_configured(self, mock_settings, mock_parse):
        """Test that access key is added to URL when configured."""
        mock_settings.return_value.rsshub_url = "http://localhost:1200"
        mock_settings.return_value.rsshub_access_key = "secret123"
        mock_settings.return_value.bot_username = "FallacySheriff"

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        fetch_mentions_rss()

        call_url = mock_parse.call_args[0][0]
        assert "key=secret123" in call_url


class TestFetchTweetData:
    """Tests for fetch_tweet_data function."""

    @patch("app.rss_client.feedparser.parse")
    @patch("app.rss_client.get_settings")
    def test_fetches_tweet_data(self, mock_settings, mock_parse):
        """Test fetching tweet data via RSS."""
        mock_settings.return_value.rsshub_url = "http://localhost:1200"
        mock_settings.return_value.rsshub_access_key = None

        mock_entry = MagicMock()
        mock_entry.summary = "This is the fallacy tweet"
        del mock_entry.description
        del mock_entry.content

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        result = fetch_tweet_data("123456", "someuser")

        assert result is not None
        assert result.tweet_id == "123456"
        assert result.author_username == "someuser"
        assert result.text == "This is the fallacy tweet"

    @patch("app.rss_client.feedparser.parse")
    @patch("app.rss_client.get_settings")
    def test_returns_none_on_empty_feed(self, mock_settings, mock_parse):
        """Test returns None when feed has no entries."""
        mock_settings.return_value.rsshub_url = "http://localhost:1200"
        mock_settings.return_value.rsshub_access_key = None

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        result = fetch_tweet_data("123456", "someuser")

        assert result is None


class TestFetchTweetChain:
    """Tests for fetch_tweet_chain function."""

    @patch("app.rss_client.fetch_tweet_data")
    def test_fetches_two_level_chain(self, mock_fetch_tweet):
        """Test fetching complete tweet chain (fallacy + original)."""
        # Setup: mention -> fallacy tweet -> original tweet
        fallacy_tweet = TweetData(
            tweet_id="222",
            text="This is a stupid argument!",
            author_username="fallacy_user",
            in_reply_to_tweet_id="111",
            in_reply_to_username="original_user",
        )

        original_tweet = TweetData(
            tweet_id="111",
            text="Here is my original statement",
            author_username="original_user",
            in_reply_to_tweet_id=None,
            in_reply_to_username=None,
        )

        mock_fetch_tweet.side_effect = [fallacy_tweet, original_tweet]

        mention = RSSMention(
            tweet_id="333",
            text="@FallacySheriff fallacyme",
            author_username="tagger",
            published="2025-01-01",
            link="https://twitter.com/tagger/status/333",
            in_reply_to_tweet_id="222",
            in_reply_to_username="fallacy_user",
        )

        fallacy_text, original_text = fetch_tweet_chain(mention)

        assert fallacy_text == "This is a stupid argument!"
        assert original_text == "Here is my original statement"

    @patch("app.rss_client.fetch_tweet_data")
    def test_returns_none_when_no_reply_to_info(self, mock_fetch_tweet):
        """Test returns None when mention has no reply-to info."""
        mention = RSSMention(
            tweet_id="333",
            text="@FallacySheriff fallacyme",
            author_username="tagger",
            published="2025-01-01",
            link="https://twitter.com/tagger/status/333",
            in_reply_to_tweet_id=None,
            in_reply_to_username=None,
        )

        fallacy_text, original_text = fetch_tweet_chain(mention)

        assert fallacy_text is None
        assert original_text is None
        mock_fetch_tweet.assert_not_called()

    @patch("app.rss_client.fetch_tweet_data")
    def test_handles_missing_original_tweet(self, mock_fetch_tweet):
        """Test handling when original tweet cannot be fetched."""
        fallacy_tweet = TweetData(
            tweet_id="222",
            text="This is a stupid argument!",
            author_username="fallacy_user",
            in_reply_to_tweet_id="111",
            in_reply_to_username="original_user",
        )

        # First call returns fallacy tweet, second call returns None
        mock_fetch_tweet.side_effect = [fallacy_tweet, None]

        mention = RSSMention(
            tweet_id="333",
            text="@FallacySheriff fallacyme",
            author_username="tagger",
            published="2025-01-01",
            link="https://twitter.com/tagger/status/333",
            in_reply_to_tweet_id="222",
            in_reply_to_username="fallacy_user",
        )

        fallacy_text, original_text = fetch_tweet_chain(mention)

        # Should still return fallacy text, just no context
        assert fallacy_text == "This is a stupid argument!"
        assert original_text is None

    @patch("app.rss_client.fetch_tweet_data")
    def test_handles_fallacy_not_a_reply(self, mock_fetch_tweet):
        """Test handling when fallacy tweet is not a reply to anything."""
        fallacy_tweet = TweetData(
            tweet_id="222",
            text="This is a standalone tweet!",
            author_username="fallacy_user",
            in_reply_to_tweet_id=None,
            in_reply_to_username=None,
        )

        mock_fetch_tweet.return_value = fallacy_tweet

        mention = RSSMention(
            tweet_id="333",
            text="@FallacySheriff fallacyme",
            author_username="tagger",
            published="2025-01-01",
            link="https://twitter.com/tagger/status/333",
            in_reply_to_tweet_id="222",
            in_reply_to_username="fallacy_user",
        )

        fallacy_text, original_text = fetch_tweet_chain(mention)

        # Fallacy text available, no context
        assert fallacy_text == "This is a standalone tweet!"
        assert original_text is None
