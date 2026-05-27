from __future__ import annotations

import asyncio

from proactive_chat import __version__
from proactive_chat.background import BackgroundWorkerRunner
from proactive_chat.config import ProactiveChatConfig
from proactive_chat.delivery import AstrBotMessenger
from proactive_chat.events import (
    enqueue_ambient_group_message,
    enqueue_voice_group_message,
    extract_group_message,
    extract_voice_group_message,
)
from proactive_chat.llm import AstrBotLLMAdapter
from proactive_chat.management import format_status, snapshot_queue
from proactive_chat.queue_factory import create_default_queue
from proactive_chat.rate_limit import InMemoryRateLimiter
from proactive_chat.voice import AstrBotVoiceAdapter
from proactive_chat.worker import AmbientWorker


try:
    from astrbot.api.star import Context, Star
except ImportError:
    Context = object

    class Star:
        def __init__(self, context: object | None = None) -> None:
            self.context = context

try:
    from astrbot.api.star import register
except ImportError:

    def register(*_args: object, **_kwargs: object) -> object:
        def decorator(cls: object) -> object:
            return cls

        return decorator

try:
    from astrbot.api.event import AstrMessageEvent, filter
except ImportError:
    AstrMessageEvent = object

    class _NoOpEventMessageType:
        GROUP_MESSAGE = "group_message"

    class _NoOpFilter:
        EventMessageType = _NoOpEventMessageType

        @staticmethod
        def event_message_type(_message_type: object) -> object:
            def decorator(func: object) -> object:
                return func

            return decorator

        @staticmethod
        def command(_command_name: str, **_kwargs: object) -> object:
            def decorator(func: object) -> object:
                return func

            return decorator

    filter = _NoOpFilter


def _noop_command(_command_name: str, **_kwargs: object) -> object:
    def decorator(func: object) -> object:
        return func

    return decorator


command = getattr(filter, "command", _noop_command)


@register(
    "astrbot_plugin_proactive_chat",
    "aitwo",
    "AIRI-like proactive group chat plugin for AstrBot.",
    __version__,
)
class ProactiveChatPlugin(Star):
    """Thin AstrBot binding for the v0 community plugin."""

    def __init__(
        self,
        context: Context,
        config: dict | None = None,
        *,
        message_chain_cls: type[object] | None = None,
        queue: object | None = None,
        queue_factory: object | None = None,
        worker: object | None = None,
        background_runner: object | None = None,
        rate_limiter: object | None = None,
    ) -> None:
        super().__init__(context)
        self.context = context
        self.config = ProactiveChatConfig.from_mapping(config)
        self.queue = queue if queue is not None else _create_queue(queue_factory, self.config)
        self.llm = AstrBotLLMAdapter(context)
        self.voice = AstrBotVoiceAdapter(context)
        self.messenger = AstrBotMessenger(context, message_chain_cls=message_chain_cls)
        self.rate_limiter = rate_limiter or InMemoryRateLimiter(
            cooldown_seconds=self.config.cooldown_seconds,
            daily_reply_limit=self.config.daily_reply_limit,
        )
        self.worker = worker or (
            AmbientWorker(
                queue=self.queue,
                llm=self.llm,
                messenger=self.messenger,
                rate_limiter=self.rate_limiter,
                voice=self.voice,
                voice_output_enabled=self.config.can_use_voice_output(),
            )
            if self.queue is not None
            else None
        )
        self.background_runner = background_runner or (
            BackgroundWorkerRunner(
                process_once=self.process_one_job,
                worker_id="proactive-chat-worker",
                interval_seconds=self.config.worker_interval_seconds,
            )
            if self.worker is not None
            else None
        )
        self.background_task: asyncio.Task[object] | None = None

    async def send_proactive_text(
        self,
        unified_msg_origin: str,
        group_id: object,
        text: str,
    ) -> bool:
        if not self.config.can_proactively_speak(group_id):
            return False
        conversation_key = f"group:{str(group_id).strip()}"
        decision = self.rate_limiter.check(conversation_key)
        if not decision.allowed:
            return False
        await self.messenger.send_text(unified_msg_origin, text)
        self.rate_limiter.record(conversation_key)
        return True

    async def handle_group_message(self, event: object) -> bool:
        message = extract_group_message(event)
        if message is not None:
            if self.queue is None or not self.config.can_observe_ambient_message(message.group_id):
                return False
            enqueue_ambient_group_message(self.queue, message)
            return True

        voice_message = extract_voice_group_message(event)
        if voice_message is None:
            return False
        if self.queue is None or not self.config.can_use_voice_input(voice_message.group_id):
            return False
        enqueue_voice_group_message(self.queue, voice_message)
        return True

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent) -> None:
        await self.handle_group_message(event)

    @command("proactive_status", permission=True)
    async def proactive_status(self, event: AstrMessageEvent):
        yield event.plain_result(self.management_status())

    @command("proactive_pause", permission=True)
    async def proactive_pause(self, event: AstrMessageEvent):
        yield event.plain_result(self.pause_background_worker())

    @command("proactive_resume", permission=True)
    async def proactive_resume(self, event: AstrMessageEvent):
        yield event.plain_result(self.resume_background_worker())

    @command("proactive_once", permission=True)
    async def proactive_once(self, event: AstrMessageEvent):
        yield event.plain_result(await self.process_one_job_command())

    async def process_one_job(self, *, worker_id: str = "proactive-chat-worker") -> bool:
        if self.worker is None:
            return False
        return await self.worker.process_once(worker_id=worker_id)

    def start_background_worker(self) -> bool:
        if self.worker is None or self.background_runner is None:
            return False
        if self.background_task is not None and not self.background_task.done():
            return True
        self.background_task = asyncio.create_task(self.background_runner.run())
        return True

    def pause_background_worker(self) -> str:
        if self.background_runner is not None:
            self.background_runner.stop()
        if self.background_task is not None and not self.background_task.done():
            self.background_task.cancel()
        self.background_task = None
        return "后台 worker 已暂停"

    def resume_background_worker(self) -> str:
        return "后台 worker 已启动" if self.start_background_worker() else "后台 worker 无法启动"

    async def process_one_job_command(self) -> str:
        processed = await self.process_one_job(worker_id="manual-admin")
        return "已处理 1 个队列任务" if processed else "没有可处理的队列任务"

    def management_status(self) -> str:
        return format_status(
            snapshot_queue(
                self.queue,
                worker_available=self.worker is not None,
                background_running=(
                    self.background_task is not None and not self.background_task.done()
                ),
            )
        )

    async def initialize(self) -> None:
        if self.config.background_worker_enabled:
            self.start_background_worker()

    async def terminate(self) -> None:
        if self.background_runner is not None:
            self.background_runner.stop()
        if self.background_task is not None and not self.background_task.done():
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass


__all__ = ["ProactiveChatPlugin", "__version__"]


def _create_queue(queue_factory: object | None, config: ProactiveChatConfig) -> object | None:
    if queue_factory is None:
        return create_default_queue(config)
    return queue_factory(config)
