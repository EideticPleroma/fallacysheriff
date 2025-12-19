# FallacySheriff

A Twitter bot that identifies logical fallacies in tweets. Reply to any tweet with `@FallacySheriff fallacyme` and the bot will analyze the parent tweet for logical fallacies, providing a balanced critique with a touch of dry British humor.

## How It Works

```
User A: "Everyone knows AI is destroying the planet!!!"

User B: "@FallacySheriff fallacyme"
         (replying to User A's tweet)

FallacySheriff: "Bandwagon + Hyperbole
                Pro: AI energy use is a valid concern.
                Con: 'Everyone knows' isn't evidence.
                More: yourlogicalfallacyis.com/bandwagon"
```

## Features

- Polls for mentions every 5 minutes (configurable)
- Detects the primary logical fallacy in tweets
- Provides balanced pro/con analysis
- Adds dry humor for hostile tweets, educational tone for genuine questions
- Never attacks the person, only the argument
- Links to educational resources

## Requirements

- Python 3.11+
- Grok API access from x.ai
- RSSHub instance (self-hosted or public, for Twitter/X data via RSS)

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/fallacysheriff.git
cd fallacysheriff
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required credentials:
- Grok API key from [console.x.ai](https://console.x.ai)
- RSSHub URL and optional access key (if using private RSSHub instance)
- Twitter/X authentication token for RSSHub (to access Twitter mentions)

### 3. Run Locally

```bash
uvicorn app.main:app --reload
```

The bot will start polling for mentions automatically.

### 4. Run Tests

```bash
pytest -v
```

### 5. Deploy to Railway

```bash
# Push to GitHub, then:
railway login
railway init
railway up
```

See [docs/deployment.md](docs/deployment.md) for detailed instructions.

## Project Structure

```
fallacysheriff/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app with polling scheduler
│   ├── config.py         # Environment configuration
│   ├── database.py       # SQLite for tracking and state
│   ├── grok_client.py    # Grok API integration
│   ├── rss_client.py     # RSSHub RSS feed integration
│   └── twitter_client.py # X/Twitter client (legacy)
├── tests/
│   ├── conftest.py       # Test fixtures
│   ├── test_polling.py   # Polling and endpoint tests
│   ├── test_grok.py
│   ├── test_rss.py       # RSS parsing tests
│   └── test_database.py
├── docs/
│   ├── setup.md          # Setup guide
│   ├── deployment.md     # Railway deployment
│   ├── api-reference.md  # Endpoint docs
│   └── testing.md        # Testing guide
├── data/                 # SQLite database directory
├── .env.example
├── requirements.txt
├── railway.toml
└── Procfile
```

## Documentation

- [Setup Guide](docs/setup.md) - Prerequisites and local setup
- [Deployment Guide](docs/deployment.md) - Deploy to Railway
- [API Reference](docs/api-reference.md) - Endpoint documentation
- [Testing Guide](docs/testing.md) - Running and writing tests

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Bot status and polling info |
| `/poll` | POST | Manually trigger a poll |

## Architecture

The bot uses a **RSS-based polling architecture**:

1. APScheduler runs in the background
2. Every 5 minutes, it fetches mentions via RSSHub's `/twitter/keyword` RSS feed
3. RSSHub converts Twitter/X mentions to RSS, providing context without API limits
4. Mentions with the trigger phrase are processed
5. Tweet chain context is extracted from RSS entry content
6. Parent tweet text is analyzed using Grok
7. Replies are posted

This approach **bypasses X API read restrictions** by using RSSHub as a universal RSS converter, eliminating the need for expensive API tiers.

## Tech Stack

- **FastAPI** - Web framework
- **APScheduler** - Background polling
- **feedparser** - RSS feed parsing
- **RSSHub** - Universal RSS converter for Twitter/X
- **OpenAI SDK** - Grok API (OpenAI-compatible)
- **SQLite** - State tracking and deduplication
- **Railway** - Deployment platform

## Cost

| Service | Monthly Cost |
|---------|--------------|
| X API | Free (RSS-based, no API tier needed) |
| Railway hosting | Free |
| RSSHub hosting | Free (self-hosted) or varies (paid) |
| Grok API | ~$0-10 (usage-based) |
| **Total** | ~$0-10/month |

**Note**: By using RSSHub instead of X's paid API tiers, FallacySheriff eliminates the $200/month X API cost.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Your Logical Fallacy Is](https://yourlogicalfallacyis.com/) - Fallacy reference
- [Grok](https://x.ai/) - AI analysis
- [RSSHub](https://docs.rsshub.app/) - Universal RSS converter
- [Railway](https://railway.app/) - Hosting
