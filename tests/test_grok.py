"""
Tests for Grok API client.

Tests fallacy analysis with mocked OpenAI-compatible API.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.grok_client import analyze_fallacy, SYSTEM_PROMPT


class TestAnalyzeFallacy:
    """Tests for the analyze_fallacy function."""

    def test_analyze_fallacy_returns_valid_response(self, mock_grok_client):
        """Test that analyze_fallacy returns the Grok response."""
        result = analyze_fallacy(
            "Everyone knows this is true!",
            client=mock_grok_client
        )

        assert "Bandwagon" in result
        assert "yourlogicalfallacyis.com" in result
        mock_grok_client.chat.completions.create.assert_called_once()

    def test_analyze_with_context(self, mock_grok_client):
        """Test that context tweet is included in the prompt."""
        result = analyze_fallacy(
            fallacy_tweet="That's completely wrong!",
            context_tweet="Here is my original statement about AI",
            client=mock_grok_client
        )

        call_kwargs = mock_grok_client.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        assert "ORIGINAL TWEET" in user_content
        assert "Here is my original statement about AI" in user_content
        assert "REPLY TO ANALYZE" in user_content
        assert "That's completely wrong!" in user_content

    def test_analyze_without_context(self, mock_grok_client):
        """Test analysis without context tweet."""
        result = analyze_fallacy(
            fallacy_tweet="Everyone knows this is true!",
            context_tweet=None,
            client=mock_grok_client
        )

        call_kwargs = mock_grok_client.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        # Should not include context sections
        assert "ORIGINAL TWEET" not in user_content
        assert "Everyone knows this is true!" in user_content

    def test_response_under_280_chars(self, mock_grok_client):
        """Test that response is truncated to 280 characters if needed."""
        # Create a response that's too long
        long_response = "A" * 300
        mock_grok_client.chat.completions.create.return_value.choices[0].message.content = long_response

        result = analyze_fallacy("Test tweet", client=mock_grok_client)

        assert len(result) <= 280
        assert result.endswith("...")

    def test_hostile_tone_includes_roast(self, mock_grok_client):
        """Test that hostile tweets get a sarcastic response."""
        # Configure mock to return a sarcastic response
        mock_response = (
            "Hyperbole\n"
            "Pro: Concerns are valid.\n"
            "Con: The claim is exaggerated.\n"
            "Ah yes, quite the dramatic interpretation.\n"
            "More: yourlogicalfallacyis.com/appeal-to-emotion"
        )
        mock_grok_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy(
            "AI is LITERALLY DESTROYING EVERYTHING!!!",
            client=mock_grok_client
        )

        # The response should contain sarcasm indicators
        assert "Ah yes" in result or "quite" in result.lower()

    def test_neutral_tone_no_roast(self, mock_grok_client):
        """Test that neutral tweets get educational response."""
        # Configure mock to return an educational response
        mock_response = (
            "Not a fallacy - genuine question!\n"
            "Pro: Good to ask questions.\n"
            "Con: No error to correct here.\n"
            "More: yourlogicalfallacyis.com"
        )
        mock_grok_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy(
            "Is AI really that energy intensive?",
            client=mock_grok_client
        )

        # Check that we got an educational response
        assert "genuine question" in result.lower() or "good" in result.lower()

    def test_grok_api_error_handling(self):
        """Test graceful handling of API errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        result = analyze_fallacy("Test tweet", client=mock_client)

        # Should return fallback response
        assert "Unable to analyze" in result
        assert "yourlogicalfallacyis.com" in result

    def test_system_prompt_content(self):
        """Test that system prompt contains required elements."""
        assert "FallacySheriff" in SYSTEM_PROMPT
        assert "280" in SYSTEM_PROMPT
        assert "hostile" in SYSTEM_PROMPT.lower()
        assert "neutral" in SYSTEM_PROMPT.lower()
        assert "yourlogicalfallacyis.com" in SYSTEM_PROMPT
        # New: should mention context/original tweet
        assert "ORIGINAL" in SYSTEM_PROMPT or "context" in SYSTEM_PROMPT.lower()

    def test_correct_api_call_parameters(self, mock_grok_client):
        """Test that the API is called with correct parameters."""
        analyze_fallacy("Test tweet", client=mock_grok_client)

        call_kwargs = mock_grok_client.chat.completions.create.call_args.kwargs
        assert "grok" in call_kwargs["model"].lower()
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert "Test tweet" in call_kwargs["messages"][1]["content"]


class TestAnalyzeFallacyWithContext:
    """Additional tests for context-aware analysis."""

    def test_context_helps_identify_strawman(self, mock_grok_client):
        """Test that context enables detection of strawman fallacies."""
        # Configure mock for strawman detection
        mock_response = (
            "Strawman\n"
            "Pro: Engaging with the topic.\n"
            "Con: Misrepresents the original argument.\n"
            "More: yourlogicalfallacyis.com/strawman"
        )
        mock_grok_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy(
            fallacy_tweet="So you're saying we should just ignore all safety!",
            context_tweet="We should balance AI development speed with safety measures",
            client=mock_grok_client
        )

        assert "Strawman" in result

    def test_context_provided_in_correct_format(self, mock_grok_client):
        """Test that context is formatted correctly for the model."""
        analyze_fallacy(
            fallacy_tweet="Reply text here",
            context_tweet="Original text here",
            client=mock_grok_client
        )

        call_kwargs = mock_grok_client.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        # Context should come before the reply in the message
        context_pos = user_content.find("Original text here")
        reply_pos = user_content.find("Reply text here")
        assert context_pos < reply_pos, "Context should appear before reply in prompt"
