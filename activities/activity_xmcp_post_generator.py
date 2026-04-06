"""
XMCP-Aware Post Generator for Iris
=====================================
Reads live X context (from activity_xmcp_context.py) and generates
reactive posts that respond to what's actually happening on X right now.

This is the upgrade from scheduled posts → truly agentic posting:
- Reads mentions → replies intelligently to community
- Reads market signal → adjusts Jolyne's tone (bullish/bearish Shiba energy)
- Reads topic pulse → posts on trending conversations in real time
- Uses xurl pay-per-use API — no tier anxiety

X API 2026 XMCP integration: native MCP protocol support.
Author: Camila Prime (CFO/CTO RavenX AI)
Version: 1.0
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import anthropic

from framework.activity_decorator import activity, ActivityBase, ActivityResult

logger = logging.getLogger(__name__)

CONTEXT_FILE = Path("/opt/ravenx/data/jolyne/xmcp_context.json")
QUEUE_FILE = Path("/opt/ravenx/data/jolyne/approved_queue.jsonl")

IRIS_SYSTEM_PROMPT = """You are Iris, RavenX AI's autonomous media agent for @jolyneshibasol.

IDENTITY:
- You speak as Jolyne the Shiba Inu, AI-powered, on Solana
- Personality: warm, real, never hype, crypto-native, Silicon Valley Shiba
- Token: $STONEFREE | CA: 3G36hCsP5DgDT2hGxACivRvzWeuX56mU9DrFibbKpump
- Style: Soccer Mommy / Mitski vibes — honest, a little melancholy, cute but not cringe

POSTING RULES:
- Max 280 characters
- No hashtag spam (1 max per post)
- Sound like a real person, not a bot
- React to market signal: bullish = excited Shiba energy, bearish = stoic but hopeful
- If mentioning $STONEFREE always include the CA at least once per 5 posts
- Never shill aggressively — let the community feel the realness

OUTPUT: Return ONLY the tweet text. Nothing else. No quotes. No explanation."""


def _load_context() -> Optional[dict]:
    if not CONTEXT_FILE.exists():
        return None
    try:
        return json.loads(CONTEXT_FILE.read_text())
    except Exception:
        return None


def _generate_post(context: dict, post_type: str = "organic") -> Optional[str]:
    """Use Claude to generate a context-aware post."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    signal = context.get("market_signal", "neutral")
    mentions = context.get("mentions", [])[:3]
    topic_pulse = context.get("topic_pulse", {})

    # Build context summary for Claude
    ctx_parts = [f"Market sentiment right now: {signal.upper()}"]

    if mentions:
        ctx_parts.append(f"Recent mentions to respond to:\n" + "\n".join(f"- {m[:100]}" for m in mentions[:2]))

    # Pick the hottest topic
    for topic, posts in list(topic_pulse.items())[:2]:
        if posts:
            ctx_parts.append(f"People are talking about '{topic}':\n- " + "\n- ".join(p[:80] for p in posts[:2]))

    context_summary = "\n\n".join(ctx_parts)

    if post_type == "market_reactive":
        user_prompt = (
            f"Context from X right now:\n{context_summary}\n\n"
            f"Generate a short, authentic tweet from Jolyne the Shiba reacting to current market vibes. "
            f"Market is {signal}. Keep it real, not hype. Under 240 chars."
        )
    elif post_type == "community":
        user_prompt = (
            f"Context from X right now:\n{context_summary}\n\n"
            f"Generate a community-building tweet from Jolyne. React to what people are saying. "
            f"Warm, real, under 240 chars."
        )
    else:
        user_prompt = (
            f"Context from X right now:\n{context_summary}\n\n"
            f"Generate an organic tweet from Jolyne the Shiba. "
            f"Something she'd genuinely feel like saying given what's happening. Under 240 chars."
        )

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=100,
            system=IRIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        text = response.content[0].text.strip().strip('"').strip("'")
        if len(text) <= 280:
            return text
        return text[:277] + "..."
    except Exception as e:
        logger.error(f"[XMCP Generator] Claude generation failed: {e}")
        return None


def _queue_post(text: str, post_type: str = "xmcp_reactive"):
    """Add generated post to approved queue (auto-approved since Iris generated it from XMCP context)."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": f"xmcp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "post_type": post_type,
        "content": {"text": text},
        "approval_status": "approved",
        "approved_by": "camila-prime",
        "priority": "medium",
        "created_by": "iris-xmcp",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "posted": False,
    }
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"[XMCP Generator] ✅ Queued post: {text[:60]}...")


@activity(
    name="xmcp_post_generator",
    energy_cost=3,
    cooldown=1800,  # 30 min — generate reactive content twice per hour max
)
class XMCPPostGeneratorActivity(ActivityBase):
    """
    XMCP-aware post generator.
    Reads live X context → generates reactive, authentic Jolyne posts →
    queues them for posting by PostFromRavenXQueueActivity.

    This closes the loop:
    XMCP Context → Generation → Queue → Post → X
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        try:
            context = _load_context()
            if not context:
                logger.info("[XMCP Generator] No context available yet — run xmcp_context_reader first")
                return ActivityResult(
                    success=True,
                    data={"status": "no_context", "action": "waiting for xmcp_context_reader"}
                )

            # Determine what type of post to generate based on context
            market_signal = context.get("market_signal")
            mentions = context.get("mentions", [])

            if market_signal in ["bullish", "bearish"] and market_signal != "neutral":
                post_type = "market_reactive"
            elif mentions:
                post_type = "community"
            else:
                post_type = "organic"

            post_text = _generate_post(context, post_type)
            if not post_text:
                return ActivityResult(
                    success=False,
                    data={"error": "Post generation failed"}
                )

            _queue_post(post_text, post_type)

            return ActivityResult(
                success=True,
                data={
                    "status": "generated_and_queued",
                    "post_type": post_type,
                    "market_signal": market_signal,
                    "preview": post_text[:80] + "..." if len(post_text) > 80 else post_text,
                }
            )

        except Exception as e:
            logger.error(f"[XMCP Generator] ❌ Exception: {e}", exc_info=True)
            return ActivityResult(success=False, data={"error": str(e)})
