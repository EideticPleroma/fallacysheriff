# Testing Guide

FallacySheriff includes a comprehensive test suite using pytest.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py         # Shared fixtures
├── test_polling.py     # Polling and endpoint tests
├── test_grok.py        # Grok API client tests
└── test_database.py    # SQLite database tests
```

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest tests/test_polling.py
pytest tests/test_grok.py
pytest tests/test_database.py
```

### Specific Test Function

```bash
pytest tests/test_polling.py::TestProcessMention::test_process_valid_mention
```

### Tests Matching Pattern

```bash
pytest -k "polling"
pytest -k "duplicate"
pytest -k "grok"
```

### Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

## Code Coverage

### Generate Coverage Report

```bash
pytest --cov=app --cov-report=html
```

This creates an `htmlcov/` directory. Open `htmlcov/index.html` in a browser to view the report.

### Coverage in Terminal

```bash
pytest --cov=app --cov-report=term-missing
```

### Coverage Thresholds

To enforce minimum coverage:

```bash
pytest --cov=app --cov-fail-under=80
```

## Test Categories

### Polling Tests (`test_polling.py`)

Tests for polling functionality and HTTP endpoints:

| Test | Description |
|------|-------------|
| `test_health_returns_ok` | Health check endpoint |
| `test_status_returns_info` | Status endpoint returns bot info |
| `test_trigger_poll_completes` | Manual poll trigger works |
| `test_get_mentions_returns_list` | Mentions API returns list |
| `test_get_mentions_with_since_id` | since_id passed to API |
| `test_process_valid_mention` | Full processing flow |
| `test_process_skips_no_trigger` | Skips without trigger |
| `test_process_skips_non_reply` | Skips non-replies |
| `test_process_skips_duplicate` | Skips duplicates |
| `test_poll_updates_last_seen_id` | Updates tracking ID |

### Grok Tests (`test_grok.py`)

Tests for Grok API integration:

| Test | Description |
|------|-------------|
| `test_analyze_fallacy_returns_valid_response` | Returns Grok response |
| `test_response_under_280_chars` | Truncates long responses |
| `test_hostile_tone_includes_roast` | Sarcasm for hostile tweets |
| `test_neutral_tone_no_roast` | Educational for neutral tweets |
| `test_grok_api_error_handling` | Graceful error handling |
| `test_system_prompt_content` | System prompt validation |
| `test_correct_api_call_parameters` | Correct API parameters |

### Database Tests (`test_database.py`)

Tests for SQLite operations:

| Test | Description |
|------|-------------|
| `test_init_creates_processed_tweets_table` | Creates tweet tracking table |
| `test_init_creates_poll_state_table` | Creates poll state table |
| `test_init_creates_parent_directory` | Creates directories |
| `test_init_idempotent` | Safe to call multiple times |
| `test_is_processed_returns_false_for_new` | New tweets return False |
| `test_is_processed_returns_true_after_mark` | Marked tweets return True |
| `test_get_last_seen_id_returns_none_initially` | No initial state |
| `test_set_and_get_last_seen_id` | State persistence works |

## Fixtures

Fixtures are defined in `conftest.py`:

### `test_settings`

Provides test configuration:

```python
@pytest.fixture
def test_settings():
    return Settings(
        twitter_consumer_key="test_consumer_key",
        bot_user_id="123456789",
        poll_interval_minutes=5,
        database_path=":memory:",
        # ... other test values
    )
```

### `test_db`

Provides a temporary SQLite database:

```python
@pytest.fixture
def test_db(test_settings, tmp_path):
    db_path = str(tmp_path / "test_tweets.db")
    init_db(db_path)
    return db_path
```

### `mock_twitter_client`

Provides a mocked Tweepy client:

```python
@pytest.fixture
def mock_twitter_client():
    mock_client = MagicMock()
    mock_client.get_users_mentions.return_value = ...
    mock_client.get_tweet.return_value = ...
    mock_client.create_tweet.return_value = ...
    return mock_client
```

### `mock_grok_client`

Provides a mocked OpenAI client:

```python
@pytest.fixture
def mock_grok_client():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = ...
    return mock_client
```

### Sample Mentions

```python
@pytest.fixture
def sample_mention():
    return {
        "id": "1234567890",
        "text": "@FallacySheriff fallacyme",
        "author_id": "111222333",
        "in_reply_to_tweet_id": "9876543210",
        "parent_tweet_text": "Everyone knows AI is bad!",
    }
```

## Writing New Tests

### Test Structure

```python
class TestFeatureName:
    """Tests for feature description."""

    def test_specific_behavior(self, fixture1, fixture2):
        """Test that specific behavior works correctly."""
        # Arrange
        input_data = ...

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result == expected_value
```

### Async Tests

Use `pytest.mark.asyncio` for async functions:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

### Mocking External Services

Always mock external API calls:

```python
from unittest.mock import patch, MagicMock

@patch("app.main.get_mentions")
def test_with_mock(mock_get_mentions, client):
    mock_get_mentions.return_value = []
    
    response = client.post("/poll")
    
    assert response.status_code == 200
    mock_get_mentions.assert_called_once()
```

## CI/CD Integration

### GitHub Actions

Add `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml
```

## Troubleshooting

### Tests Failing with Import Errors

Ensure you're in the project root and virtual environment is activated:

```bash
cd fallacysheriff
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Async Test Issues

Ensure `pytest-asyncio` is installed and mode is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Mock Not Working

Ensure you're patching at the correct location:

```python
# If main.py imports: from app.twitter_client import get_mentions
# Patch where it's USED, not where it's DEFINED:
@patch("app.main.get_mentions")  # Correct
@patch("app.twitter_client.get_mentions")  # May not work
```
