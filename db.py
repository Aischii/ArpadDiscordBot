"""
SQLite helper utilities for the Discord bot.
Creates the required schema on import and exposes a few helper functions
for XP, leveling, and future economy expansion.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

DB_PATH = Path("data.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    DB_PATH.touch(exist_ok=True)
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_voice_seconds INTEGER DEFAULT 0,
                last_message_ts INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                counting_success_rounds INTEGER DEFAULT 0,
                current_streak_days INTEGER DEFAULT 0,
                last_active_day TEXT DEFAULT NULL
            )
            """
        )
        _ensure_columns(
            conn,
            {
                "counting_success_rounds": "INTEGER DEFAULT 0",
                "current_streak_days": "INTEGER DEFAULT 0",
                "last_active_day": "TEXT DEFAULT NULL",
                "last_nick_change_ts": "INTEGER DEFAULT 0",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sticky_messages (
                channel_id TEXT PRIMARY KEY,
                message_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id TEXT PRIMARY KEY,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                year INTEGER,
                last_granted_year INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_last (
                channel_id TEXT PRIMARY KEY,
                last_video_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tiktok_last (
                feed_key TEXT PRIMARY KEY,
                last_item_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_live_last (
                channel_id TEXT PRIMARY KEY,
                last_upcoming_id TEXT,
                last_live_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tiktok_live_state (
                username TEXT PRIMARY KEY,
                is_live INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()


def _ensure_columns(conn: sqlite3.Connection, columns: Dict[str, str]) -> None:
    cur = conn.execute("PRAGMA table_info(users)")
    existing = {row["name"] for row in cur.fetchall()}
    for col, ddl in columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")


_init_db()


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def get_user(user_id: int | str) -> Dict[str, Any]:
    """Fetch a user row, creating it with defaults if missing."""
    user_key = str(user_id)
    with _get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_key,))
        row = cur.fetchone()
        if row:
            return _row_to_dict(row)  # type: ignore
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_key,))
        conn.commit()
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_key,))
        return _row_to_dict(cur.fetchone())  # type: ignore


def add_xp(user_id: int | str, amount: int) -> int:
    """Add XP to a user and return the new total."""
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute(
            "UPDATE users SET xp = xp + ? WHERE user_id = ?",
            (int(amount), user_key),
        )
        conn.commit()
        cur = conn.execute("SELECT xp FROM users WHERE user_id = ?", (user_key,))
        row = cur.fetchone()
        return int(row["xp"]) if row else 0


def set_xp(user_id: int | str, amount: int) -> int:
    """Set XP directly and return the stored total."""
    user_key = str(user_id)
    amount = max(0, int(amount))
    with _get_connection() as conn:
        conn.execute("UPDATE users SET xp = ? WHERE user_id = ?", (amount, user_key))
        conn.commit()
        cur = conn.execute("SELECT xp FROM users WHERE user_id = ?", (user_key,))
        row = cur.fetchone()
        return int(row["xp"]) if row else 0


def set_level(user_id: int | str, level: int) -> None:
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute("UPDATE users SET level = ? WHERE user_id = ?", (int(level), user_key))
        conn.commit()


def increment_messages(user_id: int | str) -> None:
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute(
            "UPDATE users SET total_messages = total_messages + 1 WHERE user_id = ?",
            (user_key,),
        )
        conn.commit()


def add_voice_time(user_id: int | str, seconds: int) -> None:
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute(
            "UPDATE users SET total_voice_seconds = total_voice_seconds + ? WHERE user_id = ?",
            (int(seconds), user_key),
        )
        conn.commit()


def set_last_message_ts(user_id: int | str, timestamp: int) -> None:
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute("UPDATE users SET last_message_ts = ? WHERE user_id = ?", (int(timestamp), user_key))
        conn.commit()


def increment_counting_rounds(user_id: int | str) -> int:
    user_key = str(user_id)
    with _get_connection() as conn:
        conn.execute(
            "UPDATE users SET counting_success_rounds = counting_success_rounds + 1 WHERE user_id = ?",
            (user_key,),
        )
        conn.commit()
        cur = conn.execute("SELECT counting_success_rounds FROM users WHERE user_id = ?", (user_key,))
        row = cur.fetchone()
        return int(row["counting_success_rounds"]) if row else 0


def get_counting_rounds(user_id: int | str) -> int:
    user_key = str(user_id)
    with _get_connection() as conn:
        cur = conn.execute("SELECT counting_success_rounds FROM users WHERE user_id = ?", (user_key,))
        row = cur.fetchone()
        return int(row["counting_success_rounds"]) if row else 0


def update_streak(user_id: int | str, today_date_str: str, reset_if_inactive_hours: int, last_message_ts: int | None = None) -> int:
    """
    Update streak based on the provided date string (YYYY-MM-DD).
    reset_if_inactive_hours: if the gap between messages exceeds this many hours, streak resets.
    last_message_ts: optional unix ts of the current message; if provided, uses difference in hours vs stored last_message_ts.
    """
    user_key = str(user_id)
    with _get_connection() as conn:
        cur = conn.execute(
            "SELECT current_streak_days, last_active_day, last_message_ts FROM users WHERE user_id = ?",
            (user_key,),
        )
        row = cur.fetchone()
        current_streak = int(row["current_streak_days"]) if row else 0
        last_active_day = row["last_active_day"] if row else None
        last_ts = int(row["last_message_ts"]) if row and row["last_message_ts"] is not None else None

        # Inactivity reset based on hours.
        if reset_if_inactive_hours and last_ts and last_message_ts:
            hours_since_last = (last_message_ts - last_ts) / 3600
            if hours_since_last > reset_if_inactive_hours:
                current_streak = 0

        if last_active_day is None:
            current_streak = 1
        elif today_date_str == last_active_day:
            pass  # same day, no change
        else:
            # Simple date diff: assume YYYY-MM-DD, compare string to detect next-day.
            from datetime import datetime, timedelta

            try:
                last_date = datetime.strptime(last_active_day, "%Y-%m-%d").date()
                today = datetime.strptime(today_date_str, "%Y-%m-%d").date()
                delta_days = (today - last_date).days
                if delta_days == 1:
                    current_streak += 1
                else:
                    current_streak = 1
            except ValueError:
                current_streak = 1

        conn.execute(
            "UPDATE users SET current_streak_days = ?, last_active_day = ? WHERE user_id = ?",
            (current_streak, today_date_str, user_key),
        )
        conn.commit()
        return current_streak


def get_top_users_by(column_name: str, limit: int) -> list[tuple[str, int]]:
    allowed = {"xp", "total_messages", "total_voice_seconds", "counting_success_rounds"}
    if column_name not in allowed:
        raise ValueError(f"Column {column_name} not allowed for leaderboard.")
    limit = max(1, min(limit, 100))
    with _get_connection() as conn:
        cur = conn.execute(
            f"SELECT user_id, {column_name} as value FROM users ORDER BY {column_name} DESC LIMIT ?",
            (limit,),
        )
        return [(row["user_id"], int(row["value"])) for row in cur.fetchall()]


# ---------------- Sticky helpers ---------------- #
def get_sticky_message_id(channel_id: int | str) -> Optional[str]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT message_id FROM sticky_messages WHERE channel_id = ?", (str(channel_id),))
        row = cur.fetchone()
        return row["message_id"] if row else None


def set_sticky_message_id(channel_id: int | str, message_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sticky_messages (channel_id, message_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET message_id = excluded.message_id
            """,
            (str(channel_id), message_id),
        )
        conn.commit()


def clear_sticky_message_id(channel_id: int | str) -> None:
    with _get_connection() as conn:
        conn.execute("DELETE FROM sticky_messages WHERE channel_id = ?", (str(channel_id),))
        conn.commit()


# ---------------- Nickname helpers ---------------- #
def get_last_nick_change(user_id: int | str) -> int:
    with _get_connection() as conn:
        cur = conn.execute("SELECT last_nick_change_ts FROM users WHERE user_id = ?", (str(user_id),))
        row = cur.fetchone()
        return int(row["last_nick_change_ts"]) if row else 0


def set_last_nick_change(user_id: int | str, ts: int) -> None:
    with _get_connection() as conn:
        conn.execute("UPDATE users SET last_nick_change_ts = ? WHERE user_id = ?", (int(ts), str(user_id)))
        conn.commit()


# ---------------- Birthday helpers ---------------- #
def set_birthday(user_id: int | str, month: int, day: int, year: Optional[int]) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO birthdays (user_id, month, day, year, last_granted_year)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                month=excluded.month,
                day=excluded.day,
                year=excluded.year,
                last_granted_year=0
            """,
            (str(user_id), month, day, year),
        )
        conn.commit()


def clear_birthday(user_id: int | str) -> None:
    with _get_connection() as conn:
        conn.execute("DELETE FROM birthdays WHERE user_id = ?", (str(user_id),))
        conn.commit()


def get_birthday(user_id: int | str) -> Optional[Dict[str, Any]]:
    with _get_connection() as conn:
        cur = conn.execute(
            "SELECT user_id, month, day, year, last_granted_year FROM birthdays WHERE user_id = ?",
            (str(user_id),),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def list_birthdays() -> list[Dict[str, Any]]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT user_id, month, day, year, last_granted_year FROM birthdays")
        return [_row_to_dict(row) for row in cur.fetchall()]


def set_birthday_granted_year(user_id: int | str, year: int) -> None:
    with _get_connection() as conn:
        conn.execute(
            "UPDATE birthdays SET last_granted_year = ? WHERE user_id = ?",
            (int(year), str(user_id)),
        )
        conn.commit()


# ---------------- Social notifications persistence ---------------- #
def get_last_youtube_video(channel_id: str) -> Optional[str]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT last_video_id FROM youtube_last WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return row["last_video_id"] if row else None


def set_last_youtube_video(channel_id: str, video_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO youtube_last (channel_id, last_video_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET last_video_id = excluded.last_video_id
            """,
            (channel_id, video_id),
        )
        conn.commit()


def get_last_tiktok_item(feed_key: str) -> Optional[str]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT last_item_id FROM tiktok_last WHERE feed_key = ?", (feed_key,))
        row = cur.fetchone()
        return row["last_item_id"] if row else None


def set_last_tiktok_item(feed_key: str, item_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tiktok_last (feed_key, last_item_id)
            VALUES (?, ?)
            ON CONFLICT(feed_key) DO UPDATE SET last_item_id = excluded.last_item_id
            """,
            (feed_key, item_id),
        )
        conn.commit()


def get_last_youtube_upcoming(channel_id: str) -> Optional[str]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT last_upcoming_id FROM youtube_live_last WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return row["last_upcoming_id"] if row else None


def set_last_youtube_upcoming(channel_id: str, video_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO youtube_live_last (channel_id, last_upcoming_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET last_upcoming_id = excluded.last_upcoming_id
            """,
            (channel_id, video_id),
        )
        conn.commit()


def get_last_youtube_live(channel_id: str) -> Optional[str]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT last_live_id FROM youtube_live_last WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return row["last_live_id"] if row else None


def set_last_youtube_live(channel_id: str, video_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO youtube_live_last (channel_id, last_live_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET last_live_id = excluded.last_live_id
            """,
            (channel_id, video_id),
        )
        conn.commit()


def get_tiktok_live_state(username: str) -> Optional[bool]:
    with _get_connection() as conn:
        cur = conn.execute("SELECT is_live FROM tiktok_live_state WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        return bool(int(row["is_live"]))


def set_tiktok_live_state(username: str, is_live: bool) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tiktok_live_state (username, is_live)
            VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET is_live = excluded.is_live
            """,
            (username, 1 if is_live else 0),
        )
        conn.commit()
