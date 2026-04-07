# 🖤 Iris XMCP Upgrade — Home Checklist

Everything that's been built while you were out. Do these in order when you get home.

---

## ✅ Already Done (no action needed)

- [x] `activity_xmcp_context.py` — reads live X context every 15 min
- [x] `activity_xmcp_post_generator.py` — generates reactive posts from live X context
- [x] `activity_xurl_post.py` — posts via xurl instead of tweepy
- [x] `activity_xurl_engage.py` — reads mentions, generates + posts replies
- [x] `scripts/deploy_to_gcp.sh` — one command deploys everything to GCP
- [x] `docs/XMCP_INTEGRATION.md` — full architecture docs
- [x] Empire Wiki seeded in `workspace/wiki/`
- [x] Iris Market Intelligence Wiki seeded in `workspace/wiki/iris-wiki/`
- [x] All committed and pushed to GitHub

---

## 🔑 Step 1 — xurl Auth for @jolyneshibasol (MacBook Pro or GCP)

This is the only blocker. One-time setup.

**Option A: On GCP (where Pippin runs)**
```bash
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4
xurl auth apps add
# Enter your X app credentials (from developer.twitter.com)
# App name: jolynetheshiba
# API Key: TWITTER_API_KEY from .env
# API Secret: TWITTER_API_SECRET from .env
xurl auth oauth2
# Follow the OAuth2 flow in browser
xurl auth status   # confirm green
xurl whoami        # should show @jolynetheshiba
```

**Option B: Local (MacBook) then copy config**
```bash
xurl auth apps add
xurl auth oauth2
# Then copy ~/.xurl/ to GCP:
scp -i ~/.ssh/ravenx_gcp_qa -r ~/.xurl/ ravenx@34.182.110.4:~/.xurl/
```

---

## 🚀 Step 2 — Deploy to GCP

```bash
cd ~/Projects/jolyne-iris
chmod +x scripts/deploy_to_gcp.sh
./scripts/deploy_to_gcp.sh
```

This uploads all 4 activities, creates iris-wiki dirs, and restarts Pippin.

---

## ✅ Step 3 — Verify

```bash
# Watch Pippin logs
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 \
  'journalctl -u pippin-jolyne -f'

# Check if context is being fetched
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 \
  'cat /opt/ravenx/data/jolyne/xmcp_context.json 2>/dev/null | python3 -m json.tool | head -30'

# Check the queue
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 \
  'tail -5 /opt/ravenx/data/jolyne/approved_queue.jsonl 2>/dev/null'

# Check posted log
ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 \
  'tail -10 /opt/ravenx/data/jolyne/posted_log.jsonl 2>/dev/null'
```

---

## 🔄 Step 4 — Switch Poster from tweepy → xurl

Once xurl is confirmed working, disable the old tweepy poster in Pippin's activity config
and enable `xurl_post` instead:

The new activity name is: `xurl_post`
The old activity name is: `post_from_ravenx_queue`

Check how Pippin loads activities (may need to update `my_digital_being/` config).

---

## 📊 What Iris Does After This

Every 15 min:
- Reads live X mentions, timeline, topic pulse ($SOL, $STONEFREE, AI agents, MLX)
- Detects market signal: bullish / bearish / neutral
- Saves to `/opt/ravenx/data/jolyne/xmcp_context.json`

Every 30 min:
- Reads that context
- Claude generates a reactive, authentic Jolyne post
- Auto-queues with camila-prime approval
- `xurl_post` activity fires it to @jolyneshibasol

Every 20 min:
- Reads mentions
- Filters spam/bots
- Generates authentic Jolyne replies via Claude
- Posts replies via xurl
- Logs to iris-wiki community intel

---

## 🔧 Troubleshooting

**xurl: No apps registered**
→ `xurl auth apps add` not done yet

**xurl: Permission denied**
→ `xurl auth oauth2` needed

**Activities not loading in Pippin**
→ Check `/opt/ravenx/logs/pippin-error.log` on GCP
→ May need to add activities to `character_config.json` or Pippin's activity loader

**Context file empty**
→ `xurl mentions -n 5` — test xurl directly on GCP first

---

*Built by Camila Prime 🖤 — April 2026*
