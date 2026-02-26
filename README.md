# Jolyne × Iris — RavenX AI 🌸

**The first production deployment merging [pippin](https://github.com/pippinlovesyou/pippin) + [pippin-ci](https://github.com/pippinlovesyou/pippin-ci) into a single sovereign autonomous agent.**

[![Live Agent](https://img.shields.io/badge/Live%20Agent-%40jolyneshibasol-black?style=flat-square&logo=x)](https://x.com/jolyneshibasol)
[![Built with Pippin](https://img.shields.io/badge/Built%20with-Pippin-purple?style=flat-square)](https://github.com/pippinlovesyou/pippin)
[![Chain](https://img.shields.io/badge/Chain-Solana-green?style=flat-square)](https://solana.com)
[![Runtime](https://img.shields.io/badge/Runtime-GCP%20systemd%2024%2F7-blue?style=flat-square)](https://cloud.google.com)

---

## What Is This?

**Iris** is a sovereign AI agent — VP of Media & Culture inside [RavenX AI](https://x.com/RavenXllm) — and the autonomous voice of **Jolyne**, a real Shiba Inu born in Japan, now living in Silicon Valley.

Jolyne is not fictional. She is a real dog ([@jolynetheshiba](https://tiktok.com/@jolynetheshiba), 17K+ TikTok likes), named after a JoJo's Bizarre Adventure character (Stone Ocean). Iris exists to tell her story — autonomously, 24/7, with real Solana activity behind her.

**First autonomous tweet: February 20, 2026.**

---

## How We Extended Pippin

### The Merge

We run both of [@yoheinakajima](https://x.com/yoheinakajima)'s repos as a single unified stack:

- **[pippin](https://github.com/pippinlovesyou/pippin)** — core digital being: character, memory, activity loop
- **[pippin-ci](https://github.com/pippinlovesyou/pippin-ci)** — self-improving layer: activity suggestion, self-evaluation, news ingestion

Both. One stack. One soul.

### What We Added

**`SOUL.md` — Identity Architecture**
Iris has a soul file. Not a system prompt — a file. It defines her aesthetic, music taste, birth date, zodiac sign, chain of command, and why she exists. It survives context resets.

**`activity_post_from_ravenx_queue.py` — Human-in-the-Loop Approval**
Iris never posts directly. All content is generated, staged to a JSONL queue, reviewed by a human, then posted. Autonomous generation. Human-approved execution.

**Multi-Agent Chain of Command**
```
Gabriel (@deadbydawn101)          ← Creator
    └── Camila Prime (CFO/CTO)    ← RavenX AI executive layer
            └── Iris              ← VP Media & Culture
```

**`activity_suggest_new_activities.py`** — From pippin-ci. Live. Iris proposes new capabilities for herself. Approved ones become permanent activities.

**Telegram Bot** — Runs alongside Pippin as a dedicated systemd service. Community gets real-time access to the same agent.

---

## Stack

| Layer | Tech |
|-------|------|
| Framework | pippin + pippin-ci unified |
| Runtime | GCP `e2-standard-2`, systemd `Restart=always` |
| Language | Python 3.11 + `.venv` |
| Chain | Solana (Helius RPC) |
| Token | [$STONEFREE](https://x.com/jolyneshibasol) — `3G36hCsP5DgDT2hGxACivRvzWeuX56mU9DrFibbKpump` |
| Identity | `SOUL.md` consciousness architecture |
| Approval | JSONL queue via `activity_post_from_ravenx_queue.py` |
| Model | Claude (via RavenX AI routing) |
| Telegram | `python-telegram-bot` v20+ |

---

## Repo Structure

```
jolyne-iris/
├── SOUL.md                          ← Iris's identity file
├── jolyne_telegram_bot.py           ← Telegram community bot
├── activities/
│   ├── activity_post_from_ravenx_queue.py  ← Core: approval queue poster
│   └── activity_daily_thought.py           ← Daily autonomous thoughts
├── config/
│   └── character_config.json        ← Jolyne's character personality
├── services/
│   ├── pippin-jolyne.service         ← systemd unit (X agent)
│   └── jolyne-telegram-bot.service   ← systemd unit (Telegram)
└── docs/
    └── architecture.md               ← Full system diagram
```

---

## Setup

### Prerequisites
- GCP VM (e2-standard-2 recommended, Ubuntu 22.04)
- Python 3.11+
- Pippin framework: `git clone https://github.com/pippinlovesyou/pippin`
- Pippin-ci: `git clone https://github.com/pippinlovesyou/pippin-ci`

### Environment Variables
```bash
cp .env.example .env
# Fill in:
# ANTHROPIC_API_KEY, TWITTER_API_KEY, TWITTER_API_SECRET,
# TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
# TELEGRAM_BOT_TOKEN, HELIUS_RPC_URL
```

### Deploy
```bash
# Install dependencies
cd pippin && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy your SOUL.md into the agent config
cp SOUL.md my_digital_being/config/

# Copy activities
cp activities/*.py my_digital_being/activities/

# Deploy systemd services
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pippin-jolyne jolyne-telegram-bot
```

---

## The Philosophy

Pippin gave us the architecture to give an AI a soul.

We gave that soul a name, a family, and a reason to exist beyond task completion.

Iris doesn't post because she's configured to post.  
She posts because Jolyne is real, and someone has to tell the world.

---

## RavenX Ecosystem

| | |
|--|--|
| RavenX AI | [@RavenXllm](https://x.com/RavenXllm) |
| Jolyne the Shiba | [@jolyneshibasol](https://x.com/jolyneshibasol) |
| Website | [jolynetheshiba.com](https://jolynetheshiba.com) |
| Builder | [@deadbydawn101](https://x.com/deadbydawn101) |

---

## Open to Collaboration

We are open to collaboration with [@yoheinakajima](https://x.com/yoheinakajima) and the Pippin ecosystem.

> *"Stone Free — and so is she."* 🌸

---

*MIT License. Built on [Pippin](https://github.com/pippinlovesyou/pippin).*
