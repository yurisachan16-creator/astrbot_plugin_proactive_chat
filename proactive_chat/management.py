from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueueSnapshot:
    queue_available: bool
    worker_available: bool
    background_running: bool
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    delivery_failed: int = 0


def snapshot_queue(queue: object | None, *, worker_available: bool, background_running: bool) -> QueueSnapshot:
    if queue is None:
        return QueueSnapshot(
            queue_available=False,
            worker_available=worker_available,
            background_running=background_running,
        )

    counts = _queue_counts(queue)
    return QueueSnapshot(
        queue_available=True,
        worker_available=worker_available,
        background_running=background_running,
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        delivery_failed=counts.get("delivery_failed", 0),
    )


def format_status(snapshot: QueueSnapshot) -> str:
    queue_state = "可用" if snapshot.queue_available else "未启用"
    worker_state = "可用" if snapshot.worker_available else "未启用"
    background_state = "运行中" if snapshot.background_running else "未运行"
    return (
        f"队列: {queue_state}\n"
        f"任务: queued={snapshot.queued}, running={snapshot.running}, completed={snapshot.completed}, "
        f"failed={snapshot.failed}, delivery_failed={snapshot.delivery_failed}\n"
        f"worker: {worker_state}\n"
        f"后台 worker: {background_state}"
    )


def _queue_counts(queue: object) -> dict[str, int]:
    if hasattr(queue, "status_counts"):
        return _normalize_counts(queue.status_counts())
    return {}


def _normalize_counts(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): int(value) for key, value in raw.items()}
