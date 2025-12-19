"""
RSS client for fetching Twitter/X data via RSSHub.
Bypasses X API read restrictions by using RSSHub RSS feeds.
"""

import logging
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

import feedparser

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RSSMention:
    """Represents a mention of the bot found in RSS feed."""
    tweet_id: str
    text: str
    author_username: str
    published: str
    link: str
    # Parent = the fallacy tweet (what user is tagging bot about)
    in_reply_to_tweet_id: str | None
    in_reply_to_username: str | None


@dataclass
class TweetData:
    """Represents tweet data fetched via RSS."""
    tweet_id: str
    text: str
    author_username: str
    in_reply_to_tweet_id: str | None
    in_reply_to_username: str | None


def _build_rsshub_url(path: str) -> str:
    """Build full RSSHub URL with optional access key."""
    settings = get_settings()
    url = urljoin(settings.rsshub_url, path)
    
    if settings.rsshub_access_key:
        separator = "&" if "?" in url else "?"
        url += f"{separator}key={settings.rsshub_access_key}"
    
    return url


def _extract_tweet_id_from_link(link: str) -> str | None:
    """
    Extract tweet ID from a Twitter/X URL.
    
    Handles formats like:
    - https://twitter.com/username/status/1234567890
    - https://x.com/username/status/1234567890
    """
    match = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", link)
    return match.group(1) if match else None


def _extract_username_from_link(link: str) -> str | None:
    """
    Extract username from a Twitter/X URL.
    
    Handles formats like:
    - https://twitter.com/username/status/1234567890
    - https://x.com/username/status/1234567890
    """
    match = re.search(r"(?:twitter\.com|x\.com)/(\w+)/status/", link)
    return match.group(1) if match else None


def _extract_text_from_entry(entry: dict) -> str:
    """
    Extract clean text content from an RSS entry.
    
    RSS entries may have content in 'summary', 'description', or 'content' fields.
    HTML entities need to be unescaped and HTML tags stripped.
    """
    # Try different content fields
    content = ""
    if hasattr(entry, "summary"):
        content = entry.summary
    elif hasattr(entry, "description"):
        content = entry.description
    elif hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    
    # Strip HTML tags (basic approach)
    content = re.sub(r"<[^>]+>", " ", content)
    # Unescape HTML entities
    content = unescape(content)
    # Normalize whitespace
    content = " ".join(content.split())
    
    return content.strip()


def _extract_reply_info_from_entry(entry: dict) -> tuple[str | None, str | None]:
    """
    Extract in_reply_to tweet ID and username from RSS entry.
    
    Looks for reply information in:
    1. Entry content/summary (may contain quoted reply link)
    2. Entry metadata
    
    Returns:
        (in_reply_to_tweet_id, in_reply_to_username)
    """
    # Try to find reply-to link in content
    content = ""
    if hasattr(entry, "summary"):
        content = entry.summary
    elif hasattr(entry, "description"):
        content = entry.description
    elif hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    
    # Look for "Replying to @username" pattern or quoted tweet links
    # RSSHub often includes the original tweet link in replies
    reply_match = re.search(
        r'href=["\']?(https?://(?:twitter\.com|x\.com)/(\w+)/status/(\d+))["\']?',
        content
    )
    
    if reply_match:
        username = reply_match.group(2)
        tweet_id = reply_match.group(3)
        return tweet_id, username
    
    # Try to find "Replying to @username" text pattern
    reply_to_match = re.search(r"Replying to @(\w+)", content, re.IGNORECASE)
    if reply_to_match:
        # We have username but not tweet ID - partial info
        return None, reply_to_match.group(1)
    
    return None, None


def fetch_mentions_rss() -> list[RSSMention]:
    """
    Fetch mentions of the bot via RSSHub RSS feed.
    
    Uses the /twitter/user/:username route to get the bot's timeline,
    then filters for mentions containing the trigger phrase.
    
    Returns:
        List of RSSMention objects for tweets mentioning the bot
    """
    settings = get_settings()
    
    # RSSHub route for user timeline (includes mentions when others tag the user)
    # We need to use a search or mentions route - using keyword search for @username
    url = _build_rsshub_url(f"/twitter/keyword/@{settings.bot_username}")
    
    logger.info(f"Fetching mentions from RSSHub: {url}")
    
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo:
            logger.error(f"RSS feed parse error: {feed.bozo_exception}")
            return []
        
        mentions = []
        for entry in feed.entries:
            # Extract tweet link and ID
            link = getattr(entry, "link", "")
            tweet_id = _extract_tweet_id_from_link(link)
            
            if not tweet_id:
                logger.debug(f"Could not extract tweet ID from: {link}")
                continue
            
            # Extract author username from link
            author_username = _extract_username_from_link(link)
            if not author_username:
                logger.debug(f"Could not extract username from: {link}")
                continue
            
            # Get tweet text
            text = _extract_text_from_entry(entry)
            
            # Extract reply-to information
            reply_to_id, reply_to_username = _extract_reply_info_from_entry(entry)
            
            mention = RSSMention(
                tweet_id=tweet_id,
                text=text,
                author_username=author_username,
                published=getattr(entry, "published", ""),
                link=link,
                in_reply_to_tweet_id=reply_to_id,
                in_reply_to_username=reply_to_username,
            )
            mentions.append(mention)
        
        logger.info(f"Fetched {len(mentions)} mentions from RSS")
        return mentions
        
    except Exception as e:
        logger.error(f"Error fetching RSS mentions: {e}")
        return []


