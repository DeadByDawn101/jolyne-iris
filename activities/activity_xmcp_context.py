"""
XMCP Context Reader Activity for Iris / Jolyne
================================================
Uses xurl (X MCP native) to read live X context before posting.
Scans trending topics, mentions, and relevant conversations.
Feeds real-time X intelligence into Iris's post generation.

X API Update 2026: XMCP + pay-per-use unlocks this pattern.
Author: Camila Prime (CFO/CTO RavenX AI)
Version: 1.0 - Initial XMCP integration
"""

import json
import logging
import subprocess
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from framework.activity_decorator import activity, ActivityBase, ActivityResult

logger = logging.getLogger(__name__)

CONTEXT_CACHE = Path("/opt/ravenx/data/jolyne/xmcp_context.json")
CACHE_TTL_MINUTES = 15  # refresh X context every 15 min

SEARCH_TOPICS = [
    "solana $SOL",
    "$STONEFREE",
    "shiba inu meme coin",
    "AI agents",
    "Apple Silicon MLX",
    "memecoin solana",
]


def _run_xurl(args: list, timeout: int = 15) -> Optional[dict]:
    """Run xurl command, return parsed JSON or None."""
    try:
        result = subprocess.run(
            ["xurl"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning(f"[XMCP] xurl {args[0]} failed: {e}")
    return None


def _load_cached_context() -> Optional[dict]:
    """Load context if fresh enough."""
    if not CONTEXT_CACHE.exists():
        return None
    try:
        ctx = json.loads(CONTEXT_CACHE.read_text())
        cached_at = datetime.fromisoformat(ctx.get("cached_at", "2000-01-01"))
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        age_minutes = (datetime.now(timezone.utc) - cached_at).total_seconds() / 60
        if age_minutes < CACHE_TTL_MINUTES:
            return ctx
    except Exception:
        pass
    return None


def _save_context(ctx: dict):
    CONTEXT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ctx["cached_at"] = datetime.now(timezone.utc).isoformat()
    CONTEXT_CACHE.write_text(json.dumps(ctx, indent=2))


def _extract_post_texts(response: dict, limit: int = 5) -> list[str]:
    """Pull tweet texts from xurl response."""
    texts = []
    data = response.get("data", [])
    if isinstance(data, list):
        for item in data[:limit]:
            if isinstance(item, dict) and item.get("text"):
                texts.append(item["text"][:200])
    elif isinstance(data, dict) and data.get("text"):
        texts.append(data["text"][:200])
    return texts


@activity(
    name="xmcp_context_reader",
    energy_cost=2,
    cooldown=900,  # 15 min
)
class XMCPContextActivity(ActivityBase):
    """
    Uses xurl XMCP to read live X context:
    - Mentions (what are people saying to us)
    - Timeline (what's happening in our feed)
    - Trending topic search (SOL, STONEFREE, AI agents, MLX)

    Stores aggregated context to disk for use by the posting activity.
    This is what makes Iris reactive to the market — not just scheduled posts.
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        try:
            # Check cache first
            cached = _load_cached_context()
            if cached:
                logger.info("[XMCP] Using cached context (still fresh)")
                return ActivityResult(
                    success=True,
                    data={"status": "cached", "topics_tracked": len(SEARCH_TOPICS)}
                )

            context = {
                "mentions": [],
                "timeline_highlights": [],
                "topic_pulse": {},
                "market_signal": None,
            }

            # 1. Read mentions — what are people saying to @jolyneshibasol
            mentions_resp = _run_xurl(["mentions", "-n", "10"])
            if mentions_resp:
                context["mentions"] = _extract_post_texts(mentions_resp, 10)
                logger.info(f"[XMCP] Loaded {len(context['mentions'])} mentions")

            # 2. Timeline — what's in our feed
            timeline_resp = _run_xurl(["timeline", "-n", "10"])
            if timeline_resp:
                context["timeline_highlights"] = _extract_post_texts(timeline_resp, 5)
                logger.info(f"[XMCP] Loaded {len(context['timeline_highlights'])} timeline posts")

            # 3. Topic pulse — search each tracked topic
            for topic in SEARCH_TOPICS[:3]:  # limit to 3 searches per run (rate limit aware)
                resp = _run_xurl(["search", topic, "-n", "5"])
                if resp:
                    posts = _extract_post_texts(resp, 5)
                    context["topic_pulse"][topic] = posts
                    logger.info(f"[XMCP] Topic '{topic}': {len(posts)} posts")

            # 4. Market signal — SOL price sentiment from recent posts
            sol_resp = _run_xurl(["search", "$SOL price", "-n", "10"])
            if sol_resp:
                sol_texts = _extract_post_texts(sol_resp, 10)
                bullish = sum(1 for t in sol_texts if any(w in t.lower() for w in ["up","moon","pump","bull","ath","buy"]))
                bearish = sum(1 for t in sol_texts if any(w in t.lower() for w in ["down","dump","bear","sell","rug","crash"]))
                if bullish > bearish:
                    context["market_signal"] = "bullish"
                elif bearish > bullish:
                    context["market_signal"] = "bearish"
                else:
                    context["market_signal"] = "neutral"
                logger.info(f"[XMCP] Market signal: {context['market_signal']} (bull={bullish} bear={bearish})")

            _save_context(context)
            logger.info(f"[XMCP] ✅ Context refreshed and saved")

            return ActivityResult(
                success=True,
                data={
                    "status": "refreshed",
                    "mentions_count": len(context["mentions"]),
                    "timeline_count": len(context["timeline_highlights"]),
                    "topics_scanned": len(context["topic_pulse"]),
                    "market_signal": context["market_signal"],
                }
            )

        except Exception as e:
            logger.error(f"[XMCP] ❌ Exception: {e}", exc_info=True)
            return ActivityResult(success=False, data={"error": str(e)})
