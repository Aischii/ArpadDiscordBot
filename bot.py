import json
import logging
from pathlib import Path
import os
import sys

import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import threading
import uvicorn

# Configure logging early so cogs can use it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")

CONFIG_PATH = Path("config.json")


# Create FastAPI app for combined bot control API + dashboard
api_app = FastAPI(title="ArpadBot")
_bot_instance = None  # Will hold reference to bot

# Add CORS middleware to allow requests from the frontend
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def set_bot_instance(bot: commands.Bot) -> None:
    global _bot_instance
    _bot_instance = bot


@api_app.get("/")
async def root():
    """Serve the lightweight dashboard built with plain HTML/JS (no Next.js build needed)."""
    tpl_path = Path("templates/index.html")
    if tpl_path.exists():
        return FileResponse(tpl_path, media_type="text/html")
    return {"error": "Dashboard not available"}


@api_app.get("/embed")
async def embed_page():
    """Serve the embed builder page (plain HTML/JS)."""
    tpl_path = Path("templates/embed.html")
    if tpl_path.exists():
        return FileResponse(tpl_path, media_type="text/html")
    return {"error": "Embed builder not available"}


@api_app.get("/api/health")
async def bot_health():
    """Check if bot is running."""
    if _bot_instance and _bot_instance.user:
        return {
            "status": "ok",
            "bot_name": _bot_instance.user.name,
            "bot_id": _bot_instance.user.id,
            "latency": _bot_instance.latency,
        }
    return {"status": "starting"}


@api_app.post("/api/restart")
async def restart_bot():
    """Restart the bot (platform will auto-restart the process)."""
    if not _bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    try:
        await _bot_instance.close()
        sys.exit(0)  # Exit cleanly; hosting platform auto-restarts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart failed: {e}")


def load_config() -> dict:
    """Load configuration with sensible fallbacks.

    Order of precedence:
    1) `config.json` file if present
    2) `CONFIG_JSON` environment variable containing JSON
    3) Defaults merged with `config.example.json` if present
    """
    # 1) Primary: config.json
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as fp:
            return json.load(fp)

    # 2) Env override: CONFIG_JSON
    env_cfg = os.environ.get("CONFIG_JSON")
    if env_cfg:
        try:
            logger.warning("CONFIG_JSON env detected; using environment-provided configuration")
            return json.loads(env_cfg)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse CONFIG_JSON env: %s", exc)

    # 3) Fallback: sensible defaults + merge example if available
    port = int(os.environ.get("PORT", "8000"))
    default_cfg: dict = {
        "dashboard": {"enabled": True, "port": port},
        "bot_api": {"enabled": True, "url": f"http://0.0.0.0:{port}"},
    }

    example_path = Path("config.example.json")
    if example_path.exists():
        try:
            with example_path.open() as fp:
                example = json.load(fp)
                # Merge example values on top of defaults (example may contain placeholders)
                default_cfg = {**default_cfg, **example}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read config.example.json: %s", exc)

    logger.warning("config.json not found; using defaults (port=%d) and environment values", port)
    return default_cfg


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w") as fp:
        json.dump(config, fp, indent=2)


@api_app.get("/api/config")
async def get_config():
    """Fetch current config."""
    return load_config()


@api_app.post("/api/config")
async def update_config(data: dict):
    """Update config and save to file."""
    try:
        save_config(data)
        logger.info("Config updated via dashboard")
        return {"status": "ok", "message": "Config saved successfully"}
    except Exception as e:
        logger.exception("Failed to save config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")


