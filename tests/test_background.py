from __future__ import annotations

import asyncio

from proactive_chat.background import BackgroundWorkerRunner


class FakePlugin:
    def __init__(self, results: list[bool]) -> None:
        self.results = results
        self.worker_ids: list[str] = []

    async def process_one_job(self, *, worker_id: str) -> bool:
        self.worker_ids.append(worker_id)
        return self.results.pop(0) if self.results else False


async def _no_sleep(_seconds: float) -> None:
    return None


async def _cancel_on_sleep(runner: BackgroundWorkerRunner, seconds: float) -> None:
    runner.stop()


def test_background_runner_processes_until_max_iterations():
    plugin = FakePlugin([True, False, True])
    runner = BackgroundWorkerRunner(
        process_once=plugin.process_one_job,
        worker_id="worker-1",
        interval_seconds=0.25,
        sleep=_no_sleep,
    )

    processed = asyncio.run(runner.run(max_iterations=3))

    assert processed == 2
    assert plugin.worker_ids == ["worker-1", "worker-1", "worker-1"]


def test_background_runner_can_be_stopped_between_iterations():
    plugin = FakePlugin([True, True, True])
    runner = BackgroundWorkerRunner(
        process_once=plugin.process_one_job,
        worker_id="worker-1",
        interval_seconds=0.25,
        sleep=lambda seconds: _cancel_on_sleep(runner, seconds),
    )

    processed = asyncio.run(runner.run())

    assert processed == 1
    assert plugin.worker_ids == ["worker-1"]
