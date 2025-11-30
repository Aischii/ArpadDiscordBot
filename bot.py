import json
import logging
from pathlib import Path

import discord
from discord.ext import commands

# Configure logging early so cogs can use it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")

CONFIG_PATH = Path("config.json")


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
        # Leaderboard and other future cogs can be added here.

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        logger.error("Error in command %s: %s", context.command, exception)
        await context.send(f"An error occurred: {exception}")


def main() -> None:
    config = load_config()
    token = config.get("BOT_TOKEN")
    if not token or token == "PUT_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN is missing or still set to the placeholder.")

    bot = ArpadBot(config)
    bot.run(token)


if __name__ == "__main__":
    main()
