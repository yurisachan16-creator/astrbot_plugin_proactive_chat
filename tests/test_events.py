from __future__ import annotations

import asyncio
import importlib
import sys
import types

from proactive_chat.events import extract_group_message, extract_voice_group_message


class FakeMessageObject:
    def __init__(
        self,
        group_id: object = "10001",
        sender_id: object = "20001",
        message: list[object] | None = None,
        raw_message: object | None = None,
    ) -> None:
        self.group_id = group_id
        self.sender = type("Sender", (), {"user_id": sender_id})()
        self.message = message or []
        self.raw_message = raw_message


class FakeEvent:
    def __init__(
        self,
        *,
        group_id: object = "10001",
        sender_id: object = "20001",
        message_str: str = "今天聊什么？",
        unified_msg_origin: str = "aiocqhttp:group:10001",
        message: list[object] | None = None,
        raw_message: object | None = None,
    ) -> None:
        self.message_obj = FakeMessageObject(group_id, sender_id, message, raw_message)
        self.message_str = message_str
        self.unified_msg_origin = unified_msg_origin


class FakeRecord:
    def __init__(self, *, url: str = "", file: str = "") -> None:
        self.url = url
        self.file = file


def test_extract_group_message_from_astrbot_event_shape():
    message = extract_group_message(FakeEvent())

    assert message is not None
    assert message.group_id == "10001"
    assert message.sender_id == "20001"
    assert message.text == "今天聊什么？"
    assert message.unified_msg_origin == "aiocqhttp:group:10001"


def test_extract_group_message_ignores_non_group_or_blank_message():
    assert extract_group_message(FakeEvent(group_id=None)) is None
    assert extract_group_message(FakeEvent(message_str="   ")) is None


def test_extract_group_message_ignores_slash_commands():
    assert extract_group_message(FakeEvent(message_str="/proactive_status")) is None
    assert (
        extract_group_message(
            FakeEvent(
                message_str="proactive_status",
                raw_message={"raw_message": "/proactive_status"},
            )
        )
        is None
    )


def test_extract_voice_group_message_from_record_component_url_or_file():
    message = extract_voice_group_message(
        FakeEvent(message_str="", message=[FakeRecord(url="http://example.com/a.wav")])
    )

    assert message is not None
    assert message.group_id == "10001"
    assert message.sender_id == "20001"
    assert message.audio_url == "http://example.com/a.wav"
    assert message.unified_msg_origin == "aiocqhttp:group:10001"

    local_message = extract_voice_group_message(
        FakeEvent(message_str="", message=[FakeRecord(file="/tmp/a.wav")])
    )

    assert local_message is not None
    assert local_message.audio_url == "/tmp/a.wav"


def test_extract_voice_group_message_ignores_non_voice_events():
    assert extract_voice_group_message(FakeEvent(message_str="文字")) is None
    assert extract_voice_group_message(FakeEvent(group_id=None, message=[FakeRecord(url="u")])) is None


class FakeContext:
    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        raise AssertionError("event ingestion must not send directly")


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, str]] = []

    def enqueue_job(
        self,
        *,
        conversation_key: str,
        job_type: str,
        payload_ref: str = "",
        public_summary: str = "",
    ) -> object:
        self.enqueued.append(
            {
                "conversation_key": conversation_key,
                "job_type": job_type,
                "payload_ref": payload_ref,
                "public_summary": public_summary,
            }
        )
        return object()


def test_plugin_queues_enabled_ambient_group_message():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "ambient_enabled": True,
        },
        queue=queue,
    )

    queued = asyncio.run(plugin.handle_group_message(FakeEvent()))

    assert queued is True
    assert queue.enqueued == [
        {
            "conversation_key": "group:10001",
            "job_type": "ambient_group_message",
            "payload_ref": "astrbot://aiocqhttp:group:10001",
            "public_summary": "今天聊什么？",
        }
    ]


def test_plugin_queues_enabled_voice_group_message():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "voice_input_enabled": True,
        },
        queue=queue,
    )

    queued = asyncio.run(
        plugin.handle_group_message(
            FakeEvent(message_str="", message=[FakeRecord(url="http://example.com/a.wav")])
        )
    )

    assert queued is True
    assert queue.enqueued == [
        {
            "conversation_key": "group:10001",
            "job_type": "voice_group_message",
            "payload_ref": (
                "astrbot://voice?umo=aiocqhttp%3Agroup%3A10001"
                "&audio_url=http%3A%2F%2Fexample.com%2Fa.wav"
            ),
            "public_summary": "[语音消息]",
        }
    ]


def test_plugin_ignores_group_message_when_group_or_ambient_disabled():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "ambient_enabled": False,
        },
        queue=queue,
    )

    assert asyncio.run(plugin.handle_group_message(FakeEvent())) is False
    assert asyncio.run(plugin.handle_group_message(FakeEvent(group_id="10002"))) is False
    assert queue.enqueued == []


