# Setup Guide

This guide walks you through setting up FallacySheriff from scratch.

## Prerequisites

- Python 3.11 or higher
- A Grok API key from x.ai
- RSSHub instance (self-hosted or using a public instance)
- Twitter/X authentication token for RSSHub

## 1. RSSHub Setup

FallacySheriff uses RSSHub to fetch Twitter/X mentions via RSS feeds, eliminating the need for expensive X API tiers.

### Option A: Self-Host RSSHub on Railway (Recommended)

This is the simplest approach for production deployment:

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Select "Deploy from GitHub repo"
4. Search for `DIYgod/RSSHub` and deploy it
5. Configure these environment variables:
   - `TWITTER_AUTH_TOKEN`: Your Twitter auth token (from browser cookies)
   - Or: `TWITTER_USERNAME`, `TWITTER_PASSWORD`, `TWITTER_AUTHENTICATION_SECRET`
6. Note the RSSHub URL (e.g., `https://rsshub-xxxx.railway.app`)

### Option B: Use Public RSSHub Instance

You can use a public RSSHub instance like `https://rsshub.app` (note: may have rate limits).

### Option C: Self-Host RSSHub Locally

For development, you can run RSSHub locally:

```bash
# Using Docker
docker run -d \
  -p 1200:1200 \
  -e TWITTER_AUTH_TOKEN=your_token \
  diygod/rsshub

# RSSHub will be available at http://localhost:1200
```

## 2. Grok API Setup

1. Go to [console.x.ai](https://console.x.ai)
2. Sign in with your X account
3. Create an API key
4. Save the API key for environment variables

## 3. Twitter/X Authentication for RSSHub

RSSHub needs Twitter authentication to fetch mentions. You have two options:

### Option 1: Use Auth Token (Recommended)

1. Open Twitter/X in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Make any request to Twitter
5. Find a request and check cookies
6. Copy the `auth_token` cookie value
7. Set `TWITTER_AUTH_TOKEN` environment variable

### Option 2: Use Username and Password

If 2FA is enabled, you'll also need the `TWITTER_AUTHENTICATION_SECRET` (your 2FA secret).

1. Set `TWITTER_USERNAME=your_username`
2. Set `TWITTER_PASSWORD=your_password`
3. Set `TWITTER_AUTHENTICATION_SECRET=your_2fa_secret` (if 2FA enabled)

## 4. Local Environment Setup

### Clone the Repository

```bash
git clone https://github.com/yourusername/fallacysheriff.git
cd fallacysheriff
```

### Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
```

Fill in your `.env` file:

```bash
# RSSHub Configuration
RSSHUB_URL=http://localhost:1200  # or https://your-rsshub-instance.com
RSSHUB_ACCESS_KEY=  # Optional, if your RSSHub instance requires an access key

# Twitter Authentication for RSSHub (choose one method)
# Method 1: Auth Token (recommended)
TWITTER_AUTH_TOKEN=your_auth_token_from_cookies

# Method 2: Username and Password
# TWITTER_USERNAME=your_username
# TWITTER_PASSWORD=your_password
# TWITTER_AUTHENTICATION_SECRET=your_2fa_secret

# Bot Username (the account mentions should tag)
BOT_USERNAME=FallacySheriff

# Grok API
GROK_API_KEY=your_grok_api_key_here

# Polling Configuration
POLL_INTERVAL_MINUTES=5

# App Configuration
DATABASE_PATH=data/tweets.db
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `RSSHUB_URL` | Yes | URL of your RSSHub instance |
| `RSSHUB_ACCESS_KEY` | No | Access key if RSSHub requires authentication |
| `TWITTER_AUTH_TOKEN` | Yes* | Twitter auth token (cookie-based) |
| `TWITTER_USERNAME` | Yes* | Twitter username (if not using auth token) |
| `TWITTER_PASSWORD` | Yes* | Twitter password (if not using auth token) |
| `TWITTER_AUTHENTICATION_SECRET` | No | 2FA secret (if using username/password and 2FA enabled) |
| `BOT_USERNAME` | Yes | Bot's Twitter username |
| `GROK_API_KEY` | Yes | Grok API key from x.ai |
| `POLL_INTERVAL_MINUTES` | No | Poll interval in minutes (default: 5) |
| `DATABASE_PATH` | No | Path to SQLite database (default: data/tweets.db) |

*Use either auth token OR username/password

## 5. Run Locally

Start the bot:

```bash
uvicorn app.main:app --reload
```

The bot will:
1. Initialize the database
2. Start the background scheduler
3. Poll for mentions every 5 minutes (configurable)
4. Process any triggers and post replies

### Check Status

```bash
curl http://localhost:8000/status
```

### Trigger Manual Poll

```bash
curl -X POST http://localhost:8000/poll
```

## 6. Verify Setup

### Test Health Endpoint

```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### Test RSSHub Connection

```bash
# Test that RSSHub is accessible
curl "http://localhost:1200/twitter/keyword/@FallacySheriff"

# Should return XML/RSS feed content
```

### Run Tests

```bash
pytest -v
```

All tests should pass if your environment is configured correctly.

## 7. Why RSSHub?

RSSHub solves the Twitter/X API access problem:

- **No API Tier Cost**: RSSHub is free to self-host or use publicly
- **No Rate Limit Concerns**: RSS feeds are more efficient than polling API endpoints
- **Universal Converter**: Works with any platform that has web access to Twitter
- **Context in Feed**: RSS entries include rich context without additional API calls

## Troubleshooting

### "Connection refused" error

RSSHub is not running. Verify:
1. RSSHub service is running (`docker ps` if using Docker)
2. `RSSHUB_URL` in `.env` is correct
3. RSSHub is accessible from your network

### "RSS feed parse error: not well-formed"

RSSHub is not returning valid RSS. Check:
1. `TWITTER_AUTH_TOKEN` is valid and not expired
2. RSSHub logs for auth errors
3. Try manually fetching: `curl "http://rsshub-url/twitter/keyword/@botname"`

### "Mentions not being fetched"

1. Check that bot username is spelled correctly
2. Ensure mentions are actually being posted to Twitter
3. Check logs for polling activity

## Next Steps

- [Deployment Guide](deployment.md) - Deploy to Railway
- [Testing Guide](testing.md) - Run and write tests
- [API Reference](api-reference.md) - Endpoint documentation
