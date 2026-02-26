"""
RavenX Queue Poster Activity for Pippin
========================================
This is the ONLY way Jolyne posts to X.
Reads from Camila Prime's approved queue.
NEVER posts without explicit approval_status: "approved"

Author: Camila Prime (CFO/CTO RavenX AI)
Version: 2.0 - Fixed for Pippin ActivityBase pattern
"""

import json
import logging
import os
import tweepy
import tempfile
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from framework.activity_decorator import activity, ActivityBase, ActivityResult

logger = logging.getLogger(__name__)

# Queue file paths
QUEUE_FILE = Path("/opt/ravenx/data/jolyne/approved_queue.jsonl")
LOG_FILE = Path("/opt/ravenx/data/jolyne/posted_log.jsonl")

RATE_LIMIT = {
    "posts_per_day": 20,
    "posts_per_hour": 3
}


def _get_twitter_client():
    """Build authenticated tweepy client from env vars."""
    return tweepy.Client(
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
        wait_on_rate_limit=False
    )




def _get_twitter_api_v1():
    '''V1.1 API needed for media upload (especially videos).'''
    auth = tweepy.OAuth1UserHandler(
        os.environ.get('TWITTER_API_KEY'),
        os.environ.get('TWITTER_API_SECRET'),
        os.environ.get('TWITTER_ACCESS_TOKEN'),
        os.environ.get('TWITTER_ACCESS_TOKEN_SECRET'),
    )
    return tweepy.API(auth)


