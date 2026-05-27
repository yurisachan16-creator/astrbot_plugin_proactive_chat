from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "启用", "是"}
    return bool(value)


def _as_int(value: Any, *, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


def _as_group_ids(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = value

    group_ids: list[str] = []
    for item in raw_items:
        normalized = str(item).strip()
        if normalized:
            group_ids.append(normalized)
    return tuple(group_ids)


@dataclass(frozen=True)
class ProactiveChatConfig:
    enabled_groups: tuple[str, ...] = ()
    proactive_enabled: bool = False
    ambient_enabled: bool = False
    background_worker_enabled: bool = False
    worker_interval_seconds: int = 5
    voice_input_enabled: bool = False
    voice_output_enabled: bool = False
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "23:00"
    quiet_hours_end: str = "08:00"
    cooldown_seconds: int = 120
    daily_reply_limit: int = 24
    global_worker_concurrency: int = 2
    stt_worker_concurrency: int = 1
    llm_worker_concurrency: int = 1
    tts_worker_concurrency: int = 1
    queue_database_path: str = "data/proactive_chat.sqlite3"
    admin_user_ids: tuple[str, ...] = ()
    kill_switch: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "ProactiveChatConfig":
        raw = raw or {}
        return cls(
            enabled_groups=_as_group_ids(raw.get("enabled_groups")),
            proactive_enabled=_as_bool(raw.get("proactive_enabled")),
            ambient_enabled=_as_bool(raw.get("ambient_enabled")),
            background_worker_enabled=_as_bool(raw.get("background_worker_enabled")),
            worker_interval_seconds=_as_int(raw.get("worker_interval_seconds"), default=5, minimum=1),
            voice_input_enabled=_as_bool(raw.get("voice_input_enabled")),
            voice_output_enabled=_as_bool(raw.get("voice_output_enabled")),
            quiet_hours_enabled=_as_bool(raw.get("quiet_hours_enabled"), default=True),
            quiet_hours_start=str(raw.get("quiet_hours_start") or "23:00"),
            quiet_hours_end=str(raw.get("quiet_hours_end") or "08:00"),
            cooldown_seconds=_as_int(raw.get("cooldown_seconds"), default=120),
            daily_reply_limit=_as_int(raw.get("daily_reply_limit"), default=24),
            global_worker_concurrency=_as_int(raw.get("global_worker_concurrency"), default=2, minimum=1),
            stt_worker_concurrency=_as_int(raw.get("stt_worker_concurrency"), default=1, minimum=1),
            llm_worker_concurrency=_as_int(raw.get("llm_worker_concurrency"), default=1, minimum=1),
            tts_worker_concurrency=_as_int(raw.get("tts_worker_concurrency"), default=1, minimum=1),
            queue_database_path=str(
                raw.get("queue_database_path") or "data/proactive_chat.sqlite3"
            ).strip(),
            admin_user_ids=_as_group_ids(raw.get("admin_user_ids")),
            kill_switch=_as_bool(raw.get("kill_switch")),
        )

    def can_proactively_speak(self, group_id: object) -> bool:
        if self.kill_switch or not self.proactive_enabled:
            return False
        return str(group_id).strip() in self.enabled_groups

    def can_observe_ambient_message(self, group_id: object) -> bool:
        if self.kill_switch or not self.ambient_enabled:
            return False
        return str(group_id).strip() in self.enabled_groups

    def can_use_voice_input(self, group_id: object) -> bool:
        if self.kill_switch or not self.voice_input_enabled:
            return False
        return str(group_id).strip() in self.enabled_groups

    def can_use_voice_output(self) -> bool:
        return self.voice_output_enabled and not self.kill_switch