def fetch_tweet_data(tweet_id: str, author_username: str) -> TweetData | None:
    """
    Fetch tweet data via RSSHub tweet status route.
    
    Uses /twitter/tweet/:username/status/:id to get tweet content
    and its reply-to information for chain traversal.
    
    Args:
        tweet_id: The tweet ID to fetch
        author_username: The username of the tweet author
        
    Returns:
        TweetData object, or None if fetch failed
    """
    url = _build_rsshub_url(f"/twitter/tweet/{author_username}/status/{tweet_id}")
    
    logger.debug(f"Fetching tweet data from RSSHub: {url}")
    
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo:
            logger.error(f"RSS feed parse error for tweet {tweet_id}: {feed.bozo_exception}")
            return None
        
        if not feed.entries:
            logger.warning(f"No entries found for tweet {tweet_id}")
            return None
        
        entry = feed.entries[0]
        text = _extract_text_from_entry(entry)
        reply_to_id, reply_to_username = _extract_reply_info_from_entry(entry)
        
        return TweetData(
            tweet_id=tweet_id,
            text=text,
            author_username=author_username,
            in_reply_to_tweet_id=reply_to_id,
            in_reply_to_username=reply_to_username,
        )
        
    except Exception as e:
        logger.error(f"Error fetching tweet {tweet_id}: {e}")
        return None


def fetch_tweet_chain(mention: RSSMention) -> tuple[str | None, str | None]:
    """
    Fetch the two-level tweet chain for analysis.
    
    Given a mention (user tagging @FallacySheriff), fetches:
    1. The fallacy tweet (parent of mention) - what to analyze
    2. The original tweet (grandparent of mention) - context
    
    Args:
        mention: The RSSMention that triggered the bot
        
    Returns:
        (fallacy_tweet_text, original_tweet_text)
        - fallacy_tweet_text: The tweet to analyze for fallacies
        - original_tweet_text: Context tweet (may be None if not a reply chain)
    """
    # Step 1: Fetch the fallacy tweet (parent of mention)
    if not mention.in_reply_to_tweet_id or not mention.in_reply_to_username:
        logger.warning(
            f"Mention {mention.tweet_id} missing reply-to info, "
            "cannot fetch fallacy tweet"
        )
        return None, None
    
    logger.info(
        f"Fetching fallacy tweet: {mention.in_reply_to_tweet_id} "
        f"by @{mention.in_reply_to_username}"
    )
    
    fallacy_tweet = fetch_tweet_data(
        mention.in_reply_to_tweet_id,
        mention.in_reply_to_username
    )
    
    if not fallacy_tweet:
        logger.error(
            f"Could not fetch fallacy tweet {mention.in_reply_to_tweet_id}"
        )
        return None, None
    
    # Step 2: Fetch the original tweet (grandparent of mention)
    original_text = None
    
    if fallacy_tweet.in_reply_to_tweet_id and fallacy_tweet.in_reply_to_username:
        logger.info(
            f"Fetching original tweet: {fallacy_tweet.in_reply_to_tweet_id} "
            f"by @{fallacy_tweet.in_reply_to_username}"
        )
        
        original_tweet = fetch_tweet_data(
            fallacy_tweet.in_reply_to_tweet_id,
            fallacy_tweet.in_reply_to_username
        )
        
        if original_tweet:
            original_text = original_tweet.text
        else:
            logger.warning(
                f"Could not fetch original tweet "
                f"{fallacy_tweet.in_reply_to_tweet_id}, proceeding without context"
            )
    else:
        logger.info(
            "Fallacy tweet is not a reply, no original context available"
        )
    
    return fallacy_tweet.text, original_text
