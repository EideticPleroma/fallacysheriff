# Deployment Guide

Deploy FallacySheriff to Railway for 24/7 operation.

## Prerequisites

- Completed [Setup Guide](setup.md)
- GitHub account with repository
- Railway account (free tier works for hosting)
- X Basic tier subscription ($200/month) for API access

## Cost Summary

| Service | Cost |
|---------|------|
| X API Basic tier | $200/month |
| Railway hosting | Free tier (500 hours/month) |
| Grok API | Usage-based (typically low) |
| **Total** | ~$200/month |

## 1. Prepare Repository

Ensure your repository has these files:

```
fallacysheriff/
├── app/
├── tests/
├── requirements.txt
├── railway.toml
├── Procfile
└── ...
```

Push to GitHub:

```bash
git add .
git commit -m "Initial FallacySheriff setup"
git push origin main
```

## 2. Railway Setup

### Create Account

1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub

### Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `fallacysheriff` repository
4. Railway will auto-detect Python and start building

## 3. Configure Environment Variables

In Railway dashboard:

1. Click on your service
2. Go to "Variables" tab
3. Add each variable:

| Variable | Value |
|----------|-------|
| `TWITTER_CONSUMER_KEY` | Your API Key |
| `TWITTER_CONSUMER_SECRET` | Your API Secret |
| `TWITTER_ACCESS_TOKEN` | Your Access Token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Your Access Token Secret |
| `TWITTER_BEARER_TOKEN` | Your Bearer Token |
| `BOT_USER_ID` | Your bot's numeric User ID |
| `GROK_API_KEY` | Your Grok API Key |
| `POLL_INTERVAL_MINUTES` | `5` or `10` |
| `DATABASE_PATH` | `/app/data/tweets.db` |

## 4. Configure Persistent Storage

SQLite needs persistent storage to survive deploys:

1. Go to your service settings
2. Click "Volumes"
3. Add a volume:
   - Mount path: `/app/data`
   - Size: 1GB (plenty for tweet IDs)

## 5. Verify Deployment

### Check Health

```bash
curl https://your-app.up.railway.app/health
# Should return: {"status":"ok"}
```

### Check Status

```bash
curl https://your-app.up.railway.app/status
```

Should return:
```json
{
  "status": "running",
  "poll_interval_minutes": 5,
  "last_poll_time": "2024-01-15T10:30:00+00:00",
  "mentions_processed": 0,
  "last_seen_id": null
}
```

### View Logs

In Railway dashboard:
1. Click on your service
2. Go to "Deployments" tab
3. Click on the latest deployment
4. View logs

You should see:
```
INFO: Initializing database...
INFO: Starting scheduler with 5 minute interval...
INFO: Running initial poll...
INFO: FallacySheriff bot started
INFO: Uvicorn running on http://0.0.0.0:PORT
```

## 6. Test the Bot

1. Find a tweet with a logical fallacy
2. Reply to it with: `@FallacySheriff fallacyme`
3. Wait up to 5 minutes (or your poll interval)
4. The bot should reply with fallacy analysis

You can also trigger an immediate poll:

```bash
curl -X POST https://your-app.up.railway.app/poll
```

## Railway CLI Alternative

For power users, Railway CLI offers command-line deployment:

```bash
# Install
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Set variables
railway variables set TWITTER_CONSUMER_KEY=your_key
railway variables set TWITTER_CONSUMER_SECRET=your_secret
railway variables set TWITTER_ACCESS_TOKEN=your_token
railway variables set TWITTER_ACCESS_TOKEN_SECRET=your_token_secret
railway variables set TWITTER_BEARER_TOKEN=your_bearer
railway variables set BOT_USER_ID=your_bot_id
railway variables set GROK_API_KEY=your_grok_key
railway variables set POLL_INTERVAL_MINUTES=5
railway variables set DATABASE_PATH=/app/data/tweets.db

# Deploy
railway up

# View logs
railway logs
```

## Troubleshooting

### Bot Not Responding to Mentions

1. Check Railway logs for polling activity
2. Verify `BOT_USER_ID` is correct
3. Ensure X API credentials are valid
4. Check that mentions API is returning data

### Rate Limit Errors

1. Increase `POLL_INTERVAL_MINUTES` (try 10 or 15)
2. Check X Developer Portal for usage stats
3. Consider upgrading X API tier if needed

### Database Errors

1. Ensure volume is mounted at `/app/data`
2. Check file permissions
3. Verify `DATABASE_PATH` environment variable

### Scheduler Not Running

1. Check logs for scheduler startup message
2. Verify APScheduler is in requirements.txt
3. Restart the service in Railway

## Monitoring

### Railway Metrics

Railway provides basic metrics:
- CPU usage
- Memory usage
- Request count

### Bot Status Endpoint

Use `/status` endpoint to monitor:
- Last poll time
- Mentions processed count
- Scheduler status

### Recommended Monitoring

For production use, consider:
- Setting up alerts for error logs
- Monitoring X API usage in Developer Portal
- Tracking Grok API costs

## Scaling Considerations

The polling architecture is simple and efficient:
- Single instance handles all polling
- SQLite is sufficient for deduplication
- No webhook complexity

For higher volume, consider:
- Reducing poll interval (watch rate limits)
- Multiple bot accounts (separate deployments)
- Upgrading to Pro tier for more API access
