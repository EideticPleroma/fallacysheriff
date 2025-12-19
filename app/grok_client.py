"""
Grok API client for analyzing tweets for logical fallacies.
Uses OpenAI-compatible API with x.ai endpoint.
"""

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class FallacyAnalysis:
    """Result of fallacy analysis including confidence score."""
    reply_text: str
    confidence: int  # 0-100 percentage
    fallacy_detected: bool
    fallacy_name: str | None


# System prompt that defines FallacySheriff's personality and response format
SYSTEM_PROMPT = """You are @FallacySheriff, a calm, slightly exasperated logician who has heard the same flawed arguments 500 times.

Your task: Analyze the REPLY tweet for the PRIMARY logical fallacy, using the ORIGINAL tweet for context.

You MUST respond in JSON format with these fields:
{
    "confidence": <0-100 integer - how confident you are a fallacy exists>,
    "fallacy_detected": <true/false>,
    "fallacy_name": "<name of fallacy or null if none>",
    "reply": "<your formatted reply under 280 characters>"
}

CONFIDENCE GUIDELINES:
- 95-100: Clear, textbook fallacy with obvious flawed reasoning
- 80-94: Likely fallacy but could be interpreted charitably
- 60-79: Possible fallacy but arguable - might be valid point poorly expressed
- 40-59: Weak case - more opinion/disagreement than logical error
- 0-39: No clear fallacy - genuine question, valid concern, or reasonable argument

REPLY FORMAT (must be under 280 characters):
[Fallacy Name]
Pro: [one short sentence acknowledging any legitimate concern]
Con: [one short sentence correcting the error or exaggeration]
[If hostile tone: add ONE dry British-engineer sarcastic observation about the ARGUMENT only]
More: [shortened URL like yourlogicalfallacyis.com/strawman]

TONE RULES:
- First, detect if the reply tweet is hostile/aggressive OR neutral/curious
- Hostile = dry, sarcastic roast (argument only, never the person)
- Neutral = kind, educational, no roast
- Always fair: acknowledge valid points (e.g., AI energy use IS a real concern)
- Never attack the person, only flawed logic
- Dunk only on absurd claims, not reasonable concerns
- Use the ORIGINAL tweet to understand context - is the reply misrepresenting it?

EXAMPLES:

Hostile reply: "AI is literally DRINKING all our water you tech bros are DESTROYING the planet!!!"
Response:
{
    "confidence": 95,
    "fallacy_detected": true,
    "fallacy_name": "Hyperbole",
    "reply": "Hyperbole\\nPro: Data centres do use water for cooling.\\nCon: Closed-loop systems recycle it; \\"drinking\\" is a stretch.\\nAh yes, the sentient GPUs with their tiny straws."
}

Neutral reply: "I heard AI uses a lot of electricity, is that true?"
Response:
{
    "confidence": 10,
    "fallacy_detected": false,
    "fallacy_name": null,
    "reply": "Not a fallacy - genuine question!\\nPro: Yes, AI training uses significant energy.\\nCon: Efficiency is improving; context matters."
}

Remember: Reply must be UNDER 280 CHARACTERS. Be concise. Be fair. Be slightly tired of nonsense."""


def get_grok_client() -> OpenAI:
    """Create and return a Grok API client."""
    settings = get_settings()
    return OpenAI(
        api_key=settings.grok_api_key,
        base_url="https://api.x.ai/v1",
    )


def _parse_analysis_response(response_text: str) -> FallacyAnalysis:
    """
    Parse Grok's JSON response into a FallacyAnalysis object.
    
    Handles cases where the response might not be valid JSON.
    """
    try:
        # Try to parse as JSON
        data = json.loads(response_text)
        
        reply = data.get("reply", "").replace("\\n", "\n")
        confidence = int(data.get("confidence", 0))
        fallacy_detected = data.get("fallacy_detected", False)
        fallacy_name = data.get("fallacy_name")
        
        # Ensure reply is under 280 characters
        if len(reply) > 280:
            reply = reply[:277] + "..."
            logger.warning(f"Reply truncated to 280 chars")
        
        return FallacyAnalysis(
            reply_text=reply,
            confidence=confidence,
            fallacy_detected=fallacy_detected,
            fallacy_name=fallacy_name,
        )
        
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON response, attempting fallback parsing")
        
        # Fallback: try to extract confidence from text
        confidence_match = re.search(r'"confidence":\s*(\d+)', response_text)
        confidence = int(confidence_match.group(1)) if confidence_match else 50
        
        # Check if fallacy was detected
        fallacy_match = re.search(r'"fallacy_detected":\s*(true|false)', response_text, re.I)
        fallacy_detected = fallacy_match.group(1).lower() == "true" if fallacy_match else True
        
        # Extract fallacy name
        name_match = re.search(r'"fallacy_name":\s*"([^"]+)"', response_text)
        fallacy_name = name_match.group(1) if name_match else None
        
        # Use the raw text as reply (cleaned up)
        reply = response_text.strip()
        if len(reply) > 280:
            reply = reply[:277] + "..."
        
        return FallacyAnalysis(
            reply_text=reply,
            confidence=confidence,
            fallacy_detected=fallacy_detected,
            fallacy_name=fallacy_name,
        )


def analyze_fallacy(
    fallacy_tweet: str,
    context_tweet: str | None = None,
    client: OpenAI | None = None
) -> FallacyAnalysis:
    """
    Analyze a tweet for logical fallacies using Grok.

    Args:
        fallacy_tweet: The reply tweet containing the potential fallacy to analyze
        context_tweet: The original tweet being replied to (provides context)
        client: Optional OpenAI client (for testing)

    Returns:
        FallacyAnalysis with reply text, confidence score, and fallacy info
    """
    if client is None:
        client = get_grok_client()

    # Build user message with context if available
    if context_tweet:
        user_message = f"""Analyze this reply for logical fallacies:

ORIGINAL TWEET (context - what they're replying to):
{context_tweet}

REPLY TO ANALYZE (check for fallacies):
{fallacy_tweet}"""
    else:
        user_message = f"""Analyze this tweet for logical fallacies:

{fallacy_tweet}"""

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-reasoning-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.7,
        )

        response_text = response.choices[0].message.content.strip()
        logger.debug(f"Grok raw response: {response_text}")
        
        return _parse_analysis_response(response_text)

    except Exception as e:
        logger.error(f"Grok API error: {e}")
        # Return a fallback with low confidence so we don't post
        return FallacyAnalysis(
            reply_text="Unable to analyze this tweet right now. More: yourlogicalfallacyis.com",
            confidence=0,
            fallacy_detected=False,
            fallacy_name=None,
        )
