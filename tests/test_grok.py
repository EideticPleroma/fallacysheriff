"""
Tests for Grok API client.

Tests fallacy analysis with mocked OpenAI-compatible API.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.grok_client import analyze_fallacy, FallacyAnalysis, SYSTEM_PROMPT, _parse_analysis_response


class TestFallacyAnalysis:
    """Tests for the FallacyAnalysis dataclass."""

    def test_fallacy_analysis_creation(self):
        """Test creating a FallacyAnalysis object."""
        analysis = FallacyAnalysis(
            reply_text="Test reply",
            confidence=95,
            fallacy_detected=True,
            fallacy_name="Strawman"
        )

        assert analysis.reply_text == "Test reply"
        assert analysis.confidence == 95
        assert analysis.fallacy_detected is True
        assert analysis.fallacy_name == "Strawman"


class TestParseAnalysisResponse:
    """Tests for the _parse_analysis_response function."""

    def test_parses_valid_json(self):
        """Test parsing a valid JSON response."""
        response = json.dumps({
            "confidence": 95,
            "fallacy_detected": True,
            "fallacy_name": "Bandwagon",
            "reply": "Bandwagon Fallacy\\nPro: Popular opinion matters.\\nCon: Popularity doesn't equal truth."
        })

        result = _parse_analysis_response(response)

        assert result.confidence == 95
        assert result.fallacy_detected is True
        assert result.fallacy_name == "Bandwagon"
        assert "Bandwagon Fallacy" in result.reply_text

    def test_handles_newline_escapes(self):
        """Test that \\n is converted to actual newlines."""
        response = json.dumps({
            "confidence": 90,
            "fallacy_detected": True,
            "fallacy_name": "Test",
            "reply": "Line 1\\nLine 2\\nLine 3"
        })

        result = _parse_analysis_response(response)

        assert "\n" in result.reply_text
        assert "\\n" not in result.reply_text

    def test_truncates_long_reply(self):
        """Test that replies over 280 chars are truncated."""
        long_reply = "A" * 300
        response = json.dumps({
            "confidence": 80,
            "fallacy_detected": True,
            "fallacy_name": "Test",
            "reply": long_reply
        })

        result = _parse_analysis_response(response)

        assert len(result.reply_text) <= 280
        assert result.reply_text.endswith("...")

    def test_fallback_parsing_for_invalid_json(self):
        """Test fallback parsing when JSON is invalid."""
        invalid_response = '"confidence": 75, "fallacy_detected": true, "fallacy_name": "Test"'

        result = _parse_analysis_response(invalid_response)

        assert result.confidence == 75
        assert result.fallacy_detected is True
        assert result.fallacy_name == "Test"


class TestAnalyzeFallacy:
    """Tests for the analyze_fallacy function."""

    def test_analyze_fallacy_returns_fallacy_analysis(self, mock_grok_client_json):
        """Test that analyze_fallacy returns a FallacyAnalysis object."""
        result = analyze_fallacy(
            "Everyone knows this is true!",
            client=mock_grok_client_json
        )

        assert isinstance(result, FallacyAnalysis)
        assert result.confidence == 95
        assert result.fallacy_detected is True
        assert "Bandwagon" in result.fallacy_name
        mock_grok_client_json.chat.completions.create.assert_called_once()

    def test_analyze_with_context(self, mock_grok_client_json):
        """Test that context tweet is included in the prompt."""
        result = analyze_fallacy(
            fallacy_tweet="That's completely wrong!",
            context_tweet="Here is my original statement about AI",
            client=mock_grok_client_json
        )

        call_kwargs = mock_grok_client_json.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        assert "ORIGINAL TWEET" in user_content
        assert "Here is my original statement about AI" in user_content
        assert "REPLY TO ANALYZE" in user_content
        assert "That's completely wrong!" in user_content

    def test_analyze_without_context(self, mock_grok_client_json):
        """Test analysis without context tweet."""
        result = analyze_fallacy(
            fallacy_tweet="Everyone knows this is true!",
            context_tweet=None,
            client=mock_grok_client_json
        )

        call_kwargs = mock_grok_client_json.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        # Should not include context sections
        assert "ORIGINAL TWEET" not in user_content
        assert "Everyone knows this is true!" in user_content

    def test_high_confidence_fallacy(self, mock_grok_client_json):
        """Test detection of high-confidence fallacy."""
        result = analyze_fallacy(
            "AI is LITERALLY DESTROYING EVERYTHING!!!",
            client=mock_grok_client_json
        )

        assert result.confidence >= 90
        assert result.fallacy_detected is True

    def test_low_confidence_no_fallacy(self):
        """Test that genuine questions get low confidence."""
        mock_client = MagicMock()
        mock_response = json.dumps({
            "confidence": 10,
            "fallacy_detected": False,
            "fallacy_name": None,
            "reply": "Not a fallacy - genuine question!"
        })
        mock_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy(
            "Is AI really that energy intensive?",
            client=mock_client
        )

        assert result.confidence < 50
        assert result.fallacy_detected is False

    def test_grok_api_error_handling(self):
        """Test graceful handling of API errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        result = analyze_fallacy("Test tweet", client=mock_client)

        # Should return fallback with 0 confidence
        assert result.confidence == 0
        assert result.fallacy_detected is False
        assert "Unable to analyze" in result.reply_text

    def test_system_prompt_content(self):
        """Test that system prompt contains required elements."""
        assert "FallacySheriff" in SYSTEM_PROMPT
        assert "280" in SYSTEM_PROMPT
        assert "hostile" in SYSTEM_PROMPT.lower()
        assert "neutral" in SYSTEM_PROMPT.lower()
        assert "yourlogicalfallacyis.com" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT.lower()
        assert "JSON" in SYSTEM_PROMPT

    def test_correct_api_call_parameters(self, mock_grok_client_json):
        """Test that the API is called with correct parameters."""
        analyze_fallacy("Test tweet", client=mock_grok_client_json)

        call_kwargs = mock_grok_client_json.chat.completions.create.call_args.kwargs
        assert "grok" in call_kwargs["model"].lower()
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert "Test tweet" in call_kwargs["messages"][1]["content"]


