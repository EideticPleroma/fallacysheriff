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
2. Bot fetches mentions since `last_seen_id`
3. Each mention is checked for trigger phrase
4. Matching mentions trigger fallacy analysis
5. Replies are posted to triggering tweets
6. `last_seen_id` is updated

### Trigger Criteria

A mention is processed if ALL conditions are met:

1. Tweet mentions `@FallacySheriff` (included in mentions API)
2. Tweet contains `fallacyme` trigger phrase (case-insensitive)
3. Tweet is a reply to another tweet
4. Tweet hasn't been processed before (checked in SQLite)

---

## Internal Functions

These are internal Python functions, documented for developers.

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

### Twitter Functions

Located in `app/twitter_client.py`:

```python
def get_mentions(since_id: str | None = None, client: tweepy.Client | None = None) -> list[dict]:
    """Fetch recent mentions of the bot account."""

def get_tweet_text(tweet_id: str, client: tweepy.Client | None = None) -> str | None:
    """Fetch tweet text by ID."""

def post_reply(reply_to_tweet_id: str, text: str, client: tweepy.Client | None = None) -> bool:
    """Post a reply to a tweet."""
```

### Grok Functions

Located in `app/grok_client.py`:

```python
def analyze_fallacy(tweet_text: str, client: OpenAI | None = None) -> str:
    """Analyze tweet for logical fallacies."""
```

---

## Rate Limits

### X API (Basic Tier)

| Operation | Limit |
|-----------|-------|
| Read tweets | 15,000/month |
| Write tweets | Included in tier |
| Mentions endpoint | Part of read quota |

### Grok API

- Check [console.x.ai](https://console.x.ai) for current limits
- Typically generous for low-volume bots

### Bot Self-Limiting

- Duplicate tweets blocked via SQLite
- Failed requests logged but not retried
- All tweets marked processed to prevent spam

---

## Error Handling

### HTTP Errors

| Code | Meaning |
|------|---------|
| 200 | Success |
| 500 | Internal server error |

### Logging

All operations are logged:

```
INFO: Polling for new mentions...
INFO: Fetched 3 new mentions
INFO: Processing mention 1234567890, analyzing tweet 9876543210
INFO: Analyzing parent tweet: This is clearly wrong...
INFO: Successfully replied to tweet 1234567890
INFO: Updated last_seen_id to 1234567890
```

View logs in Railway dashboard or local terminal.
