from __future__ import annotations

import asyncio

from proactive_chat.delivery import AstrBotMessenger, SimpleMessageChain


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        self.sent.append((unified_msg_origin, chain))


def test_send_text_uses_astrbot_active_message_contract():
    context = FakeContext()
    messenger = AstrBotMessenger(context, message_chain_cls=SimpleMessageChain)

    asyncio.run(messenger.send_text("aiocqhttp:group:10001", "今天也在。"))

    assert len(context.sent) == 1
    umo, chain = context.sent[0]
    assert umo == "aiocqhttp:group:10001"
    assert isinstance(chain, SimpleMessageChain)
    assert chain.messages == ["今天也在。"]


def test_send_record_uses_astrbot_active_message_contract():
    context = FakeContext()
    messenger = AstrBotMessenger(context, message_chain_cls=SimpleMessageChain)

    asyncio.run(messenger.send_record("aiocqhttp:group:10001", "/tmp/voice.wav"))

    assert len(context.sent) == 1
    umo, chain = context.sent[0]
    assert umo == "aiocqhttp:group:10001"
    assert isinstance(chain, SimpleMessageChain)
    assert chain.messages == [{"record": "/tmp/voice.wav"}]