class TestConfidenceThreshold:
    """Tests for confidence-based filtering."""

    def test_confidence_range(self):
        """Test that confidence is always 0-100."""
        mock_client = MagicMock()

        # Test with various confidence values
        for conf in [0, 50, 100]:
            mock_response = json.dumps({
                "confidence": conf,
                "fallacy_detected": conf > 50,
                "fallacy_name": "Test" if conf > 50 else None,
                "reply": "Test reply"
            })
            mock_client.chat.completions.create.return_value.choices[0].message.content = mock_response

            result = analyze_fallacy("Test", client=mock_client)

            assert 0 <= result.confidence <= 100

    def test_borderline_confidence(self):
        """Test analysis with borderline confidence (around threshold)."""
        mock_client = MagicMock()
        mock_response = json.dumps({
            "confidence": 85,
            "fallacy_detected": True,
            "fallacy_name": "Possible Fallacy",
            "reply": "Might be a fallacy, might not be."
        })
        mock_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy("Arguable statement", client=mock_client)

        assert result.confidence == 85
        # 85 is below default 90 threshold, so this would NOT be posted


class TestAnalyzeFallacyWithContext:
    """Additional tests for context-aware analysis."""

    def test_context_helps_identify_strawman(self):
        """Test that context enables detection of strawman fallacies."""
        mock_client = MagicMock()
        mock_response = json.dumps({
            "confidence": 92,
            "fallacy_detected": True,
            "fallacy_name": "Strawman",
            "reply": "Strawman\\nPro: Engaging with the topic.\\nCon: Misrepresents the original argument."
        })
        mock_client.chat.completions.create.return_value.choices[0].message.content = mock_response

        result = analyze_fallacy(
            fallacy_tweet="So you're saying we should just ignore all safety!",
            context_tweet="We should balance AI development speed with safety measures",
            client=mock_client
        )

        assert result.fallacy_name == "Strawman"
        assert result.confidence >= 90

    def test_context_provided_in_correct_format(self, mock_grok_client_json):
        """Test that context is formatted correctly for the model."""
        analyze_fallacy(
            fallacy_tweet="Reply text here",
            context_tweet="Original text here",
            client=mock_grok_client_json
        )

        call_kwargs = mock_grok_client_json.chat.completions.create.call_args.kwargs
        user_content = call_kwargs["messages"][1]["content"]

        # Context should come before the reply in the message
        context_pos = user_content.find("Original text here")
        reply_pos = user_content.find("Reply text here")
        assert context_pos < reply_pos, "Context should appear before reply in prompt"
