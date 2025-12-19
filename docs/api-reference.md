# API Reference

FallacySheriff exposes HTTP endpoints for health monitoring and manual control.

## Base URL

- Local: `http://localhost:8000`
- Production: `https://your-app.up.railway.app`

## Endpoints

### Health Check

Check if the service is running.

```
GET /health
```

#### Response

```json
{
  "status": "ok"
}
```

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Service is healthy |

#### Example

```bash
curl https://your-app.up.railway.app/health
```

---

### Bot Status

Get detailed bot status including polling information.

```
GET /status
```

#### Response

```json
{
  "status": "running",
  "poll_interval_minutes": 5,
  "last_poll_time": "2024-01-15T10:30:00.123456+00:00",
  "mentions_processed": 42,
  "last_seen_id": "1234567890123456789"
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Scheduler status: "running" or "stopped" |
| `poll_interval_minutes` | integer | Minutes between polls |
| `last_poll_time` | string/null | ISO timestamp of last poll |
| `mentions_processed` | integer | Total mentions processed since startup |
| `last_seen_id` | string/null | Most recent tweet ID processed |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Status retrieved successfully |

#### Example

```bash
curl https://your-app.up.railway.app/status
```

---

### Trigger Poll

Manually trigger a poll for mentions. Useful for testing or catching up after downtime.

```
POST /poll
```

#### Response

```json
{
  "status": "poll_completed"
}
```

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Poll completed |

#### Example

```bash
curl -X POST https://your-app.up.railway.app/poll
```

---

## Background Polling

The bot automatically polls for mentions using APScheduler. This is not an HTTP endpoint but runs in the background.

### Polling Flow

1. Scheduler triggers every `POLL_INTERVAL_MINUTES`
2. Bot fetches RSS feed from RSSHub via `/twitter/keyword/@bot_username`
3. Each mention is parsed from the RSS feed
4. Mention text is checked for trigger phrase (`fallacyme`)
5. Mentions are verified as replies to other tweets
6. Matching mentions trigger fallacy analysis
7. Replies are posted to triggering tweets
8. Processed mentions are marked in database to avoid duplicates

### Trigger Criteria

A mention is processed if ALL conditions are met:

1. RSS entry contains bot username (from RSSHub keyword search)
2. Tweet contains `fallacyme` trigger phrase (case-insensitive)
3. Tweet is a reply to another tweet (extracted from RSS entry)
4. Tweet hasn't been processed before (checked in SQLite)

---

## Internal Functions

These are internal Python functions, documented for developers.

### RSS Client Functions

Located in `app/rss_client.py`:

```python
def fetch_mentions_rss() -> list[RSSMention]:
    """
    Fetch mentions of the bot via RSSHub RSS feed.
    
    Uses the /twitter/keyword route to search for mentions of the bot.
    RSSHub includes reply context in the RSS entries.
    
    Returns:
        List of RSSMention objects for tweets mentioning the bot
    """

def fetch_tweet_chain(mention: RSSMention) -> tuple[str | None, str | None]:
    """
    Extract tweet chain context from RSS entry for analysis.
    
    Given a mention (user tagging @FallacySheriff), extracts context
    that's embedded in the RSS entry.
    
    Args:
        mention: The RSSMention that triggered the bot
        
    Returns:
        (fallacy_tweet_text, original_tweet_text)
        - fallacy_tweet_text: The text of the tweet being replied to
        - original_tweet_text: None (not available from RSS entry alone)
    """
```

### RSSMention Dataclass

```python
@dataclass
class RSSMention:
    """Represents a mention of the bot found in RSS feed."""
    tweet_id: str                         # ID of the mention tweet
    text: str                             # Text of the mention tweet
    author_username: str                  # Who posted the mention
    published: str                        # Publication timestamp
    link: str                             # Link to the mention tweet
    in_reply_to_tweet_id: str | None      # ID of parent tweet
    in_reply_to_username: str | None      # Author of parent tweet
```

### Database Functions

Located in `app/database.py`:

```python
def init_db(db_path: str | None = None) -> None:
    """Initialize database and create tables."""

def is_processed(tweet_id: str, db_path: str | None = None) -> bool:
    """Check if a tweet has been processed."""

def mark_processed(tweet_id: str, db_path: str | None = None) -> None:
    """Mark a tweet as processed."""

