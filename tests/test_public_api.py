from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types


def test_plugin_package_imports():
    import proactive_chat

    assert proactive_chat.__version__ == "0.1.4"


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        self.sent.append((unified_msg_origin, chain))


def test_plugin_normalizes_config_at_entrypoint():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "proactive_enabled": True,
        },
    )

    assert plugin.config.can_proactively_speak("10001") is True
    assert plugin.config.can_proactively_speak("10002") is False


def test_plugin_send_proactive_text_respects_group_gate():
    from main import ProactiveChatPlugin
    from proactive_chat.delivery import SimpleMessageChain

    context = FakeContext()
    plugin = ProactiveChatPlugin(
        context,
        {
            "enabled_groups": ["10001"],
            "proactive_enabled": True,
        },
        message_chain_cls=SimpleMessageChain,
    )

    sent = asyncio.run(plugin.send_proactive_text("aiocqhttp:group:10002", "10002", "不会发送"))
    assert sent is False
    assert context.sent == []

    sent = asyncio.run(plugin.send_proactive_text("aiocqhttp:group:10001", "10001", "今天也在。"))
    assert sent is True
    assert len(context.sent) == 1


def test_plugin_send_proactive_text_respects_rate_limiter():
    from main import ProactiveChatPlugin
    from proactive_chat.delivery import SimpleMessageChain

    context = FakeContext()
    limiter = FakeRateLimiter()
    limiter.allowed = False
    limiter.failure_code = "cooldown_active"
    limiter.checked = []
    limiter.recorded = []

    def check(conversation_key: str) -> object:
        limiter.checked.append(conversation_key)
        return type(
            "RateLimitDecision",
            (),
            {"allowed": limiter.allowed, "failure_code": limiter.failure_code},
        )()

    def record(conversation_key: str) -> None:
        limiter.recorded.append(conversation_key)

    limiter.check = check
    limiter.record = record
    plugin = ProactiveChatPlugin(
        context,
        {
            "enabled_groups": ["10001"],
            "proactive_enabled": True,
        },
        message_chain_cls=SimpleMessageChain,
        rate_limiter=limiter,
    )

    sent = asyncio.run(plugin.send_proactive_text("aiocqhttp:group:10001", "10001", "冷却中"))
    assert sent is False
    assert context.sent == []
    assert limiter.checked == ["group:10001"]
    assert limiter.recorded == []

    limiter.allowed = True
    sent = asyncio.run(plugin.send_proactive_text("aiocqhttp:group:10001", "10001", "可以发送"))

    assert sent is True
    assert len(context.sent) == 1
    assert limiter.recorded == ["group:10001"]


class FakeWorker:
    def __init__(self) -> None:
        self.worker_ids: list[str] = []

    async def process_once(self, *, worker_id: str) -> bool:
        self.worker_ids.append(worker_id)
        return True


class FakeRunner:
    def __init__(self) -> None:
        self.stopped = False
        self.started = False

    async def run(self) -> int:
        self.started = True
        await asyncio.sleep(0)
        return 0

    def stop(self) -> None:
        self.stopped = True


def test_plugin_process_one_job_delegates_to_worker_when_available():
    from main import ProactiveChatPlugin

    worker = FakeWorker()
    plugin = ProactiveChatPlugin(FakeContext(), worker=worker)

    assert asyncio.run(plugin.process_one_job(worker_id="worker-1")) is True
    assert worker.worker_ids == ["worker-1"]


def test_plugin_process_one_job_returns_false_without_worker():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(FakeContext())

    assert asyncio.run(plugin.process_one_job(worker_id="worker-1")) is False


def test_plugin_starts_and_terminates_background_worker():
    from main import ProactiveChatPlugin

    runner = FakeRunner()
    plugin = ProactiveChatPlugin(FakeContext(), worker=FakeWorker(), background_runner=runner)

    async def scenario() -> None:
        started = plugin.start_background_worker()
        assert started is True
        assert plugin.background_task is not None
        await asyncio.sleep(0)
        assert runner.started is True
        await plugin.terminate()

    asyncio.run(scenario())

    assert runner.stopped is True


def test_plugin_does_not_start_background_worker_without_worker():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(
        FakeContext(),
        background_runner=FakeRunner(),
        queue_factory=lambda _config: None,
    )

    assert plugin.start_background_worker() is False
    assert plugin.background_task is None


def test_plugin_does_not_start_background_worker_without_running_loop():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(FakeContext(), worker=FakeWorker(), background_runner=FakeRunner())

    assert plugin.start_background_worker() is False
    assert plugin.background_task is None


