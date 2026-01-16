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

from pathlib import Path
import xml.etree.ElementTree as ET

from db import (
    get_last_youtube_video,
    set_last_youtube_video,
    get_last_youtube_upcoming,
    set_last_youtube_upcoming,
    get_last_youtube_live,
    set_last_youtube_live,
)

logger = logging.getLogger(__name__)

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


class YouTubeNotifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._task_started = False
        self._session = None

    async def cog_load(self) -> None:
        cfg = getattr(self.bot, "config", {}).get("youtube") or {}
        if not cfg.get("enabled"):
            return
        if aiohttp and self._session is None:
            self._session = aiohttp.ClientSession()
        if not self._task_started:
            self.check_youtube.start()
            self._task_started = True

    def _announce_channel(self, guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
        if not guild:
            return None
        channel_id = (getattr(self.bot, "config", {}).get("youtube") or {}).get("announce_channel_id")
        if channel_id:
            ch = guild.get_channel(int(channel_id))
            return ch if isinstance(ch, discord.TextChannel) else None
        return None

    @tasks.loop(minutes=5.0)
    async def check_youtube(self) -> None:
        cfg = getattr(self.bot, "config", {}).get("youtube") or {}
        if not cfg.get("enabled"):
            return
        channel_ids: list[str] = cfg.get("channel_ids") or []
        interval = float(cfg.get("check_interval_minutes") or 5)
        if self.check_youtube.minutes != interval:
            self.check_youtube.change_interval(minutes=interval)
        if not channel_ids:
            return
        guild_id = getattr(self.bot, "config", {}).get("GUILD_ID")
        guild = self.bot.get_guild(int(guild_id)) if guild_id else None
        announce_channel = self._announce_channel(guild)
        if not announce_channel:
            return
        mention_role_id = cfg.get("mention_role_id")
        mention_prefix = f"<@&{int(mention_role_id)}> " if mention_role_id else ""
        api_key = cfg.get("api_key")

        for cid in channel_ids:
            try:
                latest = await self._fetch_latest_youtube_video_id(cid)
                if not latest:
                    continue
                last_seen = get_last_youtube_video(cid)
                if last_seen == latest:
                    continue
                set_last_youtube_video(cid, latest)
                video_url = f"https://www.youtube.com/watch?v={latest}"
                await announce_channel.send(f"{mention_prefix}New YouTube upload: {video_url}")
            except Exception as exc:  # noqa: BLE001
                logger.exception("YouTube check failed for %s: %s", cid, exc)
                continue

            # Waiting room (upcoming live) detection via Data API
            try:
                if api_key:
                    upcoming_ids = await self._fetch_youtube_event_ids(cid, api_key, event_type="upcoming")
                    upcoming_id = upcoming_ids[0] if upcoming_ids else None
                    if upcoming_id and get_last_youtube_upcoming(cid) != upcoming_id:
                        set_last_youtube_upcoming(cid, upcoming_id)
                        details = await self._fetch_live_details([upcoming_id], api_key)
                        scheduled = details.get(upcoming_id, {}).get("scheduledStartTime")
                        msg = f"{mention_prefix}YouTube waiting room created: https://www.youtube.com/watch?v={upcoming_id}"
                        if scheduled:
                            msg += f" — starts at {scheduled}"
                        await announce_channel.send(msg)
            except Exception as exc:  # noqa: BLE001
                logger.exception("YouTube upcoming check failed for %s: %s", cid, exc)

            # Live now detection via Data API
            try:
                if api_key:
                    live_ids = await self._fetch_youtube_event_ids(cid, api_key, event_type="live")
                    live_id = live_ids[0] if live_ids else None
                    if live_id and get_last_youtube_live(cid) != live_id:
                        set_last_youtube_live(cid, live_id)
                        await announce_channel.send(
                            f"{mention_prefix}YouTube is LIVE now: https://www.youtube.com/watch?v={live_id}"
                        )
            except Exception as exc:  # noqa: BLE001
                logger.exception("YouTube live check failed for %s: %s", cid, exc)

    async def _fetch_latest_youtube_video_id(self, channel_id: str) -> Optional[str]:
        url = YOUTUBE_FEED_URL.format(channel_id=channel_id)
        text: Optional[str] = None
        if aiohttp and self._session:
            to = aiohttp.ClientTimeout(total=20)
            async with self._session.get(url, timeout=to) as resp:
                    if resp.status != 200:
                        return None
                    text = await resp.text()
        else:
            loop = asyncio.get_running_loop()
            import urllib.request
            def _fetch() -> str:
                with urllib.request.urlopen(url, timeout=20) as r:  # nosec B310
                    return r.read().decode("utf-8", "replace")
            text = await loop.run_in_executor(None, _fetch)
        if not text:
            return None
        try:
            root = ET.fromstring(text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015",
            }
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None
            vid = entry.find("yt:videoId", ns)
            if vid is not None and vid.text:
                return vid.text.strip()
            link = entry.find("atom:link", ns)
            if link is not None and link.get("href"):
                href = link.get("href")
                if href and "v=" in href:
                    return href.split("v=")[-1]
        except ET.ParseError:
            return None
        return None

    async def _fetch_youtube_event_ids(self, channel_id: str, api_key: str, event_type: str) -> list[str]:
        """Use YouTube Data API search.list to get video IDs for upcoming/live events."""
        base = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&channelId={channel_id}&type=video&eventType={event_type}&order=date&maxResults=5&key={api_key}"
        )
        text: Optional[str] = None
        if aiohttp and self._session:
            to = aiohttp.ClientTimeout(total=20)
            async with self._session.get(base, timeout=to) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()
        else:
            loop = asyncio.get_running_loop()
            import urllib.request
            def _fetch() -> str:
                with urllib.request.urlopen(base, timeout=20) as r:  # nosec B310
                    return r.read().decode("utf-8", "replace")
            text = await loop.run_in_executor(None, _fetch)
        if not text:
            return []
        import json
        try:
            data = json.loads(text)
            items = data.get("items") or []
            ids = []
            for it in items:
                idobj = it.get("id") or {}
                vid = idobj.get("videoId")
                if vid:
                    ids.append(vid)
            return ids
        except Exception:  # noqa: BLE001
            return []

    async def _fetch_live_details(self, video_ids: list[str], api_key: str) -> dict[str, dict]:
        if not video_ids:
            return {}
        ids_param = ",".join(video_ids)
        url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=liveStreamingDetails,snippet&id={ids_param}&key={api_key}"
        )
        text: Optional[str] = None
        if aiohttp and self._session:
            to = aiohttp.ClientTimeout(total=20)
            async with self._session.get(url, timeout=to) as resp:
                    if resp.status != 200:
                        return {}
                    text = await resp.text()
        else:
            loop = asyncio.get_running_loop()
            import urllib.request
            def _fetch() -> str:
                with urllib.request.urlopen(url, timeout=20) as r:  # nosec B310
                    return r.read().decode("utf-8", "replace")
            text = await loop.run_in_executor(None, _fetch)
        if not text:
            return {}
        import json
        try:
            data = json.loads(text)
            out: dict[str, dict] = {}
            for it in data.get("items") or []:
                vid = it.get("id")
                live = (it.get("liveStreamingDetails") or {})
                out[str(vid)] = {
                    "scheduledStartTime": live.get("scheduledStartTime"),
                    "actualStartTime": live.get("actualStartTime"),
                }
            return out
        except Exception:  # noqa: BLE001
            return {}

    @check_youtube.before_loop
    async def before_check(self) -> None:
        await self.bot.wait_until_ready()

    async def cog_unload(self) -> None:
        try:
            if self._task_started:
                self.check_youtube.cancel()
                self._task_started = False
            if self._session:
                await self._session.close()
                self._session = None
        except Exception:  # noqa: BLE001
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YouTubeNotifyCog(bot))
