from __future__ import annotations

import math
from typing import Any, Dict

import discord

MEDIA_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "webm", "mkv"}


def get_message_xp(xp_config: Dict[str, Any], message: discord.Message) -> int:
    message_cfg = xp_config.get("message", {})
    if not message_cfg.get("enabled", True):
        return 0

    xp_gain = int(message_cfg.get("base_xp", 0))

    attachment_cfg = message_cfg.get("attachment_bonus", {})
    if attachment_cfg.get("enabled", True) and message.attachments:
        if any(_looks_like_media(att.filename) for att in message.attachments):
            xp_gain += int(attachment_cfg.get("image_or_video_bonus", 0))

    length_cfg = message_cfg.get("length_bonus", {})
    if length_cfg.get("enabled", True):
        chars_per_bonus = max(1, int(length_cfg.get("chars_per_bonus_xp", 1)))
        max_bonus = int(length_cfg.get("max_bonus", 0))
        length_bonus = min(max_bonus, len(message.content) // chars_per_bonus)
        xp_gain += length_bonus

    return max(0, xp_gain)


def get_voice_xp(xp_config: Dict[str, Any], seconds_in_tick: float) -> int:
    voice_cfg = xp_config.get("voice", {})
    if not voice_cfg.get("enabled", True):
        return 0
    xp_per_minute = int(voice_cfg.get("xp_per_minute", 0))
    full_minutes = int(seconds_in_tick // 60)
    return max(0, full_minutes * xp_per_minute)


def get_counting_success_xp(xp_config: Dict[str, Any]) -> int:
    counting_cfg = xp_config.get("counting", {})
    if not counting_cfg.get("enabled", True):
        return 0
    return int(counting_cfg.get("success_xp_per_user", 0))


def apply_counting_powerup_multiplier(base_xp: int, active: bool) -> int:
    return base_xp * 2 if active else base_xp


def get_xp_level(xp_config: Dict[str, Any], xp: int) -> int:
    formula = xp_config.get("level_formula", {})
    formula_type = formula.get("type", "power")
    if formula_type == "power":
        power = float(formula.get("power", 0.25))
        return int(max(0, xp) ** power)
    # Default fallback
    return int(max(0, xp) ** 0.25)


def _looks_like_media(filename: str) -> bool:
    parts = filename.lower().rsplit(".", maxsplit=1)
    return len(parts) == 2 and parts[1] in MEDIA_EXTS
