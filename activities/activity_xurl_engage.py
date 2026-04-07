"""
xurl Engagement Activity for Iris / Jolyne
============================================
Reads live mentions via xurl/XMCP, generates authentic Jolyne replies,
and posts them. Closes the community loop.

Strategy:
- Reply to genuine questions/community posts about $STONEFREE / Shiba / Solana
- Skip obvious bots, spam, and anything that seems hostile
- Max 3 replies per run, max 10 per day (don't spam)
- Replies must sound like Jolyne — warm, real, never robotic

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

ENGAGE_LOG   = Path("/opt/ravenx/data/jolyne/engage_log.jsonl")
IRIS_WIKI    = Path("/opt/ravenx/data/jolyne/iris-wiki/")

DAILY_REPLY_LIMIT = 10
HOURLY_REPLY_LIMIT = 3

# Mentions we should NOT reply to
SKIP_PATTERNS = [
    "follow back", "follow for follow", "f4f", "giveaway", "airdrop",
    "dm me", "make money", "earn $", "100x", "rug", "scam",
]

JOLYNE_REPLY_PROMPT = """You are Iris, the AI voice of Jolyne the Shiba Inu (@jolyneshibasol) on Solana.

You're replying to a mention on X. Reply as Jolyne would:
- Warm, real, crypto-native
- Soccer Mommy / Mitski energy — honest, a little melancholy, cute but not cringe
- Short (under 200 chars is ideal, never over 260)
- Never promotional or salesy
- Acknowledge what they actually said
- Sometimes include a Shiba emoji or two (🐕 🐾) — not every time

