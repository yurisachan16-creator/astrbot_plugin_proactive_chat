from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ProactiveChatConfig


def create_default_queue(
    config: ProactiveChatConfig,
    *,
    sqlite_queue_cls: type[Any] | None = None,
) -> object | None:
    queue_cls = sqlite_queue_cls or _load_sqlite_queue_cls()
    if queue_cls is None:
        return None

    return queue_cls(
        str(Path(config.queue_database_path).expanduser()),
        global_concurrency=config.global_worker_concurrency,
        job_type_concurrency={
            "ambient_group_message": config.llm_worker_concurrency,
            "stt": config.stt_worker_concurrency,
            "tts": config.tts_worker_concurrency,
        },
    )


def _load_sqlite_queue_cls() -> type[Any] | None:
    try:
        from astrbot_proactive_core import SQLiteQueue
    except ImportError:
        return None
    return SQLiteQueue
