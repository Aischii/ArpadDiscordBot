from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import discord
from discord.ext import commands, tasks

import db

logger = logging.getLogger(__name__)


class BirthdayCog(commands.Cog):
    """
    Birthday tracking:
    - Users set their birthday.
    - At the configured time, the bot grants a birthday role and announces.
    - Role is removed after the day passes.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict[str, Any] = bot.config.get("birthdays", {})
        self.enabled: bool = self.config.get("enabled", False)
        self.command_name: str = self.config.get("command_name", "birthday") or "birthday"
        self.announcement_channel_id: Optional[int] = self.config.get("announcement_channel_id")
        self.role_id: Optional[int] = self.config.get("role_id")
        self.announcement_message: str = self.config.get(
            "announcement_message",
            "Happy Birthday {mention}! 🎂",
        )
        self.check_time_utc: str = self.config.get("check_time_utc", "09:00")
        self.timezone_offset_hours: int = int(self.config.get("timezone_offset_hours", 7))  # default GMT+7
        self._last_run_date: Optional[str] = None
        self.birthday_check.start()

    def cog_unload(self) -> None:
        self.birthday_check.cancel()

    # ---------------- Commands ---------------- #
    @commands.command(name="birthday")
    async def birthday(self, ctx: commands.Context, date_str: Optional[str] = None) -> None:
        """
        Set or clear your birthday. Accepts MM-DD or MM-DD-YYYY. Use 'clear' to remove.
        """
        if not self.enabled or ctx.author.bot or ctx.guild is None:
            return

        if date_str is None:
            await ctx.send("Usage: !birthday MM-DD or !birthday MM-DD-YYYY. Use !birthday clear to remove.")
            return

        if date_str.lower() in {"clear", "remove", "delete"}:
            db.clear_birthday(ctx.author.id)
            await ctx.send("Your birthday has been cleared.")
            return

        parts = date_str.split("-")
        if len(parts) not in (2, 3):
            await ctx.send("Format should be MM-DD or MM-DD-YYYY.")
            return

        try:
            month = int(parts[0])
            day = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else None
        except ValueError:
            await ctx.send("Month and day must be numbers.")
            return

        if not (1 <= month <= 12) or not (1 <= day <= 31):
            await ctx.send("Month or day is out of range.")
            return

        db.set_birthday(ctx.author.id, month, day, year)
        await ctx.send(
            f"Birthday saved as {month:02d}-{day:02d}" + (f"-{year}" if year else "") + "."
        )

    # ---------------- Scheduler ---------------- #
    @tasks.loop(minutes=1)
    async def birthday_check(self) -> None:
        if not self.enabled:
            return
        if not self.bot.is_ready():
            return

        now_utc = datetime.now(tz=timezone.utc)
        local_tz = timezone(timedelta(hours=self.timezone_offset_hours))
        local_now = now_utc.astimezone(local_tz)
        today_str = local_now.strftime("%Y-%m-%d")

        # Run once per day at configured time.
        if self._last_run_date == today_str:
            return

        if not self._is_check_time(local_now):
            return

        guild_id = self.bot.config.get("GUILD_ID")
        if not guild_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        birthday_role = guild.get_role(self.role_id) if self.role_id else None
        announcement_channel = (
            guild.get_channel(self.announcement_channel_id) if self.announcement_channel_id else guild.system_channel
        )

        birthdays = db.list_birthdays()
        for bday in birthdays:
            user_id = int(bday["user_id"])
            month = int(bday["month"])
            day = int(bday["day"])
            last_granted_year = int(bday.get("last_granted_year", 0) or 0)

            member = guild.get_member(user_id)
            if not member:
                continue

            is_birthday_today = local_now.month == month and local_now.day == day
            if is_birthday_today and last_granted_year != local_now.year:
                if birthday_role and birthday_role not in member.roles:
                    await self._safe_add_role(member, birthday_role, "Birthday role grant")
                db.set_birthday_granted_year(user_id, local_now.year)
                if announcement_channel:
                    msg = self.announcement_message.replace("{mention}", member.mention)
                    await announcement_channel.send(msg, allowed_mentions=discord.AllowedMentions(users=True))
            elif not is_birthday_today and birthday_role and birthday_role in member.roles and last_granted_year == local_now.year:
                # Remove role after birthday passes.
                await self._safe_remove_role(member, birthday_role, "Birthday role removal")

        self._last_run_date = today_str

    @birthday_check.before_loop
    async def before_birthday_check(self) -> None:
        await self.bot.wait_until_ready()

    # ---------------- Helpers ---------------- #
    def _is_check_time(self, now: datetime) -> bool:
        try:
            hour_str, minute_str = self.check_time_utc.split(":")
            target_hour = int(hour_str)
            target_minute = int(minute_str)
        except Exception:
            target_hour, target_minute = 9, 0
        return now.hour == target_hour and now.minute == target_minute

    async def _safe_add_role(self, member: discord.Member, role: discord.Role, reason: str) -> None:
        me = member.guild.me
        if not me or role >= me.top_role or not me.guild_permissions.manage_roles:
            logger.warning("Cannot add birthday role to %s due to permissions/hierarchy.", member)
            return
        try:
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            logger.warning("Forbidden adding birthday role to %s", member)
        except discord.HTTPException as exc:
            logger.error("HTTP error adding birthday role to %s: %s", member, exc)

    async def _safe_remove_role(self, member: discord.Member, role: discord.Role, reason: str) -> None:
        try:
            await member.remove_roles(role, reason=reason)
        except discord.Forbidden:
            logger.warning("Forbidden removing birthday role from %s", member)
        except discord.HTTPException as exc:
            logger.error("HTTP error removing birthday role from %s: %s", member, exc)


async def setup(bot: commands.Bot) -> None:
    cog = BirthdayCog(bot)
    await bot.add_cog(cog)
    # alias support if command_name differs
    if cog.command_name != "birthday":
        cmd = bot.get_command("birthday")
        if cmd and cog.command_name not in cmd.aliases:
            cmd.aliases.append(cog.command_name)
