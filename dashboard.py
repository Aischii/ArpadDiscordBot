from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
from pathlib import Path
import logging
import aiohttp

logger = logging.getLogger(__name__)

app = FastAPI(title="ArpadBot Dashboard")
CONFIG_PATH = Path("config.json")

# Serve static files (CSS, JS) from a static folder if needed
# app.mount("/static", StaticFiles(directory="static"), name="static")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="config.json not found")
    with CONFIG_PATH.open() as fp:
        return json.load(fp)


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w") as fp:
        json.dump(config, fp, indent=2)


@app.get("/")
async def root():
    """Serve the dashboard HTML."""
    return FileResponse("templates/index.html", media_type="text/html")


@app.get("/embed")
async def embed_page():
    """Serve the embed builder."""
    return FileResponse("templates/embed.html", media_type="text/html")


@app.get("/api/config")
async def get_config():
    """Fetch current config."""
    return load_config()


@app.post("/api/config")
async def update_config(data: dict):
    """Update config and save to file."""
    try:
        save_config(data)
        logger.info("Config updated via dashboard")
        return {"status": "ok", "message": "Config saved successfully"}
    except Exception as e:
        logger.exception("Failed to save config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")


@app.get("/api/embed")
async def get_embed():
    """Fetch current welcome embed from welcome_embed.json."""
    embed_path = Path("welcome_embed.json")
    if not embed_path.exists():
        return {"embeds": []}
    with embed_path.open() as fp:
        return json.load(fp)


@app.post("/api/embed")
async def save_embed(data: dict):
    """Save embed to welcome_embed.json."""
    try:
        embed_path = Path("welcome_embed.json")
        with embed_path.open("w") as fp:
            json.dump(data, fp, indent=2)
        logger.info("Embed saved via dashboard")
        return {"status": "ok", "message": "Embed saved successfully"}
    except Exception as e:
        logger.exception("Failed to save embed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")


@app.post("/api/bot/restart")
async def restart_bot():
    """Restart the bot via its API endpoint."""
    try:
        config = load_config()
        bot_api_url = config.get("bot_api", {}).get("url") or "http://localhost:8081"
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{bot_api_url}/api/restart", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return {"status": "ok", "message": "Bot restart initiated"}
                else:
                    raise Exception(f"Bot API returned {resp.status}")
    except Exception as e:
        logger.exception("Failed to restart bot: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to restart: {e}")


@app.get("/api/bot/health")
async def get_bot_health():
    """Get bot health status from its API."""
    try:
        config = load_config()
        bot_api_url = config.get("bot_api", {}).get("url") or "http://localhost:8081"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{bot_api_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"status": "offline"}
    except Exception as e:
        logger.debug("Bot health check failed: %s", e)
        return {"status": "offline"}


# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
