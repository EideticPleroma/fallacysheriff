"""
Twitter/X API client using Tweepy.

Only used for posting replies - reading is handled by RSSHub
to bypass X API read rate limits.
"""

import logging

import tweepy

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_twitter_client() -> tweepy.Client:
    """Create and return a Tweepy v2 Client."""
    settings = get_settings()
    return tweepy.Client(
        bearer_token=settings.twitter_bearer_token,
        consumer_key=settings.twitter_consumer_key,
        consumer_secret=settings.twitter_consumer_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_token_secret,
        wait_on_rate_limit=True,
    )


def post_reply(reply_to_tweet_id: str, text: str, client: tweepy.Client | None = None) -> bool:
    """
    Post a reply to a tweet.

    Args:
        reply_to_tweet_id: The ID of the tweet to reply to
        text: The reply text (must be under 280 characters)
        client: Optional Tweepy client (for testing)

    Returns:
        True if successful, False otherwise
    """
    if client is None:
        client = get_twitter_client()

    if len(text) > 280:
        logger.error(f"Reply text too long: {len(text)} characters")
        return False

    try:
        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=reply_to_tweet_id,
        )

        if response.data:
            logger.info(f"Posted reply {response.data['id']} to tweet {reply_to_tweet_id}")
            return True

        logger.error("Failed to post reply: no response data")
        return False

    except tweepy.TweepyException as e:
        logger.error(f"Error posting reply to {reply_to_tweet_id}: {e}")
        return False