def get_last_seen_id(db_path: str | None = None) -> str | None:
    """Get the last seen tweet ID for polling."""

def set_last_seen_id(tweet_id: str, db_path: str | None = None) -> None:
    """Set the last seen tweet ID for polling."""
```

### Grok Functions

Located in `app/grok_client.py`:

```python
def analyze_fallacy(tweet_text: str, context: str | None = None) -> str:
    """Analyze tweet for logical fallacies using Grok."""
```

---

## Rate Limits

### RSSHub

- No hard rate limits for RSS feeds
- Public RSSHub instances may have soft rate limiting
- Self-hosted RSSHub on Railway has no practical limits for this use case

### Grok API

- Check [console.x.ai](https://console.x.ai) for current limits
- Typically generous for low-volume bots
- Usage-based pricing

### Bot Self-Limiting

- Duplicate tweets blocked via SQLite deduplication
- Failed requests logged but not retried
- All tweets marked processed to prevent spam
- Polling interval prevents excessive requests

---

## Error Handling

### HTTP Errors

| Code | Meaning |
|------|---------|
| 200 | Success |
| 500 | Internal server error |

### Common RSS Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | RSSHub not reachable | Check `RSSHUB_URL` and RSSHub service status |
| "not well-formed" | Invalid RSS returned | Check RSSHub auth token validity |
| "No mentions fetched" | No matching tweets found | Verify trigger phrase in mentions |

### Logging

All operations are logged:

```
INFO: Polling for new mentions...
INFO: Fetching mentions from RSSHub: http://rsshub.railway.internal:1200/twitter/keyword/@FallacySheriff
INFO: Fetched 3 mentions from RSS
INFO: Processing mention 1234567890, analyzing tweet 9876543210
INFO: Analyzing parent tweet: This is clearly wrong...
INFO: Successfully replied to tweet 1234567890
INFO: Updated last_seen_id to 1234567890
```

View logs in Railway dashboard or local terminal.

---

## Configuration

### Environment Variables

#### X API (for Posting Replies)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TWITTER_CONSUMER_KEY` | Yes | - | API Key from X Developer Portal |
| `TWITTER_CONSUMER_SECRET` | Yes | - | API Secret from X Developer Portal |
| `TWITTER_ACCESS_TOKEN` | Yes | - | Access Token from X Developer Portal |
| `TWITTER_ACCESS_TOKEN_SECRET` | Yes | - | Access Token Secret from X Developer Portal |
| `TWITTER_BEARER_TOKEN` | Yes | - | Bearer Token from X Developer Portal |

#### RSSHub (for Reading Mentions)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RSSHUB_URL` | Yes | - | URL of RSSHub instance |
| `RSSHUB_ACCESS_KEY` | No | - | Optional access key for RSSHub |
| `TWITTER_AUTH_TOKEN` | Yes* | - | Twitter auth token (cookie) for RSSHub |

#### Bot Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_USERNAME` | Yes | - | Bot's Twitter username |
| `GROK_API_KEY` | Yes | - | Grok API key from x.ai |
| `POLL_INTERVAL_MINUTES` | No | 5 | Poll interval in minutes |
| `DATABASE_PATH` | No | data/tweets.db | SQLite database path |

*Or use `TWITTER_USERNAME`/`TWITTER_PASSWORD` for RSSHub authentication

---

## Examples

### Fetch Mentions and Analyze

```python
from app.rss_client import fetch_mentions_rss, fetch_tweet_chain
from app.grok_client import analyze_fallacy

# Get recent mentions
mentions = fetch_mentions_rss()

for mention in mentions:
    # Extract tweet chain context
    fallacy_context, _ = fetch_tweet_chain(mention)
    
    if fallacy_context:
        # Analyze the tweet
        analysis = analyze_fallacy(fallacy_context)
        print(f"Tweet by {mention.author_username}: {analysis}")
```

### Manual Poll Trigger

```bash
# Trigger immediate poll
curl -X POST http://localhost:8000/poll

# Check current status
curl http://localhost:8000/status
```

### Monitor Bot Health

```bash
# Create a monitoring script
while true; do
  status=$(curl -s http://localhost:8000/status)
  echo "$(date): $status"
  sleep 60
done
```
