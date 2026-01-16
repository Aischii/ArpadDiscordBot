from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Iterable, Any, List, Tuple

import discord
from discord.ext import commands, tasks

import db
import xp_utils

logger = logging.getLogger(__name__)


def format_hms(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.xp_config: Dict[str, Any] = bot.config.get("xp", {})
        self.milestone_config: Dict[str, Any] = bot.config.get("milestones", {})
        self.streak_config: Dict[str, Any] = bot.config.get("streaks", {})
        self.leaderboard_config: Dict[str, Any] = bot.config.get("leaderboards", {"page_size": 10})
        self.message_cooldown = int(self.xp_config.get("message", {}).get("cooldown_seconds", 60))
        self.voice_sessions: Dict[int, float] = {}  # user_id -> last timestamp
        self.voice_carry: Dict[int, float] = {}  # user_id -> leftover seconds for XP calculation
        self.voice_tick.start()

    def cog_unload(self) -> None:
        self.voice_tick.cancel()

    # ---------------------- Events ---------------------- #
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        config = self.bot.config
        guild_id = config.get("GUILD_ID")
        if guild_id and message.guild.id != guild_id:
            return

        counting_channel_id = self.xp_config.get("counting", {}).get("channel_id")
        if counting_channel_id and message.channel.id == counting_channel_id:
            return  # Counting messages are handled separately.

        if not self.xp_config.get("message", {}).get("enabled", True):
            return

        if self._is_channel_blocked(message.channel, config.get("NO_XP_CHANNEL_IDS", []), config.get("NO_XP_CATEGORY_IDS", [])):
            return

        user_data = db.get_user(message.author.id)
        now = int(time.time())
        if now - int(user_data.get("last_message_ts", 0)) < self.message_cooldown:
            return

        xp_gain = xp_utils.get_message_xp(self.xp_config, message)
        if xp_gain <= 0:
            return

        db.increment_messages(message.author.id)
        new_total_xp = db.add_xp(message.author.id, xp_gain)
        db.set_last_message_ts(message.author.id, now)

        total_messages = db.get_user(message.author.id).get("total_messages", 0)
        await self._check_message_milestones(message.author, total_messages, message.channel)
        await self._update_streak(message, now)
        await self._check_level_up(member=message.author, new_total_xp=new_total_xp, source_channel=message.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        if not self.xp_config.get("voice", {}).get("enabled", True):
            return

        config = self.bot.config
        guild_id = config.get("GUILD_ID")
        if guild_id and member.guild.id != guild_id:
            return

        # Finalize the previous session if leaving/moving.
        if before.channel and member.id in self.voice_sessions:
            await self._finalize_voice_session(member, before.channel)

        # Start tracking if the new channel is eligible.
        if self._voice_channel_eligible(
            after.channel,
            member.guild,
            config.get("NO_XP_CATEGORY_IDS", []),
            config.get("NO_XP_CHANNEL_IDS", []),
        ):
            self.voice_sessions[member.id] = time.time()
            self.voice_carry[member.id] = 0.0
        else:
            self.voice_sessions.pop(member.id, None)
            self.voice_carry.pop(member.id, None)

    # ---------------------- Commands ---------------------- #
    @commands.command(name="rank")
    async def rank(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        target = member or ctx.author
        data = db.get_user(target.id)
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=f"{target.display_name}'s Stats", icon_url=target.display_avatar.url if target.display_avatar else discord.Embed.Empty)
        embed.add_field(name="Level", value=data.get("level", 0), inline=True)
        embed.add_field(name="Total XP", value=data.get("xp", 0), inline=True)
        embed.add_field(name="Messages", value=data.get("total_messages", 0), inline=True)
        embed.add_field(
            name="Voice Time",
            value=format_hms(int(data.get("total_voice_seconds", 0))),
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command(name="setxp")
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        if amount < 0:
            await ctx.send("XP amount must be non-negative.")
            return

        db.get_user(member.id)
        new_total = db.set_xp(member.id, amount)
        new_level = xp_utils.get_xp_level(self.xp_config, new_total)
        db.set_level(member.id, new_level)
        await self.update_member_level_roles(member, new_level)
        await ctx.send(f"Set {member.mention}'s XP to {new_total} (Level {new_level}).", allowed_mentions=discord.AllowedMentions(users=True))

    @setxp.error
    async def setxp_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need administrator permissions to use this command.")
        else:
            await ctx.send(f"Error: {error}")

    # ---------------------- Leaderboards ---------------------- #
    @commands.command(name="topxp")
    async def top_xp(self, ctx: commands.Context) -> None:
        await self._send_leaderboard(ctx, "xp", "Top XP")

    @commands.command(name="topmessages")
    async def top_messages(self, ctx: commands.Context) -> None:
        await self._send_leaderboard(ctx, "total_messages", "Top Messages")

    @commands.command(name="topvoice")
    async def top_voice(self, ctx: commands.Context) -> None:
        await self._send_leaderboard(ctx, "total_voice_seconds", "Top Voice Time")

    @commands.command(name="topcounting")
    async def top_counting(self, ctx: commands.Context) -> None:
        await self._send_leaderboard(ctx, "counting_success_rounds", "Top Counting Rounds")

    # ---------------------- Voice loop ---------------------- #
    @tasks.loop(seconds=60)
    async def voice_tick(self) -> None:
        config = self.bot.config
        guild_id = config.get("GUILD_ID")
        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        blocked_categories = config.get("NO_XP_CATEGORY_IDS", [])
        blocked_channels = config.get("NO_XP_CHANNEL_IDS", [])
        voice_cfg = self.xp_config.get("voice", {})
        require_not_alone = voice_cfg.get("require_not_alone", False)
        to_remove: list[int] = []

        for user_id, last_ts in list(self.voice_sessions.items()):
            member = guild.get_member(user_id)
            if not member or not member.voice or not self._voice_channel_eligible(
                member.voice.channel,
                guild,
                blocked_categories,
                blocked_channels,
            ):
                to_remove.append(user_id)
                continue

            now = time.time()
            elapsed = now - last_ts
            if elapsed <= 0:
                continue

            carried = self.voice_carry.get(user_id, 0.0)
            total_for_xp = carried + elapsed
            remainder = total_for_xp % 60

            db.get_user(user_id)
            db.add_voice_time(user_id, int(elapsed))

            channel = member.voice.channel
            if require_not_alone and channel and len([m for m in channel.members if not m.bot]) <= 1:
                # No XP while alone; just move the anchor forward.
                self.voice_sessions[user_id] = now
                self.voice_carry[user_id] = remainder
                continue

            xp_gain = xp_utils.get_voice_xp(self.xp_config, total_for_xp)
            if xp_gain > 0:
                new_total_xp = db.add_xp(user_id, xp_gain)
                await self._check_level_up(member, new_total_xp, source_channel=None)

            self.voice_sessions[user_id] = now
            self.voice_carry[user_id] = remainder

        for user_id in to_remove:
            self.voice_sessions.pop(user_id, None)
            self.voice_carry.pop(user_id, None)

    @voice_tick.before_loop
    async def before_voice_tick(self) -> None:
        await self.bot.wait_until_ready()
        interval = max(10.0, float(self.xp_config.get("voice", {}).get("tick_seconds", 60)))
        self.voice_tick.change_interval(seconds=interval)

    # ---------------------- Helpers ---------------------- #
    def _is_channel_blocked(
        self,
        channel: discord.abc.GuildChannel,
        blocked_channels: Iterable[int],
        blocked_categories: Iterable[int],
    ) -> bool:
        if channel.id in blocked_channels:
            return True
        if getattr(channel, "category_id", None) in blocked_categories:
            return True
        return False

    # Ensure DB aware of new columns on startup.
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        db.get_user(self.bot.user.id if self.bot.user else 0)  # touches schema initialization

    def _voice_channel_eligible(
        self,
        channel: Optional[discord.VoiceChannel | discord.StageChannel],
        guild: discord.Guild,
        blocked_categories: Iterable[int],
        blocked_channels: Iterable[int],
    ) -> bool:
        if channel is None:
            return False
        if guild.afk_channel and channel.id == guild.afk_channel.id:
            return False
        if channel.id in blocked_channels:
            return False
        if channel.category_id in blocked_categories:
            return False
        return True

    async def _finalize_voice_session(self, member: discord.Member, channel: Optional[discord.VoiceChannel | discord.StageChannel]) -> None:
        start_ts = self.voice_sessions.get(member.id)
        if start_ts is None:
            return

        elapsed = max(0, time.time() - start_ts)
        self.voice_sessions.pop(member.id, None)
        carried = self.voice_carry.pop(member.id, 0.0)
        if elapsed <= 0:
            return

        voice_cfg = self.xp_config.get("voice", {})
        require_not_alone = voice_cfg.get("require_not_alone", False)
        if require_not_alone and channel and len([m for m in channel.members if not m.bot]) <= 1:
            # No XP when alone if configured.
            db.add_voice_time(member.id, int(elapsed))
            return

        total_for_xp = carried + elapsed
        db.get_user(member.id)
        db.add_voice_time(member.id, int(elapsed))
        xp_gain = xp_utils.get_voice_xp(self.xp_config, total_for_xp)
        if xp_gain > 0:
            new_total_xp = db.add_xp(member.id, xp_gain)
            await self._check_level_up(member, new_total_xp, source_channel=None)

    async def _check_level_up(
        self,
        member: discord.Member,
        new_total_xp: int,
        source_channel: Optional[discord.abc.Messageable] = None,
    ) -> None:
        user_data = db.get_user(member.id)
        current_level = int(user_data.get("level", 0))
        new_level = xp_utils.get_xp_level(self.xp_config, new_total_xp)
        if new_level <= current_level:
            return

        db.set_level(member.id, new_level)
        await self.update_member_level_roles(member, new_level)

        channel = self._level_up_channel(member.guild, source_channel)
        if not channel:
            return

        embed = discord.Embed(
            title="Level Up!",
            description=f"Kerennn, {member.mention} levelmu sekarang sudah naik ke level **{new_level}**!",
            color=discord.Color.yellow(),
        )
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    async def update_member_level_roles(self, member: discord.Member, new_level: int) -> None:
        role_map = self.bot.config.get("LEVEL_ROLE_MAP", {})
        if not role_map:
            return

        thresholds = sorted(((int(level_str), role_id) for level_str, role_id in role_map.items()), key=lambda x: x[0])
        eligible_roles = [role_id for level, role_id in thresholds if level <= new_level]
        target_role_id = eligible_roles[-1] if eligible_roles else None
        target_role = member.guild.get_role(target_role_id) if target_role_id else None

        roles_to_remove = [member.guild.get_role(role_id) for _lvl, role_id in thresholds if role_id != target_role_id]

        try:
            if target_role and target_role not in member.roles:
                await member.add_roles(target_role, reason="Level reward")
            for role in roles_to_remove:
                if role and role in member.roles and role != target_role:
                    await member.remove_roles(role, reason="Level role cleanup")
        except discord.Forbidden:
            logger.warning("Missing permissions to manage roles for %s", member)
        except discord.HTTPException as exc:
            logger.error("Failed to update roles for %s: %s", member, exc)

    def _level_up_channel(
        self,
        guild: discord.Guild,
        source_channel: Optional[discord.abc.Messageable],
    ) -> Optional[discord.abc.Messageable]:
        level_up_channel_id = self.bot.config.get("LEVEL_UP_CHANNEL_ID")
        if level_up_channel_id:
            channel = guild.get_channel(level_up_channel_id)
            if channel:
                return channel
        return source_channel or guild.system_channel

    # Public helper so other cogs (counting) can reuse leveling flow.
    async def apply_xp(self, member: discord.Member, xp_gain: int, source_channel: Optional[discord.abc.Messageable] = None) -> int:
        if xp_gain <= 0:
            return db.get_user(member.id).get("xp", 0)
        db.get_user(member.id)
        new_total_xp = db.add_xp(member.id, xp_gain)
        await self._check_level_up(member, new_total_xp, source_channel)
        return new_total_xp

    async def set_level_and_roles(self, member: discord.Member, level: int) -> None:
        db.set_level(member.id, level)
        await self.update_member_level_roles(member, level)

    # ---------------------- Milestones & Streaks ---------------------- #
    async def _check_message_milestones(self, member: discord.Member, total_messages: int, source_channel: discord.abc.Messageable) -> None:
        cfg = self.milestone_config.get("message_count", {})
        if not cfg.get("enabled", False):
            return

        thresholds: List[int] = sorted(int(t) for t in cfg.get("thresholds", []))
        reward_xp = int(cfg.get("reward_xp", 0))
        roles_map = cfg.get("reward_role_ids", {})

        user_data = db.get_user(member.id)
        previous_messages = int(user_data.get("total_messages", 0)) - 1  # Because we already incremented

        for threshold in thresholds:
            if previous_messages < threshold <= total_messages:
                if reward_xp > 0:
                    await self.apply_xp(member, reward_xp, source_channel)
                role_id = roles_map.get(str(threshold))
                if role_id:
                    role = member.guild.get_role(int(role_id))
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason=f"Message milestone {threshold}")
                        except discord.Forbidden:
                            logger.warning("Missing permissions to add milestone role to %s", member)
                embed = discord.Embed(
                    title="Message Milestone!",
                    description=f"{member.mention} hit **{threshold}** messages!",
                    color=discord.Color.blurple(),
                )
                await source_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))

    async def _update_streak(self, message: discord.Message, now_ts: int) -> None:
        if not self.streak_config.get("enabled", False):
            return

        reset_hours = int(self.streak_config.get("reset_if_inactive_hours", 24))
        today_str = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        user_data = db.get_user(message.author.id)
        previous_streak = int(user_data.get("current_streak_days", 0))
        streak = db.update_streak(message.author.id, today_str, reset_hours, last_message_ts=now_ts)

        target_days = int(self.streak_config.get("chat_streak_days", 0))
        # Notify only when crossing the target for the first time in a cycle.
        if target_days and previous_streak < target_days <= streak:
            reward_xp = int(self.streak_config.get("reward_xp", 0))
            reward_role = self.streak_config.get("reward_role_id")
            if reward_xp > 0:
                await self.apply_xp(message.author, reward_xp, message.channel)
            if reward_role:
                role = message.guild.get_role(int(reward_role))
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role, reason="Chat streak reward")
                    except discord.Forbidden:
                        logger.warning("Missing permissions to add streak role to %s", message.author)
            await message.channel.send(
                f"{message.author.mention} reached a {target_days}-day chat streak! 🎉",
                allowed_mentions=discord.AllowedMentions(users=True),
            )

    async def _send_leaderboard(self, ctx: commands.Context, column: str, title: str) -> None:
        page_size = int(self.leaderboard_config.get("page_size", 10))
        records = db.get_top_users_by(column, page_size)
        if not records:
            await ctx.send("No data yet.")
            return

        lines: List[str] = []
        for idx, (user_id, value) in enumerate(records, start=1):
            member = ctx.guild.get_member(int(user_id)) if ctx.guild else None
            name = member.display_name if member else f"User {user_id}"
            if column == "total_voice_seconds":
                display_val = format_hms(value)
            else:
                display_val = str(value)
            lines.append(f"`{idx}.` **{name}** - {display_val}")

        embed = discord.Embed(title=title, description="\n".join(lines), color=discord.Color.teal())
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LevelingCog(bot))
