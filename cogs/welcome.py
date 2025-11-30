from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import aiohttp
import discord
from discord.ext import commands

# Switch between "json" to load a Discohook-like payload from welcome_embed.json
# or "embed" to use the Python-built embed below.
TEMPLATE_MODE = "json"
WELCOME_TEMPLATE_PATH = Path("welcome_embed.json")

logger = logging.getLogger(__name__)


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild_id = self.bot.config.get("GUILD_ID")
        if guild_id and member.guild.id != guild_id:
            return

        webhook_url = self.bot.config.get("WELCOME_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("WELCOME_WEBHOOK_URL is not configured.")
            return

        try:
            await self._send_welcome_webhook(member, webhook_url)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to send welcome webhook: %s", exc)

    async def _send_welcome_webhook(self, member: discord.Member, webhook_url: str) -> None:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            if TEMPLATE_MODE.lower() == "json":
                payload = self._load_template_payload(member)
                embeds_data = payload.get("embeds", [])
                embeds = [discord.Embed.from_dict(embed) for embed in embeds_data]
                await webhook.send(
                    content=payload.get("content"),
                    username=payload.get("username"),
                    avatar_url=payload.get("avatar_url"),
                    embeds=embeds,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            else:
                embed = self._build_embed(member)
                await webhook.send(
                    content=f"Welcome, {member.mention}!",
                    embeds=[embed],
                    allowed_mentions=discord.AllowedMentions(users=True),
                )

    def _load_template_payload(self, member: discord.Member) -> Dict[str, Any]:
        if not WELCOME_TEMPLATE_PATH.exists():
            logger.warning("Template mode enabled but %s is missing. Falling back to embed mode.", WELCOME_TEMPLATE_PATH)
            return {
                "content": f"Welcome, {member.mention}!",
                "embeds": [self._build_embed(member).to_dict()],
            }

        raw = WELCOME_TEMPLATE_PATH.read_text(encoding="utf-8")
        replacements = {
            "{{user_mention}}": member.mention,
            "{{user_name}}": member.name,
            "{{user_discriminator}}": member.discriminator,
            "{{user_id}}": str(member.id),
        }
        for placeholder, value in replacements.items():
            raw = raw.replace(placeholder, value)

        data = json.loads(raw)
        if "embeds" in data and isinstance(data["embeds"], list):
            return data

        # Minimal fallback if template structure is unexpected.
        return {
            "content": data.get("content") or f"Welcome, {member.mention}!",
            "embeds": [data] if isinstance(data, dict) else [],
        }

    def _build_embed(self, member: discord.Member) -> discord.Embed:
        embed = discord.Embed(
            title="Welcome To Midnight Au Lait, Sleepy Visitor!",  # Change this title to match your server's vibe.
            description=(
                f"Glad to have you here, {member.mention}.\n"
                "Feel free to grab a seat, browse the channels, and say hello!\n\n"
                "Be sure to read the rules in <#RULES_CHANNEL_ID> so you know the lay of the land."  # Replace RULES_CHANNEL_ID.
            ),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url="https://example.com/small-icon.png")  # Replace with your small icon URL.
        embed.set_image(url="https://example.com/large-welcome-image.png")  # Replace with your large welcome card art.
        embed.set_footer(text="Welcome to the community!")
        return embed

    @commands.command(name="testwelcome")
    @commands.has_permissions(manage_guild=True)
    async def test_welcome(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        """
        Manually trigger the welcome webhook for testing.
        Defaults to the caller if no member is provided.
        """
        target = member or ctx.author
        guild_id = self.bot.config.get("GUILD_ID")
        if guild_id and ctx.guild and ctx.guild.id != guild_id:
            await ctx.send("This command only works in the configured guild.")
            return

        webhook_url = self.bot.config.get("WELCOME_WEBHOOK_URL")
        if not webhook_url:
            await ctx.send("WELCOME_WEBHOOK_URL is not configured.")
            return

        await self._send_welcome_webhook(target, webhook_url)
        await ctx.send(f"Sent welcome webhook for {target.mention}.", allowed_mentions=discord.AllowedMentions(users=True))

    @test_welcome.error
    async def test_welcome_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need Manage Server permission to run this.")
        else:
            await ctx.send(f"Error: {error}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
