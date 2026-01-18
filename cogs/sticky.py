from __future__ import annotations

import logging
from typing import List, Optional, Any, Dict

import discord
from discord.ext import commands

import db

logger = logging.getLogger(__name__)


class StickyCog(commands.Cog):
    """
    Maintains a sticky message at the bottom of configured channels.
    When users chat, the previous sticky is deleted and re-posted.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        sticky_cfg: Dict[str, Any] = bot.config.get("sticky", {})
        self.enabled: bool = sticky_cfg.get("enabled", False)
        self.channel_configs: Dict[int, List[str]] = {
            int(item["channel_id"]): item.get("message", [])
            for item in sticky_cfg.get("channels", [])
            if "channel_id" in item
        }

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.enabled:
            return
        # Ensure each configured channel has a sticky message recorded/sent.
        for channel_id, lines in self.channel_configs.items():
            if db.get_sticky_message_id(channel_id):
                continue
            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            await self._post_sticky(channel, lines)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not self.enabled or message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        if channel_id not in self.channel_configs:
            return

        # Ignore the bot's own sticky messages to prevent loops.
        if self.bot.user and message.author.id == self.bot.user.id:
            return

        lines = self.channel_configs[channel_id]
        await self._refresh_sticky(message.channel, lines)

    @commands.command(name="stickynow")
    @commands.has_permissions(manage_messages=True)
    async def stickynow(self, ctx: commands.Context) -> None:
        """Force re-post of the sticky message in this channel."""
        if not self.enabled:
            await ctx.send("Sticky system is disabled in config.")
            return
        channel_id = ctx.channel.id
        if channel_id not in self.channel_configs:
            await ctx.send("This channel is not configured for sticky messages.")
            return
        lines = self.channel_configs[channel_id]
        await self._refresh_sticky(ctx.channel, lines)
        await ctx.send("Sticky message refreshed.", delete_after=5)

    @stickynow.error
    async def stickynow_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need Manage Messages or Administrator permission to use this.")
        else:
            await ctx.send(f"Error: {error}")

    # ---------------- Helpers ---------------- #
    async def _refresh_sticky(self, channel: discord.TextChannel, lines: List[str]) -> None:
        """Delete previous sticky and send a new one."""
        previous_id = db.get_sticky_message_id(channel.id)
        if previous_id:
            try:
                old_msg = await channel.fetch_message(int(previous_id))
                await old_msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            except discord.HTTPException as exc:
                logger.warning("Failed to delete old sticky in %s: %s", channel.id, exc)

        await self._post_sticky(channel, lines)

    async def _post_sticky(self, channel: discord.TextChannel, lines: List[str]) -> None:
        from bot import load_embed_template
        
        # Try to load embed template first
        template = load_embed_template("sticky_message")
        
        if template:
            try:
                color_str = template.get("color", "#5865F2")
                if isinstance(color_str, str) and color_str.startswith("#"):
                    color_int = int(color_str[1:], 16)
                else:
                    color_int = int(color_str) if isinstance(color_str, int) else 5865522
                
                embed = discord.Embed(
                    title=template.get("title", "📌 Server Info"),
                    description=template.get("description", ""),
                    color=color_int
                )
                
                for field in template.get("fields", []):
                    embed.add_field(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        inline=field.get("inline", False)
                    )
                
                try:
                    sent = await channel.send(embed=embed)
                    db.set_sticky_message_id(channel.id, str(sent.id))
                    return
                except discord.Forbidden:
                    logger.warning("Missing permissions to post sticky embed in %s", channel.id)
                    return
                except discord.HTTPException as exc:
                    logger.error("Failed to post sticky embed in %s: %s", channel.id, exc)
            except Exception as exc:
                logger.warning("Failed to use sticky embed template: %s, falling back to text", exc)
        
        # Fallback to text-based sticky message
        content = "\n".join(lines)
        try:
            sent = await channel.send(content)
        except discord.Forbidden:
            logger.warning("Missing permissions to post sticky in %s", channel.id)
            return
        except discord.HTTPException as exc:
            logger.error("Failed to post sticky in %s: %s", channel.id, exc)
            return

        db.set_sticky_message_id(channel.id, str(sent.id))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StickyCog(bot))
