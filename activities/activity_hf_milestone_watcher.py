"""
IRIS Activity: HuggingFace Download Milestone Watcher
=======================================================
Watches our HF models and auto-queues celebration posts when
download milestones are hit. Iris posts it — not Gabe manually.

Milestones: 1k, 2.5k, 5k, 10k, 25k, 50k, 100k per model
             + collective milestones: 10k, 25k, 50k, 100k total

State persists in: ~/.iris_hf_milestones.json

Author: RavenX AI — April 2026
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

MODELS = {
    "deadbydawn101/gemma-4-E4B-mlx-4bit": "Gemma 4 E4B MLX 4-bit",
    "deadbydawn101/gemma-4-E4B-Agentic-Opus-Reasoning-GeminiCLI-mlx-4bit": "Gemma 4 Agentic Opus Reasoning",
    "deadbydawn101/gemma-4-E2B-Heretic-Uncensored-mlx-4bit": "Gemma 4 E2B Heretic Uncensored",
    "deadbydawn101/gemma-4-21b-REAP-Tool-Calling-mlx-4bit": "Gemma 4 21B REAP Tool Calling",
}

PER_MODEL_MILESTONES = [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
COLLECTIVE_MILESTONES = [5000, 10000, 25000, 50000, 100000, 250000, 500000]

STATE_PATH = Path.home() / ".iris_hf_milestones.json"

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"per_model": {}, "collective": []}


def save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ── HF API ────────────────────────────────────────────────────────────────────

def fetch_downloads(repo_id: str) -> int:
    url = f"https://huggingface.co/api/models/{repo_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "RavenX-IRIS/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("downloads", 0)
    except Exception:
        return 0


# ── Post Generation ───────────────────────────────────────────────────────────

def make_milestone_post(model_name: str, milestone: int, current: int) -> str:
    posts = {
        500: f"📈 {model_name} just hit {milestone:,} downloads on Hugging Face. Appreciation to everyone running it on Apple Silicon. 🖤",
        1000: f"🎯 1,000 downloads — {model_name} is officially in the hands of the community. This is just the beginning. 🖤",
        2500: f"🔥 {model_name} — {milestone:,} downloads. Apple Silicon inference is accelerating. 🖤",
        5000: f"🚀 {model_name} just crossed {milestone:,} downloads. Built for M-series Macs, running everywhere. 🖤",
        10000: f"⚡ {model_name} hit {milestone:,} downloads. What started as a weekend experiment is now part of the open-source ecosystem. Thank you. 🖤",
    }
    default = f"🖤 {model_name} — {milestone:,} downloads. The empire grows. #AppleSilicon #OpenSource #RavenX"
    return posts.get(milestone, default)


def make_collective_post(milestone: int, current: int, breakdown: dict) -> str:
    top = max(breakdown, key=breakdown.get)
    top_name = MODELS.get(top, top.split("/")[-1])
    top_count = breakdown[top]

    if milestone == 10000:
        return (
            f"🎉 We just crossed {milestone:,} total downloads across the RavenX model collection on Hugging Face.\n\n"
            f"Leading: {top_name} at {top_count:,} downloads.\n\n"
            f"Built for Apple Silicon. Running on M1→M4. TriAttention compressed. Open source.\n\n"
            f"This is what we're building. 🖤 #RavenX #AppleSilicon #MLX"
        )
    return (
        f"🚀 {milestone:,} total downloads — RavenX model collection.\n\n"
        f"{top_name} leading at {top_count:,}. "
        f"Every download is someone running our models locally on Apple Silicon. 🖤 #RavenX"
    )


# ── Queue Post ────────────────────────────────────────────────────────────────

def queue_post(text: str, source: str = "hf_milestone"):
    """Add post to the Iris post queue."""
    queue_path = Path.home() / "Projects/jolyne-iris/ravenx_post_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "source": source,
        "status": "pending",
        "text": text,
    }
    with open(queue_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[iris][milestone] queued post: {text[:80]}...")


# ── Main Activity ─────────────────────────────────────────────────────────────

def run():
    state = load_state()
    downloads: dict[str, int] = {}
    new_posts = 0

    print("[iris][milestone] checking HF download counts...")
    for repo_id, name in MODELS.items():
        dl = fetch_downloads(repo_id)
        downloads[repo_id] = dl
        print(f"  {dl:>7,}  {name}")

        # Per-model milestone check
        hit = state["per_model"].get(repo_id, 0)
        for milestone in PER_MODEL_MILESTONES:
            if dl >= milestone and milestone > hit:
                post = make_milestone_post(name, milestone, dl)
                queue_post(post, source=f"hf_model_milestone:{repo_id}:{milestone}")
                state["per_model"][repo_id] = milestone
                new_posts += 1

    # Collective milestone check
    total = sum(downloads.values())
    print(f"  {total:>7,}  TOTAL")
    collective_hit = set(state.get("collective", []))
    for milestone in COLLECTIVE_MILESTONES:
        if total >= milestone and milestone not in collective_hit:
            post = make_collective_post(milestone, total, downloads)
            queue_post(post, source=f"hf_collective_milestone:{milestone}")
            collective_hit.add(milestone)
            new_posts += 1

    state["collective"] = list(collective_hit)
    state["last_checked"] = time.time()
    state["last_total"] = total
    save_state(state)

    if new_posts:
        print(f"[iris][milestone] 🎉 {new_posts} milestone post(s) queued!")
    else:
        print(f"[iris][milestone] no new milestones (total: {total:,})")

    return {"total_downloads": total, "new_posts_queued": new_posts}


if __name__ == "__main__":
    run()