@api_app.get("/api/embed")
async def get_embed():
    """Fetch embeds - returns a structure with embed keys like youtube_notification, welcome_message, etc."""
    embed_path = Path("embeds.json")
    default_payload = {
        "welcome_message": {"title": "", "description": "", "color": "#5865F2", "fields": []},
        "youtube_notification": {"title": "", "description": "", "color": "#FF0000", "fields": []},
        "tiktok_notification": {"title": "", "description": "", "color": "#000000", "fields": []},
        "birthday_message": {"title": "", "description": "", "color": "#FFD700", "fields": []},
        "levelup_message": {"title": "", "description": "", "color": "#00FF00", "fields": []},
        "help_message": {"title": "", "description": "", "color": "#5865F2", "fields": []},
        "sticky_message": {"title": "", "description": "", "color": "#5865F2", "fields": []},
        "xp_level_message": {"title": "", "description": "", "color": "#00B8D9", "fields": []},
    }

    if not embed_path.exists():
        return default_payload
    
    try:
        with embed_path.open() as fp:
            data = json.load(fp)
            # If stored with templates, return them directly
            if isinstance(data, dict) and "_templates" in data:
                merged = {**default_payload, **data.get("_templates", {})}
                return merged
            # Convert from old format to new format if needed
            if "embeds" in data and isinstance(data["embeds"], list) and len(data["embeds"]) > 0:
                first_embed = data["embeds"][0]
                # Convert color from decimal to hex
                color_hex = f"#{first_embed.get('color', 5865522):06x}" if isinstance(first_embed.get('color'), int) else first_embed.get('color', '#5865F2')
                converted = {
                    "welcome_message": {
                        "title": first_embed.get("title", ""),
                        "description": first_embed.get("description", ""),
                        "color": color_hex,
                        "fields": first_embed.get("fields", []),
                        "image": first_embed.get("image"),
                        "thumbnail": first_embed.get("thumbnail"),
                        "footer": first_embed.get("footer"),
                        "author": first_embed.get("author"),
                    },
                }
                merged = {**default_payload, **converted}
                return merged
            merged = {**default_payload, **data} if isinstance(data, dict) else default_payload
            return merged
    except Exception as e:
        logger.error("Failed to load embed: %s", e)
        return default_payload


@api_app.post("/api/embed")
async def save_embed(data: dict):
    """Save embeds to embeds.json."""
    try:
        embed_path = Path("embeds.json")
        embeds_to_save: dict = {}

        # Convert welcome_message into webhook-style payload for the welcome feature
        if "welcome_message" in data and data["welcome_message"]:
            embed_data = data["welcome_message"]
            color = embed_data.get("color", "#5865F2")
            if isinstance(color, str) and color.startswith("#"):
                color = int(color[1:], 16)

            embeds_to_save = {
                "content": "Welcome, {{user_mention}}!",
                "username": "Árpád the Cat",
                "avatar_url": "",
                "embeds": [
                    {
                        "title": embed_data.get("title", ""),
                        "description": embed_data.get("description", ""),
                        "color": color,
                        "fields": embed_data.get("fields", []),
                        "image": embed_data.get("image"),
                        "thumbnail": embed_data.get("thumbnail"),
                        "footer": embed_data.get("footer"),
                        "author": embed_data.get("author"),
                    }
                ],
                "attachments": [],
            }

        # Persist all templates for the dashboard (including non-welcome embeds)
        embeds_to_save["_templates"] = data

        with embed_path.open("w") as fp:
            json.dump(embeds_to_save, fp, indent=2)
        logger.info("Embed saved via dashboard")
        return {"status": "ok", "message": "Embed saved successfully"}
    except Exception as e:
        logger.exception("Failed to save embed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")


class ArpadBot(commands.Bot):
    def __init__(self, config: dict) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True

        super().__init__(command_prefix="!", intents=intents)
        self.config = config

    async def setup_hook(self) -> None:
        # Load cogs during startup.
        await self.load_extension("cogs.welcome")
        await self.load_extension("cogs.leveling")
        await self.load_extension("cogs.counting")
        await self.load_extension("cogs.sticky")
        await self.load_extension("cogs.nickname")
        await self.load_extension("cogs.birthday")
        try:
            await self.load_extension("cogs.youtube_notify")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load YouTube cog: %s", exc)
        try:
            await self.load_extension("cogs.tiktok_notify")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load TikTok cog: %s", exc)
        # Leaderboard and other future cogs can be added here.

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        logger.error("Error in command %s: %s", context.command, exception)
        await context.send(f"An error occurred: {exception}")


def main() -> None:
    config = load_config()
    token = os.environ.get("BOT_TOKEN") or config.get("BOT_TOKEN")
    if not token or token == "PUT_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN is missing or still set to the placeholder.")

    bot = ArpadBot(config)
    set_bot_instance(bot)
    
    # Start combined web server (API + Dashboard) in a background thread
    api_enabled = config.get("bot_api", {}).get("enabled", False)
    dashboard_enabled = config.get("dashboard", {}).get("enabled", False)
    
    if api_enabled or dashboard_enabled:
        # Prefer env PORT (Azure sets this) else config value else 8000
        port = int(os.environ.get("PORT", str(config.get("dashboard", {}).get("port", 8000))))
        def run_server():
            uvicorn.run(
                api_app,
                host="0.0.0.0",
                port=port,
                log_level="warning",
                access_log=False,
            )
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("Server started on port %d (Dashboard + Bot API combined)", port)
    
    bot.run(token)


if __name__ == "__main__":
    main()
