# Setup Guide

This guide walks you through setting up FallacySheriff from scratch.

## Prerequisites

- Python 3.11 or higher
- X/Twitter Developer account with Free tier (for posting replies)
- A Grok API key from x.ai
- RSSHub instance (self-hosted or using a public instance)
- Twitter/X authentication token for RSSHub (for reading mentions)

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

## 2. X/Twitter API Setup (for Posting Replies)

The bot needs X API credentials to post replies. The **Free tier** is sufficient.

### Create a Developer Account

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Sign in with your bot's X account
3. Apply for developer access if you haven't already

### Create a Project and App

1. Go to the [Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new Project (e.g., "FallacySheriff")
3. Create an App within the project

### Configure App Permissions

1. Go to your App settings
2. Under "User authentication settings", click "Set up"
3. Configure:
   - App permissions: **Read and write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://example.com/callback` (placeholder)
   - Website URL: Your website or GitHub repo

### Generate Keys and Tokens

1. Go to "Keys and tokens" tab
2. Generate and save:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token**
   - **Access Token Secret**
   - **Bearer Token**

## 3. Grok API Setup

1. Go to [console.x.ai](https://console.x.ai)
2. Sign in with your X account
3. Create an API key
4. Save the API key for environment variables

## 4. Twitter/X Authentication for RSSHub (for Reading Mentions)

RSSHub needs Twitter authentication to fetch mentions. This is separate from the API keys above. You have two options:

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

## 5. Local Environment Setup

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
# X/Twitter API Credentials (for posting replies)
# Get these from https://developer.twitter.com/en/portal/dashboard
TWITTER_CONSUMER_KEY=your_api_key_here
TWITTER_CONSUMER_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here

# RSSHub Configuration (for reading mentions)
RSSHUB_URL=http://localhost:1200  # or https://your-rsshub-instance.com
RSSHUB_ACCESS_KEY=  # Optional, if your RSSHub instance requires an access key

# Twitter Authentication for RSSHub (choose one method)
# Method 1: Auth Token (recommended)
TWITTER_AUTH_TOKEN=your_auth_token_from_cookies

# Method 2: Username and Password
# TWITTER_USERNAME=your_username
# TWITTER_PASSWORD=your_password
# TWITTER_AUTHENTICATION_SECRET=your_2fa_secret

# Bot Configuration
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
| **X API (Posting)** | | |
| `TWITTER_CONSUMER_KEY` | Yes | API Key from X Developer Portal |
| `TWITTER_CONSUMER_SECRET` | Yes | API Secret from X Developer Portal |
| `TWITTER_ACCESS_TOKEN` | Yes | Access Token from X Developer Portal |
| `TWITTER_ACCESS_TOKEN_SECRET` | Yes | Access Token Secret from X Developer Portal |
| `TWITTER_BEARER_TOKEN` | Yes | Bearer Token from X Developer Portal |
| **RSSHub (Reading)** | | |
| `RSSHUB_URL` | Yes | URL of your RSSHub instance |
| `RSSHUB_ACCESS_KEY` | No | Access key if RSSHub requires authentication |
| `TWITTER_AUTH_TOKEN` | Yes* | Twitter auth token (cookie-based) for RSSHub |
| `TWITTER_USERNAME` | Yes* | Twitter username (if not using auth token) |
| `TWITTER_PASSWORD` | Yes* | Twitter password (if not using auth token) |
| `TWITTER_AUTHENTICATION_SECRET` | No | 2FA secret (if using username/password and 2FA enabled) |
| **Bot Config** | | |
| `BOT_USERNAME` | Yes | Bot's Twitter username |
| `GROK_API_KEY` | Yes | Grok API key from x.ai |
| `POLL_INTERVAL_MINUTES` | No | Poll interval in minutes (default: 5) |
| `DATABASE_PATH` | No | Path to SQLite database (default: data/tweets.db) |

*Use either auth token OR username/password for RSSHub

## 6. Run Locally

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

## 7. Verify Setup

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

## 8. Why This Architecture?

FallacySheriff uses a **hybrid approach**:

### Reading Mentions (RSSHub)
- **Free**: No X API tier required for reading
- **No Rate Limits**: RSS feeds are more efficient than API polling
- **Rich Context**: RSS entries include tweet content and reply context

### Posting Replies (X API Free Tier)
- **Free Tier Works**: The X API Free tier allows posting tweets/replies
- **Official API**: Reliable and supported method for posting
- **Simple Auth**: Standard OAuth tokens from Developer Portal

This hybrid approach avoids the $200/month X API Basic tier while still being able to post replies.

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
