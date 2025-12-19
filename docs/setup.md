# Setup Guide

This guide walks you through setting up FallacySheriff from scratch.

## Prerequisites

- Python 3.11 or higher
- An X (Twitter) Developer account with **Basic** tier ($200/month)
- A Grok API key from x.ai

## 1. X Developer Account Setup

### Create a Developer Account

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Sign in with your X account
3. Apply for developer access if you haven't already

### Subscribe to Basic Tier

FallacySheriff uses polling to check for mentions, which requires the Basic tier:

- **Cost**: $200/month
- **Includes**: 15K tweet reads/month, adequate for polling every 5 minutes

To upgrade:
1. Go to [Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Navigate to your project settings
3. Upgrade to Basic tier

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

### Find Your Bot's User ID

You need your bot account's numeric User ID for polling mentions:

**Option 1: Use the API**
```bash
curl "https://api.twitter.com/2/users/by/username/FallacySheriff" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

**Option 2: Use a web tool**
- Go to [tweeterid.com](https://tweeterid.com)
- Enter your bot's username

Save this User ID - you'll need it for `BOT_USER_ID` in your environment.

## 2. Grok API Setup

1. Go to [console.x.ai](https://console.x.ai)
2. Sign in with your X account
3. Create an API key
4. Save the API key for environment variables

## 3. Local Environment Setup

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
TWITTER_CONSUMER_KEY=your_api_key_here
TWITTER_CONSUMER_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
BOT_USER_ID=your_bot_numeric_id_here
GROK_API_KEY=your_grok_api_key_here
POLL_INTERVAL_MINUTES=5
DATABASE_PATH=data/tweets.db
```

## 4. Run Locally

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

## 5. Verify Setup

### Test Health Endpoint

```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### Run Tests

```bash
pytest -v
```

All tests should pass if your environment is configured correctly.

## Rate Limit Considerations

With Basic tier ($200/month) and 5-minute polling:

| Metric | Value |
|--------|-------|
| Polls per day | 288 |
| Tweet reads per poll | ~2 (mentions + parent) |
| Monthly reads | ~17,000 |
| Basic tier limit | 15,000 |

**Recommendation**: Use 10-minute intervals (`POLL_INTERVAL_MINUTES=10`) to stay safely under limits, or monitor usage and adjust as needed.

## Next Steps

- [Deployment Guide](deployment.md) - Deploy to Railway
- [Testing Guide](testing.md) - Run and write tests
- [API Reference](api-reference.md) - Endpoint documentation
