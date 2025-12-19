# Deployment Guide

Deploy FallacySheriff to Railway for 24/7 operation.

## Prerequisites

- Completed [Setup Guide](setup.md)
- GitHub account with repository
- Railway account (free tier works for hosting)
- X/Twitter API credentials (Free tier - for posting replies)
- RSSHub instance (self-hosted or public - for reading mentions)

## Cost Summary

| Service | Cost |
|---------|------|
| X API (Free tier) | Free (for posting replies) |
| FallacySheriff bot hosting | Free tier (500 hours/month) |
| RSSHub hosting (self-hosted on Railway) | Free tier (included) |
| Grok API | Usage-based (typically low) |
| **Total** | Free to ~$10/month |

**Note**: RSSHub handles reading mentions (free), while the X API Free tier handles posting replies. This avoids the $200/month X API Basic tier.

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
git commit -m "Deploy FallacySheriff"
git push origin main
```

## 2. Deploy RSSHub (if self-hosting)

### Create RSSHub Service on Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Select "Deploy from GitHub repo"
4. Search for `DIYgod/RSSHub` and deploy it
5. Configure environment variables:

| Variable | Value |
|----------|-------|
| `TWITTER_AUTH_TOKEN` | Your Twitter auth token from browser cookies |
| Or: `TWITTER_USERNAME` | Your Twitter username |
| Or: `TWITTER_PASSWORD` | Your Twitter password |
| Or: `TWITTER_AUTHENTICATION_SECRET` | Your 2FA secret (if enabled) |

### Note the RSSHub URL

After deployment, Railway will provide a URL like:
```
https://rsshub-xxxx.railway.app
```

Save this URL for the next step.

## 3. Deploy FallacySheriff Bot

### Create New Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `fallacysheriff` repository
5. Railway will auto-detect Python and start building

### Configure Environment Variables

In Railway dashboard:

1. Click on your service
2. Go to "Variables" tab
3. Add each variable:

#### X API Credentials (for posting replies)

| Variable | Value |
|----------|-------|
| `TWITTER_CONSUMER_KEY` | Your API Key |
| `TWITTER_CONSUMER_SECRET` | Your API Secret |
| `TWITTER_ACCESS_TOKEN` | Your Access Token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Your Access Token Secret |
| `TWITTER_BEARER_TOKEN` | Your Bearer Token |

#### RSSHub Configuration (for reading mentions)

| Variable | Value |
|----------|-------|
| `RSSHUB_URL` | `http://rsshub.railway.internal:1200` |
| `RSSHUB_ACCESS_KEY` | (leave empty unless you have a custom key) |
| `TWITTER_AUTH_TOKEN` | Your Twitter auth token (from browser cookies) |

#### Bot Configuration

| Variable | Value |
|----------|-------|
| `BOT_USERNAME` | `FallacySheriff` (or your bot's username) |
| `GROK_API_KEY` | Your Grok API Key |
| `POLL_INTERVAL_MINUTES` | `5` or `10` |
| `DATABASE_PATH` | `/app/data/tweets.db` |

**Important**: Use `http://rsshub.railway.internal:1200` for internal Railway networking. This connects to your RSSHub service running on the same Railway project.

### Configure Persistent Storage

SQLite needs persistent storage to survive deploys:

1. Go to your service settings
2. Click "Volumes"
3. Add a volume:
   - Mount path: `/app/data`
   - Size: 1GB (plenty for tweet IDs)

## 4. Link RSSHub and FallacySheriff Services

If both services are in the same project, Railway automatically connects them via internal networking:

- RSSHub service exposes: `http://rsshub.railway.internal:1200`
- FallacySheriff connects via this internal URL
- No external network calls needed between services

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
1. Click on your FallacySheriff service
2. Go to "Deployments" tab
3. Click on the latest deployment
4. View logs

You should see:
```
INFO: Initializing database...
INFO: Starting scheduler with 5 minute interval...
INFO: Running initial poll...
INFO: Fetching mentions from RSSHub: http://rsshub.railway.internal:1200/twitter/keyword/@FallacySheriff
INFO: FallacySheriff bot started
INFO: Uvicorn running on http://0.0.0.0:PORT
```

### Check RSSHub Logs

Also check RSSHub service logs to ensure it's running:
1. Click on RSSHub service
2. Go to "Deployments" tab
3. Look for RSSHub startup messages

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

# Set X API variables (for posting)
railway variables set TWITTER_CONSUMER_KEY=your_api_key
railway variables set TWITTER_CONSUMER_SECRET=your_api_secret
railway variables set TWITTER_ACCESS_TOKEN=your_access_token
railway variables set TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
railway variables set TWITTER_BEARER_TOKEN=your_bearer_token

# Set RSSHub variables (for reading)
railway variables set RSSHUB_URL=http://rsshub.railway.internal:1200
railway variables set TWITTER_AUTH_TOKEN=your_auth_token

# Set bot config
railway variables set BOT_USERNAME=FallacySheriff
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
2. Verify `BOT_USERNAME` is correct
3. Check RSSHub logs for connection issues
4. Ensure mentions are actually being posted to Twitter

### "Connection refused" Error

RSSHub service not responding:
1. Verify RSSHub service is running (check its logs)
2. Check that `RSSHUB_URL` uses correct internal URL: `http://rsshub.railway.internal:1200`
3. Ensure both services are in the same Railway project

### RSS Feed Parse Error

1. Check RSSHub logs for authentication issues
2. Verify `TWITTER_AUTH_TOKEN` is valid and not expired
3. Try manually fetching from RSSHub endpoint
4. Renew auth token if it expires

### Mentions Not Being Found

1. Check that mentions are being posted (reply with bot mention to any tweet)
2. Verify `BOT_USERNAME` matches your actual bot account name
3. Check database volume is mounted correctly

### Database Errors

1. Ensure volume is mounted at `/app/data`
2. Check file permissions
3. Verify `DATABASE_PATH` environment variable is set
4. Check Railway logs for write permission errors

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
- Monitoring RSSHub availability
- Tracking Grok API costs
- Setting up notifications for failed polls

## Scaling Considerations

The RSS-based architecture is simple and efficient:
- Single instance handles all polling
- SQLite is sufficient for deduplication
- No webhook complexity
- RSSHub can be scaled independently if needed

For higher volume:
- Reduce poll interval (but watch for RSS feed updates)
- Use multiple bot accounts (separate deployments)
- Upgrade RSSHub to managed service if needed
- Monitor Grok API usage and costs
