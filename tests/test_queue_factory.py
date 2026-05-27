from __future__ import annotations

from proactive_chat.config import ProactiveChatConfig
from proactive_chat.queue_factory import create_default_queue


class FakeSQLiteQueue:
    created: list[dict[str, object]] = []

    def __init__(
        self,
        path: str,
        *,
        global_concurrency: int | None = None,
        job_type_concurrency: dict[str, int] | None = None,
    ) -> None:
        self.path = path
        self.global_concurrency = global_concurrency
        self.job_type_concurrency = job_type_concurrency or {}
        self.created.append(
            {
                "path": path,
                "global_concurrency": global_concurrency,
                "job_type_concurrency": self.job_type_concurrency,
            }
        )


def test_create_default_queue_uses_configured_sqlite_path_and_concurrency(tmp_path):
    FakeSQLiteQueue.created = []
    db_path = tmp_path / "proactive.sqlite3"
    config = ProactiveChatConfig.from_mapping(
        {
            "queue_database_path": str(db_path),
            "global_worker_concurrency": 3,
            "llm_worker_concurrency": 2,
            "stt_worker_concurrency": 1,
            "tts_worker_concurrency": 1,
        }
    )

    queue = create_default_queue(config, sqlite_queue_cls=FakeSQLiteQueue)

    assert isinstance(queue, FakeSQLiteQueue)
    assert FakeSQLiteQueue.created == [
        {
            "path": str(db_path),
            "global_concurrency": 3,
            "job_type_concurrency": {
                "ambient_group_message": 2,
                "stt": 1,
                "tts": 1,
            },
        }
    ]


def test_create_default_queue_returns_none_when_core_package_is_missing(monkeypatch):
    import proactive_chat.queue_factory as queue_factory

    config = ProactiveChatConfig.from_mapping({})
    monkeypatch.setattr(queue_factory, "_load_sqlite_queue_cls", lambda: None)

    assert create_default_queue(config) is None