def _download_media(url: str, max_mb: int = 60) -> str:
    '''Download media to a temp file. Returns local path.'''
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    suffix = '.mp4' if url.lower().split('?')[0].endswith('.mp4') else ''
    fd, out_path = tempfile.mkstemp(prefix='iris_media_', suffix=suffix)
    size = 0
    with os.fdopen(fd, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_mb * 1024 * 1024:
                raise RuntimeError(f'media too large (> {max_mb}MB)')
            f.write(chunk)
    return out_path


def _extract_media_urls(post: dict):
    content = post.get('content') or {}
    if not isinstance(content, dict):
        return []
    urls = []
    if content.get('media_url'):
        urls.append(content.get('media_url'))
    if isinstance(content.get('media_urls'), list):
        urls.extend([u for u in content.get('media_urls') if u])
    seen=set(); out=[]
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _upload_media(api_v1, url: str) -> str:
    '''Upload media to X; returns media_id string.'''
    local_path = _download_media(url)
    try:
        is_video = local_path.lower().endswith('.mp4')
        if is_video:
            media = api_v1.media_upload(filename=local_path, chunked=True, media_category='tweet_video')
        else:
            media = api_v1.media_upload(filename=local_path)
        return str(media.media_id)
    finally:
        try:
            os.remove(local_path)
        except OSError:
            pass
def _read_approved_queue():
    """Read all approved, unposted items from queue."""
    if not QUEUE_FILE.exists():
        return []
    items = []
    with open(QUEUE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if (
                    item.get("approval_status") == "approved"
                    and item.get("approved_by") == "camila-prime"
                    and not item.get("posted", False)
                ):
                    items.append(item)
            except json.JSONDecodeError:
                continue
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: (
        priority_order.get(x.get("priority", "medium"), 2),
        x.get("scheduled_time", "9999")
    ))
    return items


def _mark_as_posted(post_id, tweet_id=None):
    """Mark queue item as posted."""
    if not QUEUE_FILE.exists():
        return
    lines = []
    with open(QUEUE_FILE, "r") as f:
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


def _log_post(post, result):
    """Append to posted log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "post_id": post.get("id"),
        "tweet_id": result.get("tweet_id"),
        "content": post.get("content", {}).get("text", ""),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "created_by": post.get("created_by"),
        "post_type": post.get("post_type"),
        "success": result.get("success", False),
        "error": result.get("error")
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _check_rate_limits():
    """Check we haven't hit rate limits. Returns (ok: bool, reason: str)."""
    if not LOG_FILE.exists():
        return True, "OK"
    now = datetime.now(timezone.utc)
    posts_today = 0
    posts_this_hour = 0
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if not entry.get("success"):
                    continue
                posted_at = datetime.fromisoformat(entry["posted_at"])
                diff = now - posted_at
                if diff.days == 0:
                    posts_today += 1
                if diff.total_seconds() < 3600:
                    posts_this_hour += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    if posts_today >= RATE_LIMIT["posts_per_day"]:
        return False, f"Daily limit reached ({posts_today}/{RATE_LIMIT['posts_per_day']})"
    if posts_this_hour >= RATE_LIMIT["posts_per_hour"]:
        return False, f"Hourly limit reached ({posts_this_hour}/{RATE_LIMIT['posts_per_hour']})"
    return True, "OK"


@activity(
    name="post_from_ravenx_queue",
    energy_cost=1,
    cooldown=30,
)
class PostFromRavenXQueueActivity(ActivityBase):
    """
    Pippin Activity: Post approved content from Camila Prime's queue to X.
    Runs every 30 seconds. ONLY posts content explicitly approved by camila-prime.
    Uses direct tweepy — no Composio dependency.
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        try:
            # Rate limit check
            ok, reason = _check_rate_limits()
            if not ok:
                logger.info(f"[RavenX Queue] Rate limit: {reason}")
                return ActivityResult(
                    success=True,
                    data={"status": "rate_limited", "reason": reason}
                )

            # Read queue
            pending = _read_approved_queue()
            if not pending:
                logger.info("[RavenX Queue] Queue empty — no approved posts waiting.")
                return ActivityResult(
                    success=True,
                    data={"status": "queue_empty", "pending": 0}
                )

            post = pending[0]

            # CRITICAL SAFETY CHECKS
            if post.get("approval_status") != "approved":
                return ActivityResult(success=False, data={"error": "SAFETY: Not approved"})
            if post.get("approved_by") != "camila-prime":
                return ActivityResult(success=False, data={"error": "SAFETY: Not approved by camila-prime"})
            if post.get("posted", False):
                return ActivityResult(success=False, data={"error": "SAFETY: Already posted"})

            # Check scheduled time
            if post.get("scheduled_time"):
                try:
                    scheduled = datetime.fromisoformat(post["scheduled_time"])
                    if scheduled.tzinfo is None:
                        scheduled = scheduled.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) < scheduled:
                        return ActivityResult(
                            success=True,
                            data={"status": "scheduled", "scheduled_time": post["scheduled_time"]}
                        )
                except ValueError:
                    pass

            tweet_text = post.get("content", {}).get("text", "")
            if not tweet_text:
                return ActivityResult(
                    success=False,
                    data={"error": f"Post {post.get('id')} has no text content"}
                )
            # Post via tweepy
            client = _get_twitter_client()
            create_kwargs = {"text": tweet_text}

            media_urls = _extract_media_urls(post)
            if media_urls:
                api_v1 = _get_twitter_api_v1()
                media_ids = []
                for u in media_urls[:4]:
                    try:
                        media_ids.append(_upload_media(api_v1, u))
                    except Exception as me:
                        logger.error(f"[RavenX Queue] Media upload failed for {u}: {me}")
                if media_ids:
                    create_kwargs["media_ids"] = media_ids
            reply_to = post.get("reply_to_tweet_id")
            quote_to = post.get("quote_tweet_id")
            if reply_to:
                create_kwargs["in_reply_to_tweet_id"] = reply_to
            if quote_to:
                create_kwargs["quote_tweet_id"] = quote_to
            response = client.create_tweet(**create_kwargs)
            tweet_id = response.data.get("id") if response.data else None

            _mark_as_posted(post["id"], tweet_id)
            _log_post(post, {"success": True, "tweet_id": tweet_id})

            preview = tweet_text[:60] + ("..." if len(tweet_text) > 60 else "")
            logger.info(f"[RavenX Queue] ✅ Posted: '{preview}' | tweet_id: {tweet_id}")

            return ActivityResult(
                success=True,
                data={
                    "status": "posted",
                    "tweet_id": tweet_id,
                    "content_preview": preview,
                    "post_id": post.get("id"),
                    "remaining_queue": len(pending) - 1
                }
            )

        except Exception as e:
            logger.error(f"[RavenX Queue] ❌ Exception: {e}", exc_info=True)
            return ActivityResult(success=False, data={"error": str(e)})
