from __future__ import annotations

from datetime import UTC, datetime, timedelta

from proactive_chat.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_first_reply_and_blocks_cooldown():
    now = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)
    limiter = InMemoryRateLimiter(cooldown_seconds=120, daily_reply_limit=24)

    assert limiter.check("group:10001", now=now).allowed is True
    limiter.record("group:10001", now=now)

    blocked = limiter.check("group:10001", now=now + timedelta(seconds=60))

    assert blocked.allowed is False
    assert blocked.failure_code == "cooldown_active"


def test_rate_limiter_resets_cooldown_and_daily_count_by_group():
    now = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)
    limiter = InMemoryRateLimiter(cooldown_seconds=120, daily_reply_limit=1)
    limiter.record("group:10001", now=now)

    same_day = limiter.check("group:10001", now=now + timedelta(minutes=3))
    next_day = limiter.check("group:10001", now=now + timedelta(days=1, minutes=3))
    other_group = limiter.check("group:10002", now=now + timedelta(minutes=3))

    assert same_day.allowed is False
    assert same_day.failure_code == "daily_reply_limit_reached"
    assert next_day.allowed is True
    assert other_group.allowed is True


def test_rate_limiter_allows_exact_cooldown_boundary_and_zero_cooldown():
    now = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)
    limiter = InMemoryRateLimiter(cooldown_seconds=120, daily_reply_limit=24)
    limiter.record("group:10001", now=now)

    assert limiter.check("group:10001", now=now + timedelta(seconds=120)).allowed is True

    no_cooldown = InMemoryRateLimiter(cooldown_seconds=0, daily_reply_limit=24)
    no_cooldown.record("group:10001", now=now)

    assert no_cooldown.check("group:10001", now=now).allowed is True


def test_rate_limiter_zero_daily_limit_blocks_after_no_successful_replies():
    limiter = InMemoryRateLimiter(cooldown_seconds=0, daily_reply_limit=0)

    blocked = limiter.check("group:10001", now=datetime(2026, 5, 27, 8, 0, tzinfo=UTC))

    assert blocked.allowed is False
    assert blocked.failure_code == "daily_reply_limit_reached"
