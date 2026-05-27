from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    failure_code: str = ""


@dataclass
class _ConversationUsage:
    last_reply_at: datetime | None = None
    reply_date: date | None = None
    daily_count: int = 0


class InMemoryRateLimiter:
    def __init__(self, *, cooldown_seconds: int, daily_reply_limit: int) -> None:
        self.cooldown = timedelta(seconds=max(0, cooldown_seconds))
        self.daily_reply_limit = max(0, daily_reply_limit)
        self._usage: dict[str, _ConversationUsage] = {}

    def check(
        self,
        conversation_key: str,
        *,
        now: datetime | None = None,
    ) -> RateLimitDecision:
        timestamp = _coerce_datetime(now)
        usage = self._usage.get(conversation_key)
        if self.daily_reply_limit <= 0:
            return RateLimitDecision(allowed=False, failure_code="daily_reply_limit_reached")
        if usage is None:
            return RateLimitDecision(allowed=True)

        if usage.last_reply_at is not None and timestamp - usage.last_reply_at < self.cooldown:
            return RateLimitDecision(allowed=False, failure_code="cooldown_active")

        current_date = timestamp.date()
        daily_count = usage.daily_count if usage.reply_date == current_date else 0
        if daily_count >= self.daily_reply_limit:
            return RateLimitDecision(allowed=False, failure_code="daily_reply_limit_reached")

        return RateLimitDecision(allowed=True)

    def record(
        self,
        conversation_key: str,
        *,
        now: datetime | None = None,
    ) -> None:
        timestamp = _coerce_datetime(now)
        current_date = timestamp.date()
        usage = self._usage.setdefault(conversation_key, _ConversationUsage())
        if usage.reply_date != current_date:
            usage.reply_date = current_date
            usage.daily_count = 0
        usage.daily_count += 1
        usage.last_reply_at = timestamp


def _coerce_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
