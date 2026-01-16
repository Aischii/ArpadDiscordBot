from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands

import db

logger = logging.getLogger(__name__)


class NicknameCog(commands.Cog):
    """
    Nickname management cog.
    Only allows changes via the command with a per-user cooldown.
    Staff should remove the "Change Nickname" permission from normal roles so the bot is the only path.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict[str, Any] = bot.config.get("nicknames", {})
        self.enabled: bool = self.config.get("enabled", True)
        self.cooldown_days: int = int(self.config.get("cooldown_days", 14))
        self.max_length: int = int(self.config.get("max_length", 32))
        self.allow_reset: bool = bool(self.config.get("allow_reset_to_username", True))
        self.allowed_roles_bypass: List[int] = [int(r) for r in self.config.get("allowed_roles_to_bypass_cooldown", [])]
        self.command_name: str = self.config.get("command_name", "nick") or "nick"

    def cog_unload(self) -> None:
        pass

    # ---------------- Commands ---------------- #
    @commands.command(name="nick")
    async def nick(self, ctx: commands.Context, *, new_nick: Optional[str] = None) -> None:
        if not self.enabled:
            return

        if ctx.guild is None or ctx.author.bot:
            return

        member: discord.Member = ctx.author

        # Verify bot permissions.
        me = ctx.guild.me
        if me is None or not me.guild_permissions.manage_nicknames:
            await ctx.send("I need the Manage Nicknames permission to change names.")
            return
        if me.top_role <= member.top_role:
            await ctx.send("I cannot change your nickname due to role hierarchy.")
            return

        # Handle aliases if config command name differs.
        if self.command_name and self.command_name != "nick" and ctx.invoked_with != self.command_name:
            # Allow both default and configured name; not an error.
            pass

        target_nick: Optional[str] = None
        reset_keywords = {"reset", "default", "clear"}
        if new_nick is None or (self.allow_reset and new_nick.strip().lower() in reset_keywords):
            if not self.allow_reset:
                await ctx.send("Resetting nickname is not allowed.")
                return
            target_nick = None
        else:
            new_nick = new_nick.strip()
            if not new_nick:
                await ctx.send("Nickname cannot be empty.")
                return
            if len(new_nick) > self.max_length:
                await ctx.send(f"Nickname is too long (max {self.max_length} characters).")
                return
            target_nick = new_nick

        # Cooldown check.
        now = int(time.time())
        last_change = db.get_last_nick_change(member.id)
        cooldown_seconds = self.cooldown_days * 86400
        bypass = any(role.id in self.allowed_roles_bypass for role in member.roles)

        if not bypass and last_change:
            elapsed = now - last_change
            if elapsed < cooldown_seconds:
                remaining = cooldown_seconds - elapsed
                days = remaining // 86400
                hours = (remaining % 86400 + 3599) // 3600  # round up hours
                await ctx.send(
                    f"You changed your nickname recently. You can change it again in {int(days)} days and {int(hours)} hours."
                )
                return

        try:
            await member.edit(nick=target_nick, reason="Nickname changed via bot command")
        except discord.Forbidden:
            await ctx.send("I don't have permission to change your nickname.")
            return
        except discord.HTTPException as exc:
            logger.error("Failed to change nickname for %s: %s", member, exc)
            await ctx.send("Something went wrong while changing your nickname.")
            return

        db.set_last_nick_change(member.id, now)
        if target_nick is None:
            await ctx.send("Your nickname has been reset to your username.")
        else:
            await ctx.send(
                f"Your nickname has been changed to **{target_nick}**. You can change it again in {self.cooldown_days} days."
            )

    @commands.command(name="nickinfo")
    async def nickinfo(self, ctx: commands.Context) -> None:
        if not self.enabled:
            return
        if ctx.guild is None or ctx.author.bot:
            return

        now = int(time.time())
        last_change = db.get_last_nick_change(ctx.author.id)
        cooldown_seconds = self.cooldown_days * 86400
        elapsed = now - last_change if last_change else None
        if not last_change:
            await ctx.send("You have not changed your nickname yet.")
            return

        remaining = max(0, cooldown_seconds - (elapsed or 0))
        days = remaining // 86400
        hours = (remaining % 86400 + 3599) // 3600
        await ctx.send(
            f"Last nickname change: <t:{last_change}:R>. "
            f"Time until next change: {int(days)} days and {int(hours)} hours."
        )


async def setup(bot: commands.Bot) -> None:
    cog = NicknameCog(bot)
    await bot.add_cog(cog)
    # Add alias if command_name differs from default.
    if cog.command_name != "nick":
        cmd = bot.get_command("nick")
        if cmd and cog.command_name not in cmd.aliases:
            cmd.aliases.append(cog.command_name)