def test_plugin_ignores_voice_message_when_voice_input_disabled():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "voice_input_enabled": False,
        },
        queue=queue,
    )

    queued = asyncio.run(
        plugin.handle_group_message(
            FakeEvent(message_str="", message=[FakeRecord(url="http://example.com/a.wav")])
        )
    )

    assert queued is False
    assert queue.enqueued == []


def test_plugin_prefers_text_when_event_contains_text_and_voice():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "ambient_enabled": True,
            "voice_input_enabled": True,
        },
        queue=queue,
    )

    queued = asyncio.run(
        plugin.handle_group_message(
            FakeEvent(message_str="文字优先", message=[FakeRecord(url="http://example.com/a.wav")])
        )
    )

    assert queued is True
    assert queue.enqueued[0]["job_type"] == "ambient_group_message"
    assert queue.enqueued[0]["public_summary"] == "文字优先"


def test_plugin_ignores_voice_message_when_kill_switch_is_enabled():
    from main import ProactiveChatPlugin

    queue = FakeQueue()
    plugin = ProactiveChatPlugin(
        FakeContext(),
        {
            "enabled_groups": ["10001"],
            "voice_input_enabled": True,
            "kill_switch": True,
        },
        queue=queue,
    )

    queued = asyncio.run(
        plugin.handle_group_message(
            FakeEvent(message_str="", message=[FakeRecord(url="http://example.com/a.wav")])
        )
    )

    assert queued is False
    assert queue.enqueued == []


def test_plugin_registers_group_message_handler_when_astrbot_filter_exists(monkeypatch):
    class FakeStar:
        def __init__(self, context: object | None = None) -> None:
            self.context = context

    class FakeEventMessageType:
        GROUP_MESSAGE = "group_message"

    class FakeFilter:
        EventMessageType = FakeEventMessageType

        @staticmethod
        def event_message_type(message_type: str) -> object:
            def decorator(func: object) -> object:
                setattr(func, "_astrbot_message_type", message_type)
                return func

            return decorator

    fake_astrbot = types.ModuleType("astrbot")
    fake_api = types.ModuleType("astrbot.api")
    fake_star = types.ModuleType("astrbot.api.star")
    fake_star.Context = object
    fake_star.Star = FakeStar
    fake_event = types.ModuleType("astrbot.api.event")
    fake_event.AstrMessageEvent = object
    fake_event.filter = FakeFilter

    monkeypatch.setitem(sys.modules, "astrbot", fake_astrbot)
    monkeypatch.setitem(sys.modules, "astrbot.api", fake_api)
    monkeypatch.setitem(sys.modules, "astrbot.api.star", fake_star)
    monkeypatch.setitem(sys.modules, "astrbot.api.event", fake_event)

    original_main = sys.modules.pop("main", None)
    try:
        module = importlib.import_module("main")
        assert module.ProactiveChatPlugin.on_group_message._astrbot_message_type == "group_message"
    finally:
        sys.modules.pop("main", None)
        if original_main is not None:
            sys.modules["main"] = original_main


def test_plugin_registers_management_commands_when_astrbot_filter_exists(monkeypatch):
    class FakeStar:
        def __init__(self, context: object | None = None) -> None:
            self.context = context

    class FakeEventMessageType:
        GROUP_MESSAGE = "group_message"

    class FakeFilter:
        EventMessageType = FakeEventMessageType

        @staticmethod
        def event_message_type(message_type: str) -> object:
            def decorator(func: object) -> object:
                setattr(func, "_astrbot_message_type", message_type)
                return func

            return decorator

        @staticmethod
        def command(command_name: str, **kwargs: object) -> object:
            def decorator(func: object) -> object:
                setattr(func, "_astrbot_command", command_name)
                setattr(func, "_astrbot_command_kwargs", kwargs)
                return func

            return decorator

    fake_astrbot = types.ModuleType("astrbot")
    fake_api = types.ModuleType("astrbot.api")
    fake_star = types.ModuleType("astrbot.api.star")
    fake_star.Context = object
    fake_star.Star = FakeStar
    fake_event = types.ModuleType("astrbot.api.event")
    fake_event.AstrMessageEvent = object
    fake_event.filter = FakeFilter

    monkeypatch.setitem(sys.modules, "astrbot", fake_astrbot)
    monkeypatch.setitem(sys.modules, "astrbot.api", fake_api)
    monkeypatch.setitem(sys.modules, "astrbot.api.star", fake_star)
    monkeypatch.setitem(sys.modules, "astrbot.api.event", fake_event)

    original_main = sys.modules.pop("main", None)
    try:
        module = importlib.import_module("main")
        assert module.ProactiveChatPlugin.proactive_status._astrbot_command == "proactive_status"
        assert module.ProactiveChatPlugin.proactive_pause._astrbot_command == "proactive_pause"
        assert module.ProactiveChatPlugin.proactive_resume._astrbot_command == "proactive_resume"
        assert module.ProactiveChatPlugin.proactive_once._astrbot_command == "proactive_once"
        assert module.ProactiveChatPlugin.proactive_status._astrbot_command_kwargs == {
            "permission": True
        }
    finally:
        sys.modules.pop("main", None)
        if original_main is not None:
            sys.modules["main"] = original_main
