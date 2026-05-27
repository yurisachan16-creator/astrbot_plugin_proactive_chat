from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from proactive_chat.async_utils import maybe_await


@dataclass
class SimpleMessageChain:
    messages: list[str] = field(default_factory=list)

    def message(self, text: str) -> "SimpleMessageChain":
        self.messages.append(text)
        return self

    def record(self, audio_path: str) -> "SimpleMessageChain":
        self.messages.append({"record": audio_path})
        return self


def _load_astrbot_message_chain() -> type[Any]:
    try:
        from astrbot.api.event import MessageChain
    except ImportError:
        return SimpleMessageChain
    return MessageChain


def _load_record_component() -> type[Any] | None:
    try:
        from astrbot.api.message_components import Record
    except ImportError:
        return None
    return Record


class AstrBotMessenger:
    def __init__(self, context: object, message_chain_cls: type[Any] | None = None) -> None:
        self.context = context
        self.message_chain_cls = message_chain_cls or _load_astrbot_message_chain()

    async def send_text(self, unified_msg_origin: str, text: str) -> None:
        chain = self.message_chain_cls().message(text)
        await maybe_await(self.context.send_message(unified_msg_origin, chain))

    async def send_record(self, unified_msg_origin: str, audio_path: str) -> None:
        chain = self.message_chain_cls()
        if hasattr(chain, "record"):
            chain.record(audio_path)
        else:
            record_component = _load_record_component()
            if record_component is None:
                raise RuntimeError("record_component_unavailable")
            chain.chain.append(record_component(file=audio_path, url=audio_path))
        await maybe_await(self.context.send_message(unified_msg_origin, chain))
