import json
import logging
from pathlib import Path
import os
import sys

import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import threading
import uvicorn

# Configure logging early so cogs can use it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")

CONFIG_PATH = Path("config.json")


# Create FastAPI app for bot control API
api_app = FastAPI(title="ArpadBot API")
_bot_instance = None  # Will hold reference to bot


def set_bot_instance(bot: commands.Bot) -> None:
    global _bot_instance
    _bot_instance = bot


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
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.json is missing. Copy config.example.json and fill in your values.")
    with CONFIG_PATH.open() as fp:
        return json.load(fp)


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
    
    # Start bot API server in a background thread (for restart & health checks)
    api_enabled = config.get("bot_api", {}).get("enabled", False)
    if api_enabled:
        api_port = config.get("bot_api", {}).get("port", 8081)
        def run_api():
            uvicorn.run(
                api_app,
                host="0.0.0.0",
                port=api_port,
                log_level="warning",
                access_log=False,
            )
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("Bot API started on port %d", api_port)
    
    # Start web dashboard in a background thread (optional)
    dashboard_enabled = config.get("dashboard", {}).get("enabled", False)
    if dashboard_enabled:
        dashboard_port = config.get("dashboard", {}).get("port", 8080)
        def run_dashboard():
            import dashboard
            uvicorn.run(
                dashboard.app,
                host="0.0.0.0",
                port=dashboard_port,
                log_level="warning",
                access_log=False,
            )
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        logger.info("Dashboard started on port %d", dashboard_port)
    
    bot.run(token)


if __name__ == "__main__":
    main()
