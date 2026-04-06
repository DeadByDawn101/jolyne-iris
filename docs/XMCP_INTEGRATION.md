# Iris XMCP Integration — X API 2026 Upgrade

## What Changed

X launched native **XMCP (Model Context Protocol)** support + pay-per-use pricing.

For Iris this is a fundamental upgrade: she goes from **scheduled poster → truly reactive agentic agent**.

## The New Loop

```
X Live Context (XMCP)
        ↓
activity_xmcp_context.py     — reads mentions, timeline, topic pulse, market signal
        ↓
activity_xmcp_post_generator.py  — Claude generates reactive posts from live context
        ↓
approved_queue.jsonl          — queued with camila-prime approval
        ↓
activity_post_from_ravenx_queue.py  — posts to X via xurl (existing)
        ↓
X / @jolyneshibasol
```

## New Activities

### `activity_xmcp_context.py`
- Runs every 15 min (cooldown: 900s)
- Reads: mentions, timeline, topic searches (SOL, STONEFREE, AI agents, MLX)
- Computes market sentiment signal: bullish / bearish / neutral
- Caches context to `/opt/ravenx/data/jolyne/xmcp_context.json`

### `activity_xmcp_post_generator.py`
- Runs every 30 min (cooldown: 1800s)
- Reads live context → picks post type:
  - `market_reactive` if SOL is clearly bullish or bearish
  - `community` if there are mentions to respond to
  - `organic` otherwise
- Uses Claude Opus to generate authentic Jolyne voice
- Auto-queues with `approved_by: camila-prime`

## xurl Setup (One-Time)

```bash
# Register the @jolyneshibasol app
xurl auth apps add jolyne

# Authenticate
xurl auth oauth2

# Verify
xurl auth status
xurl whoami
```

## Pay-Per-Use Advantage

Old model: monthly tier → billing anxiety on high-volume posting.
New model: pay per API call → Iris can post reactively without worrying about tier limits.

xAI credit bonus: 20% back when buying X API credits → feeds directly into Grok-powered market analysis for Iris.

## What This Unlocks

| Before | After |
|---|---|
| Scheduled posts only | Reactive to live X context |
| No market awareness | Bullish/bearish signal from real X data |
| No mention reading | Responds to community mentions |
| Tweepy only | xurl XMCP native |
| Tier anxiety | Pay-per-use freedom |

## GCP Deployment

The two new activities deploy alongside existing Iris services on `ravenx-qa-core-1`:

```bash
# Copy activities to GCP
scp -i ~/.ssh/ravenx_gcp_qa activities/activity_xmcp_context.py ravenx@34.182.110.4:/opt/ravenx/jolyne-iris/activities/
scp -i ~/.ssh/ravenx_gcp_qa activities/activity_xmcp_post_generator.py ravenx@34.182.110.4:/opt/ravenx/jolyne-iris/activities/

# Restart Iris
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 'sudo systemctl restart pippin-jolyne.service'

# Watch logs
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 'journalctl -u pippin-jolyne -f'
```

## Status

- [ ] xurl app registered for @jolyneshibasol (`xurl auth apps add`)
- [ ] OAuth2 authenticated (`xurl auth oauth2`)
- [ ] Activities deployed to GCP
- [ ] `pippin-jolyne.service` restarted
- [ ] First XMCP context pull verified
- [ ] First reactive post generated and queued
- [ ] First reactive post fired live

---

*Built by Camila Prime, CFO/CTO RavenX AI — April 2026*
