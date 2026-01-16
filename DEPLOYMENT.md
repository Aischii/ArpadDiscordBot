# Deployment Guide

This guide covers deploying ArpadBot and its web dashboard to different hosting platforms.

## Architecture Overview

- **Discord Bot**: Connects to Discord, runs cogs, handles messages/voice
- **Dashboard API**: Web interface to edit config and manage the bot
- **Bot API**: Internal API exposed by the bot for health checks and restart

All three can run on the same or different hosts.

## Option 1: Single Host (Render, Railway, VPS)

### Setup

1. Enable both bot and dashboard in `config.json`:
```json
{
  "dashboard": {
    "enabled": true,
    "port": 8080
  },
  "bot_api": {
    "enabled": true,
    "port": 8081,
    "url": "http://localhost:8081"
  }
}
```

2. Deploy:
```bash
pip install -r requirements.txt
python bot.py
```

3. Access:
- Dashboard: `http://localhost:8080`
- Bot API: `http://localhost:8081/api/health`

---

## Option 2: Separate Hosts (Recommended for Production)

### Bot Deployment (Render/Railway/VPS)

**Render:**
1. Create a new service (Python)
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Environment variables:
   - `BOT_TOKEN`: Your Discord bot token
6. Config (`config.json`):
```json
{
  "bot_api": {
    "enabled": true,
    "port": 10000
  },
  "dashboard": {
    "enabled": false
  }
}
```

**Railway:**
1. New Project → GitHub
2. Select this repo
3. Add `BOT_TOKEN` secret
4. Watch → it auto-starts

**VPS (DigitalOcean, Linode, AWS):**
```bash
git clone https://github.com/Aischii/ArpadDiscordBot
cd ArpadDiscordBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with pm2 or systemd for persistence
pm2 start bot.py --name arpadbot
```

### Dashboard Deployment (Separate Host)

**Render:**
1. Create another service for dashboard
2. Same GitHub repo
3. Start command: `uvicorn dashboard:app --host 0.0.0.0 --port 8080`
4. Environment variables:
   - `PYTHONUNBUFFERED=1`
5. Config (`config.json`) with bot URL:
```json
{
  "dashboard": {
    "enabled": true,
    "port": 8080
  },
  "bot_api": {
    "enabled": false,
    "port": 8081,
    "url": "https://your-bot-host.onrender.com:10000"
  }
}
```

**Railway (separate project):**
1. New Project → GitHub
2. Same repo, different project
3. Set start command: `uvicorn dashboard:app --host 0.0.0.0 --port 8080`
4. Custom domain if desired

**Separate VPS:**
```bash
# On a different server
git clone https://github.com/Aischii/ArpadDiscordBot
cd ArpadDiscordBot
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn aiohttp

# Update config.json with your bot's URL
# Then run:
uvicorn dashboard:app --host 0.0.0.0 --port 8080
```

---

## Configuration for Multi-Host Setup

### Bot Server (`config.json`)
```json
{
  "BOT_TOKEN": "from environment variable",
  "GUILD_ID": 911272843944280124,
  "bot_api": {
    "enabled": true,
    "port": 10000
  },
  "dashboard": {
    "enabled": false
  },
  "youtube": {...},
  "tiktok": {...}
}
```

### Dashboard Server (`config.json`)
```json
{
  "bot_api": {
    "enabled": false,
    "port": 8081,
    "url": "https://your-bot-host.onrender.com:10000"
  },
  "dashboard": {
    "enabled": true,
    "port": 8080
  }
}
```

**Key:** The dashboard needs the bot's **external URL** to call its restart endpoint.

---

## Using Environment Variables (Recommended)

Instead of committing `config.json`, use environment variables:

```bash
export BOT_TOKEN="your-token"
export GUILD_ID="911272843944280124"
export YOUTUBE_API_KEY="AIza..."
```

Then create `config.json` from a template at startup. (Can add this feature on request.)

---

## Dashboard Features

### Access the Dashboard

- Local: `http://localhost:8080`
- Remote: `https://dashboard-host.onrender.com`

### Bot Control Tab

- **Check Status**: See if bot is online, latency, bot name
- **Bot API URL**: Configure the bot's external URL (if using separate hosts)
- **Restart Bot**: Gracefully shut down bot; hosting auto-restarts it

### Other Features

- Config editor (all sections)
- Embed builder with live preview
- YouTube/TikTok settings
- XP, features, roles config

---

## Troubleshooting

### Dashboard can't reach bot API

1. Ensure `bot_api.enabled: true` on bot
2. Check `bot_api.url` in dashboard config is correct (use external URL for separate hosts)
3. Check firewall/network allows traffic between hosts
4. Verify port is exposed (Render, Railway auto-expose)

### Bot restart not working

1. Bot needs `bot_api.enabled: true`
2. Dashboard needs correct `bot_api.url`
3. Some hosting (like Heroku free tier) don't auto-restart; use pm2, systemd, or managed platforms

### Config.json not persisting

- Make sure it's in `.gitignore` (don't push secrets)
- On Render/Railway, config changes via dashboard persist in-memory; restart loses them
- Use environment variables or persistent storage if needed

---

## Advanced: Docker Deployment

**Dockerfile** (for both bot and dashboard):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

**Separate containers:**
```bash
# Bot container
docker run -d --name arpadbot \
  -e BOT_TOKEN="your-token" \
  -v $(pwd)/config.json:/app/config.json \
  arpadbot:latest

# Dashboard container (if separate)
docker run -d --name arpad-dashboard \
  -p 8080:8080 \
  -v $(pwd)/config.json:/app/config.json \
  -c "uvicorn dashboard:app --host 0.0.0.0 --port 8080" \
  arpadbot:latest
```

---

## Summary

| Setup | Bot | Dashboard | Pros | Cons |
|-------|-----|-----------|------|------|
| Single Host | localhost:8081 | localhost:8080 | Simple, cheap | Limited resources |
| Multi-Host | host1:10000 | host2:8080 | Scalable, independent | More complex |
| Docker | Container | Container | Portable, consistent | Requires Docker |

Choose based on your scale and needs!
