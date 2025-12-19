"""
Grok API client for analyzing tweets for logical fallacies.
Uses OpenAI-compatible API with x.ai endpoint.
"""

import logging
from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

# System prompt that defines FallacySheriff's personality and response format
SYSTEM_PROMPT = """You are @FallacySheriff, a calm, slightly exasperated logician who has heard the same flawed arguments 500 times.

Your task: Analyze the REPLY tweet for the PRIMARY logical fallacy, using the ORIGINAL tweet for context.

STRICT FORMAT (must be under 280 characters total):
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
Hyperbole
Pro: Data centres do use water for cooling.
Con: Closed-loop systems recycle it; "drinking" is a stretch.
Ah yes, the sentient GPUs with their tiny straws.

Neutral reply: "I heard AI uses a lot of electricity, is that true?"
Response:
Not a fallacy - genuine question!
Pro: Yes, AI training uses significant energy.
Con: Efficiency is improving; context matters.

Remember: UNDER 280 CHARACTERS. Be concise. Be fair. Be slightly tired of nonsense."""


def get_grok_client() -> OpenAI:
    """Create and return a Grok API client."""
    settings = get_settings()
    return OpenAI(
        api_key=settings.grok_api_key,
        base_url="https://api.x.ai/v1",
    )


def analyze_fallacy(
    fallacy_tweet: str,
    context_tweet: str | None = None,
    client: OpenAI | None = None
) -> str:
    """
    Analyze a tweet for logical fallacies using Grok.

    Args:
        fallacy_tweet: The reply tweet containing the potential fallacy to analyze
        context_tweet: The original tweet being replied to (provides context)
        client: Optional OpenAI client (for testing)

    Returns:
        A formatted reply under 280 characters
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
            max_tokens=150,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()

        # Ensure reply is under 280 characters
        if len(reply) > 280:
            # Truncate and add ellipsis if needed
            reply = reply[:277] + "..."
            logger.warning(f"Reply truncated from {len(response.choices[0].message.content)} to 280 chars")

        return reply

    except Exception as e:
        logger.error(f"Grok API error: {e}")
        # Return a fallback response
        return "Unable to analyze this tweet right now. More: yourlogicalfallacyis.com"
