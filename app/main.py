"""
FastAPI application for the FallacySheriff Twitter bot.

Uses RSSHub for reading mentions (bypasses X API read limits).
Uses X API only for posting replies.

Endpoints:
- GET /health: Health check for Railway deployment
- GET /status: Bot status and last poll time
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.config import get_settings
from app.database import (
    init_db,
    is_processed,
    mark_processed,
    get_last_seen_id,
    set_last_seen_id,
)
from app.grok_client import analyze_fallacy
from app.rss_client import fetch_mentions_rss, fetch_tweet_chain, RSSMention
from app.twitter_client import post_reply

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Bot configuration
TRIGGER_PHRASE = "fallacyme"

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None

# Track last poll time for status endpoint
last_poll_time: datetime | None = None
mentions_processed_count: int = 0


async def poll_mentions() -> None:
    """
    Poll for new mentions via RSS and process them.

    This function is called by the scheduler every few minutes.
    It fetches mentions from RSSHub, filters for trigger phrases,
    and processes matching tweets.
    """
    global last_poll_time, mentions_processed_count

    logger.info("Polling for new mentions via RSS...")
    last_poll_time = datetime.now(timezone.utc)

    # Get the last seen tweet ID for filtering
    since_id = get_last_seen_id()

    # Fetch mentions from RSSHub
    mentions = fetch_mentions_rss()

    if not mentions:
        logger.debug("No mentions found in RSS feed")
        return

    # Track the newest tweet ID for next poll
    newest_id = None

    for mention in mentions:
        tweet_id = mention.tweet_id

        # Skip if we've seen this tweet before (older than since_id)
        if since_id and int(tweet_id) <= int(since_id):
            logger.debug(f"Tweet {tweet_id} is older than since_id, skipping")
            continue

        # Update newest_id
        if newest_id is None or int(tweet_id) > int(newest_id):
            newest_id = tweet_id

        # Process the mention
        await process_mention(mention)

    # Update the last seen ID for next poll
    if newest_id:
        set_last_seen_id(newest_id)
        logger.info(f"Updated last_seen_id to {newest_id}")


async def process_mention(mention: RSSMention) -> None:
    """
    Process a single mention from RSS.

    Checks if the mention:
    1. Contains "fallacyme" trigger phrase
    2. Is a reply to another tweet (has in_reply_to info)
    3. Hasn't been processed before

    If all conditions are met, fetches the tweet chain (fallacy tweet + original),
    analyzes for fallacies, and posts a reply.
    """
    global mentions_processed_count

    tweet_id = mention.tweet_id
    tweet_text = mention.text.lower()

    # Check for trigger phrase
    if TRIGGER_PHRASE not in tweet_text:
        logger.debug(f"Tweet {tweet_id} doesn't contain trigger phrase, skipping")
        return

    # Must be a reply to another tweet
    if not mention.in_reply_to_tweet_id:
        logger.info(f"Tweet {tweet_id} is not a reply, skipping")
        return

    # Check for duplicates
    if is_processed(tweet_id):
        logger.debug(f"Tweet {tweet_id} already processed, skipping")
        return

    logger.info(
        f"Processing mention {tweet_id}, "
        f"replying to {mention.in_reply_to_tweet_id}"
    )

    # Fetch the two-level tweet chain via RSS
    # - fallacy_text: the tweet with the fallacy (parent of mention)
    # - original_text: context tweet (grandparent of mention)
    fallacy_text, original_text = fetch_tweet_chain(mention)

    if not fallacy_text:
        logger.error(f"Could not fetch fallacy tweet for mention {tweet_id}")
        mark_processed(tweet_id)  # Mark to avoid retrying
        return

    # Analyze for fallacies using Grok (with context if available)
    logger.info(
        f"Analyzing fallacy tweet: {fallacy_text[:100]}... "
        f"(context available: {bool(original_text)})"
    )
    analysis = analyze_fallacy(fallacy_text, context_tweet=original_text)

    # Get confidence threshold from settings
    settings = get_settings()
    threshold = settings.confidence_threshold

    # Log the analysis result
    logger.info(
        f"Analysis result: confidence={analysis.confidence}%, "
        f"fallacy_detected={analysis.fallacy_detected}, "
        f"fallacy_name={analysis.fallacy_name}"
    )

    # Only post if confidence meets threshold
    if analysis.confidence < threshold:
        logger.info(
            f"Confidence {analysis.confidence}% below threshold {threshold}%, "
            f"not posting reply for tweet {tweet_id}"
        )
        mark_processed(tweet_id)
        return

    # Post the reply to the mention tweet
    success = post_reply(tweet_id, analysis.reply_text)

    if success:
        logger.info(f"Successfully replied to tweet {tweet_id}")
        mentions_processed_count += 1
    else:
        logger.error(f"Failed to reply to tweet {tweet_id}")

    # Mark as processed regardless of success to avoid spam
    mark_processed(tweet_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize database and start scheduler."""
    global scheduler

    logger.info("Initializing database...")
    init_db()

    # Get polling interval from settings
    settings = get_settings()
    interval_minutes = settings.poll_interval_minutes

    # Create and start the scheduler
    logger.info(f"Starting scheduler with {interval_minutes} minute interval...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_mentions,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="poll_mentions",
        name="Poll for mentions via RSS",
        replace_existing=True,
    )
    scheduler.start()

    # Run initial poll on startup
    logger.info("Running initial poll...")
    await poll_mentions()

    logger.info("FallacySheriff bot started (RSS mode)")
    yield

    # Shutdown
    logger.info("Shutting down scheduler...")
    if scheduler:
        scheduler.shutdown(wait=False)
    logger.info("FallacySheriff bot stopped")


app = FastAPI(
    title="FallacySheriff Bot",
    description="Twitter bot that identifies logical fallacies in tweets (RSS-based)",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Railway."""
    return {"status": "ok"}


@app.get("/status")
async def bot_status() -> dict:
    """
    Get bot status information.

    Returns polling status, last poll time, and processing stats.
    """
    settings = get_settings()

    return {
        "status": "running" if scheduler and scheduler.running else "stopped",
        "mode": "rss",
        "rsshub_url": settings.rsshub_url,
        "poll_interval_minutes": settings.poll_interval_minutes,
        "last_poll_time": last_poll_time.isoformat() if last_poll_time else None,
        "mentions_processed": mentions_processed_count,
        "last_seen_id": get_last_seen_id(),
    }


@app.post("/poll")
async def trigger_poll() -> dict[str, str]:
    """
    Manually trigger a poll for mentions.

    Useful for testing or catching up after downtime.
    """
    await poll_mentions()
    return {"status": "poll_completed"}


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
