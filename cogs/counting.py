from __future__ import annotations

import logging
import math
from typing import Optional, Set, Dict, Any

import discord
from discord.ext import commands

import db
import xp_utils

logger = logging.getLogger(__name__)


class CountingCog(commands.Cog):
    """
    Simple counting game.
    - Only active in the configured counting channel.
    - Tracks current number and participants in-memory.
    - Success grants XP to all participants.
    - Mistakes apply XP/level penalties.
    - Tracks counting milestones.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.xp_config: Dict[str, Any] = bot.config.get("xp", {})
        self.milestone_config: Dict[str, Any] = bot.config.get("milestones", {})

        counting_cfg = self.xp_config.get("counting", {})
        self.enabled = counting_cfg.get("enabled", True)
        self.channel_id: Optional[int] = counting_cfg.get("channel_id")
        self.target: int = int(counting_cfg.get("target", 100))

        self.current_value: int = 0  # Expect next number to be current_value + 1 (starts at 1 after reset).
        self.last_user_id: Optional[int] = None
        self.participants: Set[int] = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not self.enabled or message.author.bot or not message.guild:
            return
        if not self.channel_id or message.channel.id != self.channel_id:
            return

        counting_cfg = self.xp_config.get("counting", {})
        if not counting_cfg.get("enabled", True):
            return

        expected = self.current_value + 1 if self.current_value >= 1 else 1
        try:
            value = int(message.content.strip())
        except ValueError:
            await self._handle_break(message.author, message.channel, message.content, expected)
            return

        if value <= 0:
            await self._handle_break(message.author, message.channel, value, expected)
            return

        if value != expected:
            await self._handle_break(message.author, message.channel, value, expected)
            return

        if self.last_user_id == message.author.id:
            await self._handle_break(message.author, message.channel, value, expected)
            return

        # Correct number.
        await message.add_reaction("✅")
        self.current_value = value
        self.last_user_id = message.author.id
        self.participants.add(message.author.id)

        if self.current_value >= self.target:
            await self._handle_success_round(message.channel)

    # ------------------ Helpers ------------------ #
    def _reset_round(self) -> None:
        self.current_value = 0
        self.last_user_id = None
        self.participants.clear()

    async def _handle_success_round(self, channel: discord.TextChannel) -> None:
        success_xp = xp_utils.get_counting_success_xp(self.xp_config)

        leveling_cog = self.bot.get_cog("LevelingCog")
        guild = channel.guild

        awarded = 0
        for user_id in list(self.participants):
            member = guild.get_member(user_id)
            if not member:
                continue
            if success_xp > 0 and leveling_cog and hasattr(leveling_cog, "apply_xp"):
                await leveling_cog.apply_xp(member, success_xp, source_channel=channel)  # type: ignore[attr-defined]
            elif success_xp > 0:
                db.add_xp(user_id, success_xp)
            total_rounds = db.increment_counting_rounds(user_id)
            await self._check_counting_milestones(member, total_rounds, channel)
            awarded += 1

        await channel.send(
            f"We reached {self.target}! Everyone who helped ({awarded} participants) gains XP.",
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        self._reset_round()

    async def _handle_break(self, user: discord.Member, channel: discord.TextChannel, wrong_number: Any, expected_number: int) -> None:
        counting_cfg = self.xp_config.get("counting", {})
        penalty_cfg = counting_cfg.get("penalty", {})
        xp_loss_pct = float(penalty_cfg.get("xp_loss_percent", 0))
        level_loss_pct = float(penalty_cfg.get("level_loss_percent", 0))

        user_data = db.get_user(user.id)
        current_xp = int(user_data.get("xp", 0))
        current_level = int(user_data.get("level", 0))

        xp_loss = math.floor(current_xp * (xp_loss_pct / 100.0))
        level_loss = math.floor(current_level * (level_loss_pct / 100.0))

        new_xp = max(0, current_xp - xp_loss)
        target_level = max(0, current_level - level_loss)
        computed_level = xp_utils.get_xp_level(self.xp_config, new_xp)
        new_level = min(target_level, computed_level)

        db.set_xp(user.id, new_xp)
        db.set_level(user.id, new_level)

        leveling_cog = self.bot.get_cog("LevelingCog")
        if leveling_cog and hasattr(leveling_cog, "update_member_level_roles"):
            try:
                await leveling_cog.update_member_level_roles(user, new_level)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to update roles after penalty for %s: %s", user, exc)

        await channel.send(
            f"{user.mention} broke the count at `{wrong_number}` (expected `{expected_number}`)! Next number is `1`. "
            f"Penalty applied: -{xp_loss_pct:.0f}% XP and -{level_loss_pct:.0f}% levels.",
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        self._reset_round()

    async def _check_counting_milestones(self, member: discord.Member, total_rounds: int, source_channel: discord.abc.Messageable) -> None:
        cfg = self.milestone_config.get("counting_rounds", {})
        if not cfg.get("enabled", False):
            return

        thresholds = sorted(int(t) for t in cfg.get("thresholds", []))
        reward_xp = int(cfg.get("reward_xp", 0))
        roles_map = cfg.get("reward_role_ids", {})

        previous = total_rounds - 1
        for threshold in thresholds:
            if previous < threshold <= total_rounds:
                if reward_xp > 0:
                    leveling_cog = self.bot.get_cog("LevelingCog")
                    if leveling_cog and hasattr(leveling_cog, "apply_xp"):
                        await leveling_cog.apply_xp(member, reward_xp, source_channel=source_channel)  # type: ignore[attr-defined]
                    else:
                        db.add_xp(member.id, reward_xp)
                role_id = roles_map.get(str(threshold))
                if role_id:
                    role = member.guild.get_role(int(role_id))
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason=f"Counting milestone {threshold}")
                        except discord.Forbidden:
                            logger.warning("Missing permissions to add counting milestone role to %s", member)
                embed = discord.Embed(
                    title="Counting Milestone!",
                    description=f"{member.mention} helped complete **{threshold}** rounds!",
                    color=discord.Color.purple(),
                )
                await source_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CountingCog(bot))
