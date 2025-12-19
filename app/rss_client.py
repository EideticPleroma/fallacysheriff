"""
RSS client for fetching Twitter/X data via RSSHub.
Bypasses X API read restrictions by using RSSHub RSS feeds.
"""

import logging
import re
import urllib.request
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

import feedparser

from app.config import get_settings

# Timeout for RSS requests (seconds)
RSS_REQUEST_TIMEOUT = 15

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


def _extract_reply_info_from_entry(entry: dict) -> tuple[str | None, str | None, str | None]:
    """
    Extract in_reply_to tweet ID, username, and text from RSS entry.
    
    Looks for reply information in:
    1. Entry content/summary (may contain quoted reply link and text)
    2. Entry metadata
    
    RSSHub often embeds the replied-to tweet content in the entry HTML.
    
    Returns:
        (in_reply_to_tweet_id, in_reply_to_username, in_reply_to_text)
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
    
    tweet_id = None
    username = None
    reply_text = None
    
    if reply_match:
        username = reply_match.group(2)
        tweet_id = reply_match.group(3)
    
    # Try to find "Replying to @username" text pattern
    reply_to_match = re.search(r"Replying to @(\w+)", content, re.IGNORECASE)
    if reply_to_match and not username:
        # We have username but not tweet ID - partial info
        username = reply_to_match.group(1)
    
    # Extract the replied-to tweet text if it's embedded in the RSS entry
    # RSSHub sometimes includes quoted tweet content in blockquotes or similar
    # Look for content between "Replying to" and the mention text
    if content:
        # Try to extract text from between markers that indicate reply content
        # This handles cases where the reply-to tweet text is embedded
        blockquote_match = re.search(
            r"(?:Replying to @\w+.*?)?\n+([^<]*(?:<[^>]+>[^<]*)*?)(?:\n|$)",
            content,
            re.IGNORECASE
        )
        if blockquote_match:
            potential_text = blockquote_match.group(1)
            # Clean up the extracted text
            potential_text = re.sub(r"<[^>]+>", " ", potential_text)
            potential_text = unescape(potential_text)
            potential_text = " ".join(potential_text.split())
            if potential_text and len(potential_text) > 10:
                reply_text = potential_text.strip()
    
    return tweet_id, username, reply_text


def fetch_mentions_rss() -> list[RSSMention]:
    """
    Fetch mentions of the bot via RSSHub RSS feed.
    
    Uses the /twitter/keyword route to search for mentions of the bot.
    RSSHub includes reply context in the RSS entries.
    
    Returns:
        List of RSSMention objects for tweets mentioning the bot
    """
    settings = get_settings()
    
    # RSSHub route for keyword search
    # Use simple route without routeParams to avoid URL encoding issues
    url = _build_rsshub_url(f"/twitter/keyword/@{settings.bot_username}")
    
    logger.info(f"Fetching mentions from RSSHub: {url}")
    
    try:
        # Use urllib with timeout to prevent hanging indefinitely
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'FallacySheriff/1.0')
        
        with urllib.request.urlopen(request, timeout=RSS_REQUEST_TIMEOUT) as response:
            status_code = response.getcode()
            content_type = response.headers.get('Content-Type', 'unknown')
            feed_content = response.read()
            
            logger.info(
                f"RSSHub response: status={status_code}, "
                f"content_type={content_type}, "
                f"content_length={len(feed_content)} bytes"
            )
            
            # Log first 500 chars of response for debugging
            content_preview = feed_content[:500].decode('utf-8', errors='replace')
            logger.debug(f"Response preview: {content_preview}")
        
        feed = feedparser.parse(feed_content)
        
        if feed.bozo:
            logger.error(f"RSS feed parse error: {feed.bozo_exception}")
            # Log the actual content that failed to parse
            logger.error(f"Failed content preview: {feed_content[:1000].decode('utf-8', errors='replace')}")
            return []
        
        logger.info(f"Parsed feed: {len(feed.entries)} entries, feed title: {feed.feed.get('title', 'N/A')}")
        
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
            
            # Extract reply-to information (includes text if embedded in RSS)
            reply_to_id, reply_to_username, reply_to_text = _extract_reply_info_from_entry(entry)
            
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
        
    except urllib.error.HTTPError as e:
        # HTTP errors (4xx, 5xx) - log the response body for debugging
        error_body = e.read().decode('utf-8', errors='replace')[:1000]
        logger.error(
            f"RSS fetch HTTP error: {e.code} {e.reason}\n"
            f"URL: {url}\n"
            f"Response body: {error_body}"
        )
        return []
    except urllib.error.URLError as e:
        logger.error(f"RSS fetch failed (URL error): {e.reason}\nURL: {url}")
        return []
    except TimeoutError:
        logger.error(f"RSS fetch timed out after {RSS_REQUEST_TIMEOUT}s\nURL: {url}")
        return []
    except Exception as e:
        logger.error(f"Error fetching RSS mentions: {e}\nURL: {url}", exc_info=True)
        return []


def fetch_tweet_chain(mention: RSSMention) -> tuple[str | None, str | None]:
    """
    Extract tweet chain context from RSS entry for analysis.
    
    Given a mention (user tagging @FallacySheriff), extracts:
    1. The fallacy tweet (parent of mention) - what to analyze
    2. The original tweet (grandparent of mention) - context
    
    Since RSSHub doesn't provide a route to fetch individual tweets by ID,
    we extract context that's already embedded in the RSS entry.
    
    Args:
        mention: The RSSMention that triggered the bot
        
    Returns:
        (fallacy_tweet_text, original_tweet_text)
        - fallacy_tweet_text: The text of the tweet being replied to
        - original_tweet_text: None (not available from RSS entry alone)
    """
    # The RSS entry from RSSHub keyword search includes reply context
    # The mention object contains the in_reply_to information extracted from the entry
    
    if not mention.in_reply_to_tweet_id or not mention.in_reply_to_username:
        logger.warning(
            f"Mention {mention.tweet_id} missing reply-to info, "
            "cannot get fallacy tweet context"
        )
        return None, None
    
    logger.info(
        f"Using context for fallacy tweet: {mention.in_reply_to_tweet_id} "
        f"by @{mention.in_reply_to_username}"
    )
    
    # We don't have access to the parent tweet's full content via RSSHub,
    # but we use whatever context was extracted from the RSS entry
    # The mention.text contains the user's reply text, which references the fallacy
    
    # Return the mention text (user's reply) as the context for analysis
    # This includes the fallacy they're responding to
    fallacy_context = mention.text
    
    if not fallacy_context:
        logger.warning(
            f"No text content for mention {mention.tweet_id}"
        )
        return None, None
    
    logger.info(
        f"Extracted fallacy context ({len(fallacy_context)} chars) from mention"
    )
    
    # Original tweet context is not available via RSSHub keyword route
    return fallacy_context, None

