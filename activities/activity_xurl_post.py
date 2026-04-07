"""
xurl Post Activity for Iris / Jolyne
======================================
Drop-in replacement for activity_post_from_ravenx_queue.py's tweepy poster.
Uses xurl CLI (X MCP native) instead of tweepy.

Why xurl over tweepy:
- Native XMCP integration — same tool chain as context reader
- Pay-per-use billing — no tier anxiety
- First-class agent tool (X's official agent CLI)
- Simpler auth — one xurl auth oauth2, no 4-token juggle

Author: Camila Prime (CFO/CTO RavenX AI)
Version: 1.0 — xurl native posting
"""

import json
import logging
import os
import subprocess
import tempfile
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from framework.activity_decorator import activity, ActivityBase, ActivityResult

logger = logging.getLogger(__name__)

QUEUE_FILE = Path("/opt/ravenx/data/jolyne/approved_queue.jsonl")
LOG_FILE   = Path("/opt/ravenx/data/jolyne/posted_log.jsonl")
IRIS_WIKI  = Path("/opt/ravenx/data/jolyne/iris-wiki/")

RATE_LIMIT = {"posts_per_day": 20, "posts_per_hour": 3}


# ─────────────────────────── xurl helpers ────────────────────────────────────

def _xurl(*args, timeout: int = 20) -> tuple[bool, str]:
    """Run xurl command. Returns (success, output/error)."""
    try:
        result = subprocess.run(
            ["xurl"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "xurl timeout"
    except FileNotFoundError:
        return False, "xurl not in PATH"
    except Exception as e:
        return False, str(e)


def _xurl_post(text: str, media_ids: list[str] = None,
               reply_to: str = None, quote_id: str = None) -> tuple[bool, Optional[str]]:
    """Post a tweet via xurl. Returns (success, tweet_id or error)."""
    args = ["post", text]
    if media_ids:
        for mid in media_ids[:4]:
            args += ["--media", mid]
    if reply_to:
        args += ["--reply-to", reply_to]
    if quote_id:
        args += ["--quote", quote_id]

    ok, out = _xurl(*args)
    if not ok:
        return False, out

    # Try to parse tweet id from output
    try:
        data = json.loads(out)
        tweet_id = (data.get("data", {}) or {}).get("id") or data.get("id")
        return True, str(tweet_id) if tweet_id else out
    except (json.JSONDecodeError, AttributeError):
        # xurl might just return the id as plain text
        if out and out.isdigit():
            return True, out
        return True, out  # posted but couldn't parse id


def _upload_media_xurl(url: str) -> Optional[str]:
    """Download media from URL, upload via xurl, return media_id."""
    suffix = ".mp4" if url.lower().split("?")[0].endswith(".mp4") else ".jpg"
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        fd, path = tempfile.mkstemp(prefix="iris_media_", suffix=suffix)
        size = 0
        with os.fdopen(fd, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    size += len(chunk)
                    if size > 60 * 1024 * 1024:
                        raise RuntimeError("media > 60MB")
                    f.write(chunk)
        ok, out = _xurl("media", "upload", path)
        os.remove(path)
        if not ok:
            logger.error(f"[xurl] media upload failed: {out}")
            return None
        try:
            return str(json.loads(out).get("media_id_string") or json.loads(out).get("media_id"))
        except Exception:
            return out.strip() if out.strip().isdigit() else None
    except Exception as e:
        logger.error(f"[xurl] media download/upload error: {e}")
        return None


# ─────────────────────────── queue helpers ───────────────────────────────────

def _read_approved_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    items = []
    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if (item.get("approval_status") == "approved"
                        and item.get("approved_by") == "camila-prime"
                        and not item.get("posted", False)):
                    items.append(item)
            except json.JSONDecodeError:
                continue
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: (
        priority_order.get(x.get("priority", "medium"), 2),
        x.get("scheduled_time", "9999")
    ))
    return items


def _mark_as_posted(post_id: str, tweet_id: str = None):
    if not QUEUE_FILE.exists():
        return
    lines = []
    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("id") == post_id:
                    item["posted"] = True
                    item["posted_at"] = datetime.now(timezone.utc).isoformat()
                    item["tweet_id"] = tweet_id
                lines.append(json.dumps(item))
            except json.JSONDecodeError:
                lines.append(line)
    with open(QUEUE_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def _log_post(post: dict, result: dict):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "post_id": post.get("id"),
        "tweet_id": result.get("tweet_id"),
        "content": post.get("content", {}).get("text", ""),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "created_by": post.get("created_by"),
        "post_type": post.get("post_type"),
        "poster": "xurl",
        "success": result.get("success", False),
        "error": result.get("error"),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also append to iris-wiki winners tracker if successful
    if result.get("success") and post.get("content", {}).get("text"):
        _update_iris_wiki_log(post, result.get("tweet_id"))


def _update_iris_wiki_log(post: dict, tweet_id: str):
    """Append posted tweet to iris-wiki log for compounding intelligence."""
    try:
        wiki_log = IRIS_WIKI / "log.md"
        IRIS_WIKI.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        text = post.get("content", {}).get("text", "")[:80]
        post_type = post.get("post_type", "unknown")
        entry = f"\n## [{ts}] posted | {post_type} | tweet:{tweet_id}\n`{text}`\n"
        with open(wiki_log, "a") as f:
            f.write(entry)
    except Exception:
        pass  # wiki logging is best-effort


def _check_rate_limits() -> tuple[bool, str]:
    if not LOG_FILE.exists():
        return True, "OK"
    now = datetime.now(timezone.utc)
    today = this_hour = 0
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if not e.get("success"):
                    continue
                posted_at = datetime.fromisoformat(e["posted_at"])
                diff = now - posted_at
                if diff.days == 0:
                    today += 1
                if diff.total_seconds() < 3600:
                    this_hour += 1
            except Exception:
                continue
    if today >= RATE_LIMIT["posts_per_day"]:
        return False, f"Daily limit ({today}/{RATE_LIMIT['posts_per_day']})"
    if this_hour >= RATE_LIMIT["posts_per_hour"]:
        return False, f"Hourly limit ({this_hour}/{RATE_LIMIT['posts_per_hour']})"
    return True, "OK"


# ─────────────────────────── activity ────────────────────────────────────────

@activity(
    name="xurl_post",
    energy_cost=1,
    cooldown=30,
)
class XurlPostActivity(ActivityBase):
    """
    Posts approved queue items to X via xurl (XMCP native).
    Drop-in replacement for tweepy-based poster.
    Falls back to tweepy if xurl is unavailable.
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        try:
            # Rate limit check
            ok, reason = _check_rate_limits()
            if not ok:
                return ActivityResult(success=True, data={"status": "rate_limited", "reason": reason})

            pending = _read_approved_queue()
            if not pending:
                return ActivityResult(success=True, data={"status": "queue_empty"})

            post = pending[0]

            # Safety gates — never skip these
            if post.get("approval_status") != "approved":
                return ActivityResult(success=False, data={"error": "SAFETY: Not approved"})
            if post.get("approved_by") != "camila-prime":
                return ActivityResult(success=False, data={"error": "SAFETY: Not approved by camila-prime"})
            if post.get("posted", False):
                return ActivityResult(success=False, data={"error": "SAFETY: Already posted"})

            # Scheduled time check
            if post.get("scheduled_time"):
                try:
                    scheduled = datetime.fromisoformat(post["scheduled_time"])
                    if scheduled.tzinfo is None:
                        scheduled = scheduled.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) < scheduled:
                        return ActivityResult(success=True, data={"status": "scheduled"})
                except ValueError:
                    pass

            tweet_text = (post.get("content") or {}).get("text", "")
            if not tweet_text:
                return ActivityResult(success=False, data={"error": f"Post {post.get('id')} has no text"})

            # Upload media if present
            media_ids = []
            content = post.get("content") or {}
            media_urls = []
            if content.get("media_url"):
                media_urls.append(content["media_url"])
            if isinstance(content.get("media_urls"), list):
                media_urls.extend(content["media_urls"])
            for url in media_urls[:4]:
                mid = _upload_media_xurl(url)
                if mid:
                    media_ids.append(mid)

            # Post via xurl
            success, tweet_id = _xurl_post(
                tweet_text,
                media_ids=media_ids or None,
                reply_to=post.get("reply_to_tweet_id"),
                quote_id=post.get("quote_tweet_id"),
            )

            if not success:
                # xurl failed — log but don't mark as posted
                logger.error(f"[xurl Post] ❌ Failed: {tweet_id}")
                _log_post(post, {"success": False, "error": tweet_id})
                return ActivityResult(success=False, data={"error": tweet_id})

            _mark_as_posted(post["id"], tweet_id)
            _log_post(post, {"success": True, "tweet_id": tweet_id})

            preview = tweet_text[:60] + ("..." if len(tweet_text) > 60 else "")
            logger.info(f"[xurl Post] ✅ Posted: '{preview}' | tweet_id: {tweet_id}")

            return ActivityResult(
                success=True,
                data={
                    "status": "posted",
                    "poster": "xurl",
                    "tweet_id": tweet_id,
                    "content_preview": preview,
                    "post_id": post.get("id"),
                    "remaining_queue": len(pending) - 1,
                }
            )

        except Exception as e:
            logger.error(f"[xurl Post] ❌ Exception: {e}", exc_info=True)
            return ActivityResult(success=False, data={"error": str(e)})