def test_plugin_initialize_respects_background_worker_enabled_flag():
    from main import ProactiveChatPlugin

    disabled_runner = FakeRunner()
    disabled = ProactiveChatPlugin(
        FakeContext(),
        {"background_worker_enabled": False},
        worker=FakeWorker(),
        background_runner=disabled_runner,
    )

    enabled_runner = FakeRunner()
    enabled = ProactiveChatPlugin(
        FakeContext(),
        {"background_worker_enabled": True},
        worker=FakeWorker(),
        background_runner=enabled_runner,
    )

    async def scenario() -> None:
        await disabled.initialize()
        assert disabled.background_task is None

        await enabled.initialize()
        assert enabled.background_task is not None
        await asyncio.sleep(0)
        await enabled.terminate()

    asyncio.run(scenario())

    assert disabled_runner.started is False
    assert enabled_runner.started is True


class FakeQueue:
    pass


class FakeRateLimiter:
    pass


def test_plugin_builds_default_queue_when_factory_returns_one():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    seen_config_paths: list[str] = []

    def queue_factory(config: object) -> object:
        seen_config_paths.append(config.queue_database_path)
        return queue

    plugin = ProactiveChatPlugin(
        FakeContext(),
        {"queue_database_path": "custom/queue.sqlite3"},
        queue_factory=queue_factory,
    )

    assert plugin.queue is queue
    assert plugin.worker is not None
    assert seen_config_paths == ["custom/queue.sqlite3"]


def test_plugin_builds_default_rate_limiter_from_config():
    from main import ProactiveChatPlugin
    from proactive_chat.rate_limit import InMemoryRateLimiter

    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "cooldown_seconds": 9,
            "daily_reply_limit": 3,
        },
        queue=FakeQueue(),
    )

    assert isinstance(plugin.rate_limiter, InMemoryRateLimiter)
    assert plugin.rate_limiter.cooldown.total_seconds() == 9
    assert plugin.rate_limiter.daily_reply_limit == 3


def test_plugin_uses_explicit_rate_limiter_when_supplied():
    from main import ProactiveChatPlugin

    limiter = FakeRateLimiter()
    plugin = ProactiveChatPlugin(FakeContext(), queue=FakeQueue(), rate_limiter=limiter)

    assert plugin.rate_limiter is limiter


def test_plugin_injects_voice_adapter_into_default_worker_when_voice_enabled():
    from main import ProactiveChatPlugin
    from proactive_chat.worker import AmbientWorker

    plugin = ProactiveChatPlugin(
        FakeContext(),
        {"voice_output_enabled": True},
        queue=FakeQueue(),
    )

    assert isinstance(plugin.worker, AmbientWorker)
    assert plugin.worker.voice is plugin.voice
    assert plugin.worker.voice_output_enabled is True


def test_plugin_does_not_build_default_queue_when_explicit_queue_is_supplied():
    from main import ProactiveChatPlugin

    queue = FakeQueue()

    def queue_factory(config: object) -> object:
        raise AssertionError("explicit queue should bypass default factory")

    plugin = ProactiveChatPlugin(FakeContext(), queue=queue, queue_factory=queue_factory)

    assert plugin.queue is queue
    assert plugin.worker is not None


def test_plugin_uses_real_astrbot_star_when_register_helper_is_absent(monkeypatch):
    class FakeStar:
        def __init__(self, context: object | None = None) -> None:
            self.context = context

    fake_astrbot = types.ModuleType("astrbot")
    fake_api = types.ModuleType("astrbot.api")
    fake_star = types.ModuleType("astrbot.api.star")
    fake_star.Context = object
    fake_star.Star = FakeStar

    monkeypatch.setitem(sys.modules, "astrbot", fake_astrbot)
    monkeypatch.setitem(sys.modules, "astrbot.api", fake_api)
    monkeypatch.setitem(sys.modules, "astrbot.api.star", fake_star)

    original_main = sys.modules.pop("main", None)
    try:
        module = importlib.import_module("main")
        assert issubclass(module.ProactiveChatPlugin, FakeStar)
    finally:
        sys.modules.pop("main", None)
        if original_main is not None:
            sys.modules["main"] = original_main


def test_plugin_imports_under_astrbot_package_path(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    package_names = [
        "data",
        "data.plugins",
        "data.plugins.astrbot_plugin_proactive_chat",
    ]
    package_paths = [
        str(root.parent),
        str(root.parent),
        str(root),
    ]
    for name, path in zip(package_names, package_paths, strict=True):
        package = types.ModuleType(name)
        package.__path__ = [path]
        monkeypatch.setitem(sys.modules, name, package)

    module_name = "data.plugins.astrbot_plugin_proactive_chat.main"
    spec = importlib.util.spec_from_file_location(module_name, root / "main.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)

    spec.loader.exec_module(module)

    assert module.ProactiveChatPlugin.__name__ == "ProactiveChatPlugin"