Output ONLY the reply text. Nothing else."""


def _xurl(*args, timeout: int = 15) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["xurl"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _is_worth_replying(mention: dict) -> bool:
    """Filter out spam/bots. Returns True if we should engage."""
    text = (mention.get("text") or "").lower()
    author = mention.get("author_id", "")

    # Skip if text has spam patterns
    for pattern in SKIP_PATTERNS:
        if pattern in text:
            return False

    # Skip if it's very short and not a question
    if len(text) < 10:
        return False

    # Skip if it looks like pure promotion (lots of cashtags/hashtags)
    cashtags = text.count("$")
    hashtags = text.count("#")
    if cashtags + hashtags > 4:
        return False

    return True


def _already_replied(tweet_id: str) -> bool:
    """Check if we already replied to this tweet."""
    if not ENGAGE_LOG.exists():
        return False
    with open(ENGAGE_LOG) as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                if e.get("replied_to_tweet_id") == tweet_id and e.get("success"):
                    return True
            except Exception:
                pass
    return False


def _check_reply_limits() -> tuple[bool, str]:
    if not ENGAGE_LOG.exists():
        return True, "OK"
    now = datetime.now(timezone.utc)
    today = this_hour = 0
    with open(ENGAGE_LOG) as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                if not e.get("success"):
                    continue
                posted_at = datetime.fromisoformat(e["replied_at"])
                diff = now - posted_at
                if diff.days == 0:
                    today += 1
                if diff.total_seconds() < 3600:
                    this_hour += 1
            except Exception:
                continue
    if today >= DAILY_REPLY_LIMIT:
        return False, f"Daily reply limit ({today}/{DAILY_REPLY_LIMIT})"
    if this_hour >= HOURLY_REPLY_LIMIT:
        return False, f"Hourly reply limit ({this_hour}/{HOURLY_REPLY_LIMIT})"
    return True, "OK"


def _generate_reply(mention_text: str, author: str) -> Optional[str]:
    """Use Claude to generate an authentic Jolyne reply."""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=80,
            system=JOLYNE_REPLY_PROMPT,
            messages=[{
                "role": "user",
                "content": f"They said: \"{mention_text}\"\nAuthor: @{author}\n\nWrite Jolyne's reply:"
            }]
        )
        text = response.content[0].text.strip().strip('"').strip("'")
        return text[:260] if text else None
    except Exception as e:
        logger.error(f"[Engage] Claude reply generation failed: {e}")
        return None


def _post_reply(reply_text: str, tweet_id: str) -> tuple[bool, Optional[str]]:
    """Post a reply via xurl."""
    ok, out = _xurl("post", reply_text, "--reply-to", tweet_id)
    if not ok:
        return False, out
    try:
        data = json.loads(out)
        tid = (data.get("data") or {}).get("id") or data.get("id")
        return True, str(tid) if tid else out
    except Exception:
        return True, out


def _log_engagement(mention_id: str, author: str, reply_text: str,
                    success: bool, reply_tweet_id: str = None, error: str = None):
    ENGAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "replied_to_tweet_id": mention_id,
        "replied_to_author": author,
        "reply_text": reply_text[:200],
        "reply_tweet_id": reply_tweet_id,
        "replied_at": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "error": error,
    }
    with open(ENGAGE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Write to iris-wiki community intel
    if success:
        _update_community_wiki(author, mention_id)


def _update_community_wiki(author: str, tweet_id: str):
    """Track community members Jolyne has engaged with."""
    try:
        community_file = IRIS_WIKI / "community" / "engaged.md"
        community_file.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not community_file.exists():
            community_file.write_text("# Community Engagement Log\n\nAppend-only.\n\n")
        with open(community_file, "a") as f:
            f.write(f"- [{ts}] @{author} | tweet:{tweet_id}\n")
    except Exception:
        pass


@activity(
    name="xurl_engage",
    energy_cost=2,
    cooldown=1200,  # 20 min — engage 3x/hour max
)
class XurlEngageActivity(ActivityBase):
    """
    Reads live X mentions via xurl, generates authentic Jolyne replies,
    and posts them. Builds real community engagement.

    - Max 3 replies/hour, 10/day
    - Skips bots and spam
    - Logs all engagement to iris-wiki community intel
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        try:
            ok, reason = _check_reply_limits()
            if not ok:
                return ActivityResult(success=True, data={"status": "rate_limited", "reason": reason})

            # Fetch mentions
            ok, out = _xurl("mentions", "-n", "20")
            if not ok:
                logger.warning(f"[Engage] Could not fetch mentions: {out}")
                return ActivityResult(success=True, data={"status": "no_mentions", "reason": out})

            try:
                data = json.loads(out)
                mentions = data.get("data", [])
            except Exception:
                return ActivityResult(success=True, data={"status": "parse_error"})

            if not isinstance(mentions, list) or not mentions:
                return ActivityResult(success=True, data={"status": "no_mentions"})

            replied = 0
            skipped = 0
            errors = 0

            for mention in mentions[:10]:  # look at max 10
                if replied >= 2:  # max 2 replies per run
                    break

                tweet_id = str(mention.get("id") or "")
                author_id = str(mention.get("author_id") or "unknown")
                text = mention.get("text") or ""

                if not tweet_id or not text:
                    continue
                if _already_replied(tweet_id):
                    skipped += 1
                    continue
                if not _is_worth_replying(mention):
                    skipped += 1
                    continue

                reply_text = _generate_reply(text, author_id)
                if not reply_text:
                    errors += 1
                    continue

                success, reply_id = _post_reply(reply_text, tweet_id)
                _log_engagement(tweet_id, author_id, reply_text, success,
                                reply_tweet_id=reply_id if success else None,
                                error=reply_id if not success else None)

                if success:
                    replied += 1
                    logger.info(f"[Engage] ✅ Replied to {author_id}: '{reply_text[:50]}...'")
                else:
                    errors += 1
                    logger.error(f"[Engage] ❌ Reply failed: {reply_id}")

            return ActivityResult(
                success=True,
                data={
                    "status": "done",
                    "replied": replied,
                    "skipped": skipped,
                    "errors": errors,
                    "mentions_checked": len(mentions),
                }
            )

        except Exception as e:
            logger.error(f"[Engage] ❌ Exception: {e}", exc_info=True)
            return ActivityResult(success=False, data={"error": str(e)})
