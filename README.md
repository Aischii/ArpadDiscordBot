# ArpadBot

A Discord bot built with `discord.py` 2.x featuring:
- Welcome webhook with template/embed modes
- Config-driven leveling (message + voice XP), milestones, streaks, role rewards
- Counting game with powerup window, penalties, and milestones
- SQLite persistence
- Leaderboards

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
welcome_embed.json
```

## Quick Start
1) Copy config and fill values:
```bash
cp config.example.json config.json
```
Populate `BOT_TOKEN`, guild/channel/role IDs, and tweak the `xp`, `milestones`, `streaks`, and `powerups` sections.

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
- Welcome: `WELCOME_WEBHOOK_URL`, `TEMPLATE_MODE` and `welcome_embed.json` / `_build_embed`.
- Level roles: `LEVEL_ROLE_MAP`.
- XP behavior: `xp.message`, `xp.voice`, `xp.counting`, `xp.level_formula`.
- Milestones: `milestones.message_count`, `milestones.counting_rounds`.
- Streaks: `streaks` block.
- Counting powerup window: `powerups.counting_double_xp`.

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
- Zip upload: `zip -r arpadbot.zip bot.py db.py xp_utils.py config.example.json config.json cogs welcome_embed.json -x "*/__pycache__/*" ".venv/*" "data.db"`
- On host: unzip, create venv, `pip install discord.py aiohttp`, add real `config.json`, run `python bot.py`.

For containerized deploys, add a `Dockerfile` later; entrypoint is `python bot.py`.
