from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


ProcessOnce = Callable[..., Awaitable[bool]]
Sleep = Callable[[float], Awaitable[None]]


class BackgroundWorkerRunner:
    def __init__(
        self,
        *,
        process_once: ProcessOnce,
        worker_id: str,
        interval_seconds: float,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.process_once = process_once
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        self.sleep = sleep
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    async def run(self, *, max_iterations: int | None = None) -> int:
        processed_count = 0
        iterations = 0
        self._stopped = False

        while not self._stopped:
            processed = await self.process_once(worker_id=self.worker_id)
            if processed:
                processed_count += 1
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            await self.sleep(self.interval_seconds)

        return processed_count
