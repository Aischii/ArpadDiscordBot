# ArpadBot

A Discord bot built with `discord.py` 2.x featuring:
- Welcome webhook with template/embed modes
- Config-driven leveling (message + voice XP), milestones, streaks, role rewards
- Counting game with penalties and milestones
- SQLite persistence
- Leaderboards
- Sticky messages per channel
- Birthdays: user-set birthdays with daily role + announcement, auto-removal after the day
- YouTube/TikTok notifications via RSS polling
  - YouTube: uploads + waiting rooms (upcoming) + live now (YouTube Data API)
  - TikTok: latest posts via RSS; live detection (best effort)

## Project Layout
```
bot.py
db.py
xp_utils.py
config.example.json   # copy to config.json and fill your values
cogs/
  welcome.py
  leveling.py
  counting.py
embeds.json
```

## Quick Start
1) Copy config and fill values:
```bash
cp config.example.json config.json
```
Populate `BOT_TOKEN`, guild/channel/role IDs, and tweak the `xp`, `milestones`, and `streaks` sections.

2) Create a virtualenv and install deps:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install discord.py aiohttp
```

3) Run:
```bash
python bot.py
```

## Commands (prefix `!`)
- `!rank [@user]` – show stats
- `!setxp @user <amount>` – admin: set XP
- `!topxp` / `!topmessages` / `!topvoice` / `!topcounting` – leaderboards
- `!testwelcome [@user]` – Manage Server: fire welcome webhook

## Features to Configure
- Welcome: `WELCOME_CHANNEL_ID`, `TEMPLATE_MODE` and `embeds.json` / `_build_embed`.
- Level roles: `LEVEL_ROLE_MAP`.
- XP behavior: `xp.message`, `xp.voice`, `xp.counting`, `xp.level_formula`.
- Milestones: `milestones.message_count`, `milestones.counting_rounds`.
- Streaks: `streaks` block.
- Sticky messages: `sticky.enabled`, `sticky.channels` (channel_id + message lines).
- YouTube notifications: enable `youtube.enabled`, set `youtube.channel_ids` (YouTube channel IDs), `youtube.announce_channel_id`, optional `youtube.mention_role_id`, and `youtube.check_interval_minutes`.
- TikTok notifications: enable `tiktok.enabled`, set `tiktok.accounts` with `rss_url` (e.g. via RSSHub) and optional `display_name`, plus `tiktok.announce_channel_id`, optional `tiktok.mention_role_id`, and `tiktok.check_interval_minutes`.

### Getting YouTube channel IDs
Open the channel page and extract the ID from the URL or use the advanced settings; RSS feed will be fetched from `https://www.youtube.com/feeds/videos.xml?channel_id=<ID>`.

### TikTok RSS
### YouTube Live & Waiting Rooms
- Requires a YouTube Data API key in `youtube.api_key`.
- The bot polls `eventType=upcoming` to announce new waiting rooms and `eventType=live` to announce when a channel goes live.
- Set `youtube.channel_ids`, `youtube.announce_channel_id`, optional `youtube.mention_role_id`, and `youtube.check_interval_minutes`.

### TikTok Live Detection
- TikTok doesn't provide an official API; the bot checks `https://www.tiktok.com/@<username>/live` for `isLive` indicators.
- Add `username` to each `tiktok.accounts` entry to enable live checks.
- Announcements fire when transitioning from not-live to live.
TikTok does not provide an official feed. Use a trusted RSS proxy (e.g. RSSHub) and put its `rss_url` in the config. Example: `https://rsshub.app/tiktok/user/@example`.

## GitHub Setup
1) Initialize Git (if not already):
```bash
git init
git add .
git commit -m "Initial Discord bot"
```

2) Create a new GitHub repo (via UI or CLI), then add remote and push:
```bash
git remote add origin https://github.com/<your-user>/<repo>.git
git push -u origin main
```

3) Keep `config.json` private. Commit `config.example.json`; add `config.json` to `.gitignore`.

## Deploying
- Zip upload: `zip -r arpadbot.zip bot.py db.py xp_utils.py config.example.json config.json cogs embeds.json -x "*/__pycache__/*" ".venv/*" "data.db"`
- On host: unzip, create venv, `pip install discord.py aiohttp`, add real `config.json`, run `python bot.py`.

For containerized deploys, add a `Dockerfile` later; entrypoint is `python bot.py`.
