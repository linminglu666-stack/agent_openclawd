from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import random


@dataclass(frozen=True)
class FireDecision:
    fire_at: int
    next_fire_at: int
    due: bool


class ScheduleEngine:
    def compute(self, policy: Dict[str, Any], now: int, current_next_fire_at: int) -> FireDecision:
        p = dict(policy or {})
        typ = str(p.get("type", "")).strip()
        if typ == "at":
            at = _parse_time(p.get("at", ""))
            if at is None:
                return FireDecision(fire_at=0, next_fire_at=0, due=False)
            at_ts = int(at.timestamp())
            if current_next_fire_at <= 0:
                current_next_fire_at = at_ts
            due = current_next_fire_at > 0 and current_next_fire_at <= now
            next_fire_at = 0 if due else current_next_fire_at
            return FireDecision(fire_at=current_next_fire_at if due else 0, next_fire_at=next_fire_at, due=due)

        if typ == "interval":
            every = int(p.get("every_sec", 0) or 0)
            jitter = int(p.get("jitter_sec", 0) or 0)
            if every <= 0:
                return FireDecision(fire_at=0, next_fire_at=0, due=False)
            if current_next_fire_at <= 0:
                current_next_fire_at = now + every + _jitter(jitter)
            due = current_next_fire_at <= now
            if not due:
                return FireDecision(fire_at=0, next_fire_at=current_next_fire_at, due=False)
            next_fire_at = now + every + _jitter(jitter)
            return FireDecision(fire_at=current_next_fire_at, next_fire_at=next_fire_at, due=True)

        if typ == "window":
            interval_sec = int(p.get("interval_sec", 0) or 0)
            if interval_sec <= 0:
                return FireDecision(fire_at=0, next_fire_at=0, due=False)
            start = _parse_time_or_hhmm(p.get("start", ""), now)
            end = _parse_time_or_hhmm(p.get("end", ""), now)
            if start is None or end is None:
                return FireDecision(fire_at=0, next_fire_at=0, due=False)
            if end <= start:
                end = start + timedelta(hours=1)
            if current_next_fire_at <= 0:
                current_next_fire_at = max(now, int(start.timestamp()))
            due = current_next_fire_at <= now and now <= int(end.timestamp())
            if not due:
                if now > int(end.timestamp()):
                    next_start = start + timedelta(days=1)
                    return FireDecision(fire_at=0, next_fire_at=int(next_start.timestamp()), due=False)
                return FireDecision(fire_at=0, next_fire_at=current_next_fire_at, due=False)
            next_fire_at = now + interval_sec
            if next_fire_at > int(end.timestamp()):
                next_fire_at = int((start + timedelta(days=1)).timestamp())
            return FireDecision(fire_at=current_next_fire_at, next_fire_at=next_fire_at, due=True)

        return FireDecision(fire_at=0, next_fire_at=0, due=False)


def _parse_time(v: Any) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_time_or_hhmm(v: Any, now_ts: int) -> Optional[datetime]:
    dt = _parse_time(v)
    if dt is not None:
        return dt
    s = str(v or "").strip()
    if not s or ":" not in s:
        return None
    parts = s.split(":")
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return None
    base = datetime.fromtimestamp(int(now_ts), tz=timezone.utc)
    return base.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _jitter(max_jitter: int) -> int:
    if max_jitter <= 0:
        return 0
    return random.randint(0, max_jitter)

