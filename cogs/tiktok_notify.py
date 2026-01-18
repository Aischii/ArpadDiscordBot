from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands, tasks

try:
    import aiohttp
except Exception:  # noqa: BLE001
    aiohttp = None  # type: ignore

import xml.etree.ElementTree as ET

from db import (
    get_last_tiktok_item,
    set_last_tiktok_item,
    get_tiktok_live_state,
    set_tiktok_live_state,
)

logger = logging.getLogger(__name__)


class TikTokNotifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._task_started = False
        self._session = None

    async def cog_load(self) -> None:
        cfg = getattr(self.bot, "config", {}).get("tiktok") or {}
        if not cfg.get("enabled"):
            return
        if aiohttp and self._session is None:
            self._session = aiohttp.ClientSession(headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            })
        if not self._task_started:
            self.check_tiktok.start()
            self._task_started = True

    def _announce_channel(self, guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
        if not guild:
            return None
        channel_id = (getattr(self.bot, "config", {}).get("tiktok") or {}).get("announce_channel_id")
        if channel_id:
            ch = guild.get_channel(int(channel_id))
            return ch if isinstance(ch, discord.TextChannel) else None
        return None

    @tasks.loop(minutes=10.0)
    async def check_tiktok(self) -> None:
        cfg = getattr(self.bot, "config", {}).get("tiktok") or {}
        if not cfg.get("enabled"):
            return
        accounts: list[dict] = cfg.get("accounts") or []
        interval = float(cfg.get("check_interval_minutes") or 10)
        if self.check_tiktok.minutes != interval:
            self.check_tiktok.change_interval(minutes=interval)
        if not accounts:
            return
        guild_id = getattr(self.bot, "config", {}).get("GUILD_ID")
        guild = self.bot.get_guild(int(guild_id)) if guild_id else None
        announce_channel = self._announce_channel(guild)
        if not announce_channel:
            return
        mention_role_id = cfg.get("mention_role_id")
        mention_prefix = f"<@&{int(mention_role_id)}> " if mention_role_id else ""

        for acc in accounts:
            rss_url = acc.get("rss_url")
            display_name = acc.get("display_name") or "TikTok"
            username = acc.get("username")
            if not rss_url:
                continue
            try:
                latest_id, latest_link = await self._fetch_latest_item_from_rss(rss_url)
                if not latest_id:
                    continue
                last_seen = get_last_tiktok_item(rss_url)
                if last_seen == latest_id:
                    continue
                set_last_tiktok_item(rss_url, latest_id)
                await self._send_tiktok_embed(
                    announce_channel,
                    "tiktok_notification_newpost",
                    {
                        "{{creator_name}}": display_name,
                        "{{post_url}}": latest_link or ""
                    },
                    mention_prefix
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("TikTok check failed for %s: %s", rss_url, exc)
                continue

            # Live detection (best-effort) by checking @username/live page
            try:
                if username:
                    live = await self._is_tiktok_live(username)
                    prev = get_tiktok_live_state(username)
                    if live and not prev:
                        set_tiktok_live_state(username, True)
                        await self._send_tiktok_embed(
                            announce_channel,
                            "tiktok_notification_live",
                            {
                                "{{creator_name}}": display_name,
                                "{{live_url}}": f"https://www.tiktok.com/@{username}/live"
                            },
                            mention_prefix
                        )
                    elif live is False and prev:
                        set_tiktok_live_state(username, False)
            except Exception as exc:  # noqa: BLE001
                logger.exception("TikTok live check failed for %s: %s", username, exc)

    async def _fetch_latest_item_from_rss(self, rss_url: str) -> tuple[Optional[str], Optional[str]]:
        text: Optional[str] = None
        if aiohttp and self._session:
            to = aiohttp.ClientTimeout(total=20)
            async with self._session.get(rss_url, timeout=to) as resp:
                    if resp.status != 200:
                        return None, None
                    text = await resp.text()
        else:
            loop = asyncio.get_running_loop()
            import urllib.request
            def _fetch() -> str:
                with urllib.request.urlopen(rss_url, timeout=20) as r:  # nosec B310
                    return r.read().decode("utf-8", "replace")
            text = await loop.run_in_executor(None, _fetch)
        if not text:
            return None, None
        try:
            root = ET.fromstring(text)
            channel = root.find("channel")
            if channel is None:
                return None, None
            item = channel.find("item")
            if item is None:
                return None, None
            guid = item.findtext("guid")
            link = item.findtext("link")
            if guid:
                return guid.strip(), (link.strip() if link else None)
        except ET.ParseError:
            return None, None
        return None, None

    async def _is_tiktok_live(self, username: str) -> Optional[bool]:
        url = f"https://www.tiktok.com/@{username}/live"
        text: Optional[str] = None
        if aiohttp and self._session:
            to = aiohttp.ClientTimeout(total=20)
            async with self._session.get(url, timeout=to, allow_redirects=True) as resp:
                    if resp.status not in (200, 302):
                        return None
                    text = await resp.text()
        else:
            loop = asyncio.get_running_loop()
            import urllib.request
            def _fetch() -> str:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                })
                with urllib.request.urlopen(req, timeout=20) as r:  # nosec B310
                    return r.read().decode("utf-8", "replace")
            text = await loop.run_in_executor(None, _fetch)
        if not text:
            return None
        lowered = text.lower()
        # Heuristics: presence of isLive:true or live badge
        if "islive\":true" in lowered or "\"islive\":true" in lowered:
            return True
        if ">live<" in lowered or "live now" in lowered:
            return True
        return False

    @check_tiktok.before_loop
    async def before_check(self) -> None:
        await self.bot.wait_until_ready()

    async def cog_unload(self) -> None:
        try:
            if self._task_started:
                self.check_tiktok.cancel()
                self._task_started = False
            if self._session:
                await self._session.close()
                self._session = None
        except Exception:  # noqa: BLE001
            pass

    async def _send_tiktok_embed(self, channel: discord.TextChannel, template_name: str,
                                  replacements: dict, mention_prefix: str) -> None:
        """Send a TikTok notification using embed template or fallback to text."""
        from bot import load_embed_template
        
        template = load_embed_template(template_name, replacements)
        
        if template:
            try:
                color_str = template.get("color", "#000000")
                if isinstance(color_str, str) and color_str.startswith("#"):
                    color_int = int(color_str[1:], 16)
                else:
                    color_int = int(color_str) if isinstance(color_str, int) else 0
                
                embed = discord.Embed(
                    title=template.get("title", "TikTok Notification"),
                    description=template.get("description", ""),
                    color=color_int
                )
                
                for field in template.get("fields", []):
                    embed.add_field(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        inline=field.get("inline", False)
                    )
                
                footer_data = template.get("footer")
                if footer_data:
                    embed.set_footer(text=footer_data.get("text", ""))
                
                thumbnail = template.get("thumbnail")
                if thumbnail and isinstance(thumbnail, dict) and thumbnail.get("url"):
                    embed.set_thumbnail(url=thumbnail.get("url"))
                
                await channel.send(mention_prefix.strip() and f"{mention_prefix}", embed=embed)
                return
            except Exception as exc:
                logger.warning("Failed to send TikTok embed for %s: %s, falling back to text", template_name, exc)
        
        # Fallback: send basic text notification
        default_msg = {
            "tiktok_notification_newpost": "New TikTok post",
            "tiktok_notification_scheduled": "TikTok live scheduled",
            "tiktok_notification_live": "TikTok is LIVE now"
        }.get(template_name, "TikTok notification")
        
        await channel.send(f"{mention_prefix}{default_msg}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TikTokNotifyCog(bot))
