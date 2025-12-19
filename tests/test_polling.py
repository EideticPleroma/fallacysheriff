"""
Tests for polling functionality and endpoints.

Tests the RSS-based mention polling, processing, and HTTP endpoints.
"""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.grok_client import FallacyAnalysis
from app.rss_client import RSSMention


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_ok(self, client):
        """Test that health check returns status ok."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStatusEndpoint:
    """Tests for GET /status endpoint."""

    @patch("app.main.get_last_seen_id")
    def test_status_returns_info(self, mock_get_last_seen, client):
        """Test that status endpoint returns bot information."""
        mock_get_last_seen.return_value = None

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mode" in data
        assert data["mode"] == "rss"
        assert "poll_interval_minutes" in data
        assert "mentions_processed" in data
        assert "rsshub_url" in data


class TestTriggerPoll:
    """Tests for POST /poll endpoint."""

    @patch("app.main.fetch_mentions_rss")
    def test_trigger_poll_completes(self, mock_fetch_mentions, client):
        """Test that manual poll trigger works."""
        mock_fetch_mentions.return_value = []

        response = client.post("/poll")

        assert response.status_code == 200
        assert response.json() == {"status": "poll_completed"}


class TestProcessMention:
    """Tests for the process_mention function."""

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_process_valid_mention_high_confidence(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test processing a valid mention with high confidence fallacy."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = ("Fallacy tweet text", "Original tweet context")
        mock_analyze_fallacy.return_value = FallacyAnalysis(
            reply_text="Bandwagon fallacy detected",
            confidence=95,
            fallacy_detected=True,
            fallacy_name="Bandwagon"
        )
        mock_post_reply.return_value = True

        await process_mention(sample_rss_mention)

        mock_fetch_chain.assert_called_once_with(sample_rss_mention)
        mock_analyze_fallacy.assert_called_once_with(
            "Fallacy tweet text",
            context_tweet="Original tweet context"
        )
        mock_post_reply.assert_called_once()
        mock_mark_processed.assert_called()

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_process_skips_low_confidence(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test that low confidence analysis doesn't post reply."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = ("Fallacy tweet text", "Original tweet context")
        mock_analyze_fallacy.return_value = FallacyAnalysis(
            reply_text="Maybe a fallacy?",
            confidence=75,  # Below 90% threshold
            fallacy_detected=True,
            fallacy_name="Possible Fallacy"
        )

        await process_mention(sample_rss_mention)

        mock_analyze_fallacy.assert_called_once()
        mock_post_reply.assert_not_called()  # Should NOT post
        mock_mark_processed.assert_called()  # But still mark processed

    @pytest.mark.asyncio
    @patch("app.main.post_reply")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.fetch_tweet_chain")
    async def test_process_skips_no_trigger(
        self,
        mock_fetch_chain,
        mock_analyze_fallacy,
        mock_post_reply,
        sample_rss_mention_no_trigger,
        test_settings,
    ):
        """Test that mentions without trigger phrase are skipped."""
        from app.main import process_mention

        await process_mention(sample_rss_mention_no_trigger)

        mock_fetch_chain.assert_not_called()
        mock_analyze_fallacy.assert_not_called()
        mock_post_reply.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.main.post_reply")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.fetch_tweet_chain")
    async def test_process_skips_non_reply(
        self,
        mock_fetch_chain,
        mock_analyze_fallacy,
        mock_post_reply,
        sample_rss_mention_not_reply,
        test_settings,
    ):
        """Test that mentions that aren't replies are skipped."""
        from app.main import process_mention

        await process_mention(sample_rss_mention_not_reply)

        mock_fetch_chain.assert_not_called()
        mock_analyze_fallacy.assert_not_called()
        mock_post_reply.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.main.post_reply")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.is_processed")
    async def test_process_skips_duplicate(
        self,
        mock_is_processed,
        mock_fetch_chain,
        mock_analyze_fallacy,
        mock_post_reply,
        sample_rss_mention,
        test_settings,
    ):
        """Test that already-processed mentions are skipped."""
        from app.main import process_mention

        mock_is_processed.return_value = True

        await process_mention(sample_rss_mention)

        mock_fetch_chain.assert_not_called()
        mock_analyze_fallacy.assert_not_called()
        mock_post_reply.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_process_handles_missing_chain(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test handling when tweet chain cannot be fetched."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = (None, None)

        await process_mention(sample_rss_mention)

        mock_analyze_fallacy.assert_not_called()
        mock_post_reply.assert_not_called()
        mock_mark_processed.assert_called()  # Should still mark processed

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_process_works_without_context(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test processing works when original context is not available."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = ("Fallacy tweet text", None)  # No context
        mock_analyze_fallacy.return_value = FallacyAnalysis(
            reply_text="Fallacy detected",
            confidence=92,
            fallacy_detected=True,
            fallacy_name="Test Fallacy"
        )
        mock_post_reply.return_value = True

        await process_mention(sample_rss_mention)

        mock_analyze_fallacy.assert_called_once_with(
            "Fallacy tweet text",
            context_tweet=None
        )
        mock_post_reply.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_confidence_at_threshold_posts(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test that exactly 90% confidence posts reply."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = ("Fallacy tweet text", "Context")
        mock_analyze_fallacy.return_value = FallacyAnalysis(
            reply_text="Borderline fallacy",
            confidence=90,  # Exactly at threshold
            fallacy_detected=True,
            fallacy_name="Test"
        )
        mock_post_reply.return_value = True

        await process_mention(sample_rss_mention)

        mock_post_reply.assert_called_once()  # Should post at exactly 90%

    @pytest.mark.asyncio
    @patch("app.main.fetch_tweet_chain")
    @patch("app.main.analyze_fallacy")
    @patch("app.main.post_reply")
    @patch("app.main.is_processed")
    @patch("app.main.mark_processed")
    async def test_confidence_just_below_threshold_skips(
        self,
        mock_mark_processed,
        mock_is_processed,
        mock_post_reply,
        mock_analyze_fallacy,
        mock_fetch_chain,
        sample_rss_mention,
        test_settings,
    ):
        """Test that 89% confidence does not post reply."""
        from app.main import process_mention

        mock_is_processed.return_value = False
        mock_fetch_chain.return_value = ("Fallacy tweet text", "Context")
        mock_analyze_fallacy.return_value = FallacyAnalysis(
            reply_text="Almost a fallacy",
            confidence=89,  # Just below threshold
            fallacy_detected=True,
            fallacy_name="Test"
        )

        await process_mention(sample_rss_mention)

        mock_post_reply.assert_not_called()  # Should NOT post at 89%


class TestPollMentions:
    """Tests for the poll_mentions function."""

    @pytest.mark.asyncio
    @patch("app.main.fetch_mentions_rss")
    @patch("app.main.get_last_seen_id")
    @patch("app.main.set_last_seen_id")
    @patch("app.main.process_mention", new_callable=AsyncMock)
    async def test_poll_updates_last_seen_id(
        self,
        mock_process,
        mock_set_last_seen,
        mock_get_last_seen,
        mock_fetch_mentions,
        test_settings,
    ):
        """Test that polling updates the last seen ID."""
        from app.main import poll_mentions

        mock_get_last_seen.return_value = None
        mock_fetch_mentions.return_value = [
            RSSMention(
                tweet_id="999",
                text="@FallacySheriff fallacyme",
                author_username="user1",
                published="2025-01-01",
                link="https://twitter.com/user1/status/999",
                in_reply_to_tweet_id="888",
                in_reply_to_username="target_user",
            ),
            RSSMention(
                tweet_id="998",
                text="@FallacySheriff fallacyme",
                author_username="user2",
                published="2025-01-01",
                link="https://twitter.com/user2/status/998",
                in_reply_to_tweet_id="887",
                in_reply_to_username="target_user2",
            ),
        ]

        await poll_mentions()

        # Should set last_seen_id to the newest tweet
        mock_set_last_seen.assert_called_once_with("999")

    @pytest.mark.asyncio
    @patch("app.main.fetch_mentions_rss")
    @patch("app.main.get_last_seen_id")
    @patch("app.main.set_last_seen_id")
    async def test_poll_no_mentions(
        self,
        mock_set_last_seen,
        mock_get_last_seen,
        mock_fetch_mentions,
        test_settings,
    ):
        """Test polling with no new mentions."""
        from app.main import poll_mentions

        mock_get_last_seen.return_value = "12345"
        mock_fetch_mentions.return_value = []

        await poll_mentions()

        # Should not update last_seen_id
        mock_set_last_seen.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.main.fetch_mentions_rss")
    @patch("app.main.get_last_seen_id")
    @patch("app.main.set_last_seen_id")
    @patch("app.main.process_mention", new_callable=AsyncMock)
    async def test_poll_skips_old_tweets(
        self,
        mock_process,
        mock_set_last_seen,
        mock_get_last_seen,
        mock_fetch_mentions,
        test_settings,
    ):
        """Test that tweets older than since_id are skipped."""
        from app.main import poll_mentions

        mock_get_last_seen.return_value = "500"  # Already seen up to ID 500
        mock_fetch_mentions.return_value = [
            RSSMention(
                tweet_id="600",  # Newer - should process
                text="@FallacySheriff fallacyme",
                author_username="user1",
                published="2025-01-01",
                link="https://twitter.com/user1/status/600",
                in_reply_to_tweet_id="888",
                in_reply_to_username="target_user",
            ),
            RSSMention(
                tweet_id="400",  # Older - should skip
                text="@FallacySheriff fallacyme",
                author_username="user2",
                published="2025-01-01",
                link="https://twitter.com/user2/status/400",
                in_reply_to_tweet_id="887",
                in_reply_to_username="target_user2",
            ),
        ]

        await poll_mentions()

        # Should only process the newer tweet
        assert mock_process.call_count == 1
        processed_mention = mock_process.call_args[0][0]
        assert processed_mention.tweet_id == "600"
