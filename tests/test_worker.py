from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from proactive_chat.delivery import AstrBotMessenger, SimpleMessageChain
from proactive_chat.llm import AstrBotLLMAdapter, LLMUnavailableError
from proactive_chat.worker import AmbientWorker


@dataclass(frozen=True)
class FakeJob:
    id: int = 1
    conversation_key: str = "group:10001"
    job_type: str = "ambient_group_message"
    payload_ref: str = "astrbot://aiocqhttp:group:10001"
    public_summary: str = "今天聊什么？"


class FakeQueue:
    def __init__(self, job: FakeJob | None = None) -> None:
        self.job = job
        self.claims: list[str] = []
        self.completed: list[int] = []
        self.failed: list[dict[str, object]] = []
        self.delivery: list[dict[str, object]] = []

    def claim_next_job(self, *, worker_id: str) -> FakeJob | None:
        self.claims.append(worker_id)
        job = self.job
        self.job = None
        return job

    def complete_job(self, job_id: int) -> None:
        self.completed.append(job_id)

    def fail_job(self, job_id: int, *, failure_code: str, public_detail: str = "") -> None:
        self.failed.append(
            {
                "job_id": job_id,
                "failure_code": failure_code,
                "public_detail": public_detail,
            }
        )

    def record_delivery(
        self,
        job_id: int,
        delivery_state: object,
        *,
        failure_code: str | None = None,
        public_detail: str = "",
    ) -> None:
        self.delivery.append(
            {
                "job_id": job_id,
                "delivery_state": getattr(delivery_state, "value", delivery_state),
                "failure_code": failure_code,
                "public_detail": public_detail,
            }
        )


class FakeLLM:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    async def generate_ambient_reply(self, *, unified_msg_origin: str, message_text: str) -> str:
        self.calls.append(
            {
                "unified_msg_origin": unified_msg_origin,
                "message_text": message_text,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeVoice:
    def __init__(
        self,
        response: str | Exception = "/tmp/voice.wav",
        *,
        transcription: str | Exception = "语音转写文本",
    ) -> None:
        self.response = response
        self.transcription = transcription
        self.calls: list[dict[str, str]] = []
        self.transcriptions: list[dict[str, str]] = []

    async def transcribe(self, unified_msg_origin: str, audio_url: str) -> str:
        self.transcriptions.append(
            {
                "unified_msg_origin": unified_msg_origin,
                "audio_url": audio_url,
            }
        )
        if isinstance(self.transcription, Exception):
            raise self.transcription
        return self.transcription

    async def synthesize(self, unified_msg_origin: str, text: str) -> str:
        self.calls.append(
            {
                "unified_msg_origin": unified_msg_origin,
                "text": text,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeRateLimiter:
    def __init__(self, *, allowed: bool, failure_code: str = "cooldown_active") -> None:
        self.allowed = allowed
        self.failure_code = failure_code
        self.checked: list[str] = []
        self.recorded: list[str] = []

    def check(self, conversation_key: str) -> object:
        self.checked.append(conversation_key)
        return type(
            "RateLimitDecision",
            (),
            {"allowed": self.allowed, "failure_code": self.failure_code},
        )()

    def record(self, conversation_key: str) -> None:
        self.recorded.append(conversation_key)


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        self.sent.append((unified_msg_origin, chain))


class BrokenContext(FakeContext):
    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        raise RuntimeError("platform down")


def test_worker_claims_ambient_job_generates_reply_sends_and_records_delivery():
    queue = FakeQueue(FakeJob())
    llm = FakeLLM("可以聊点今天的新鲜事。")
    context = FakeContext()
    messenger = AstrBotMessenger(context, message_chain_cls=SimpleMessageChain)
    worker = AmbientWorker(queue=queue, llm=llm, messenger=messenger)

    processed = asyncio.run(worker.process_once(worker_id="worker-1"))

    assert processed is True
    assert queue.claims == ["worker-1"]
    assert llm.calls == [
        {
            "unified_msg_origin": "aiocqhttp:group:10001",
            "message_text": "今天聊什么？",
        }
    ]
    assert queue.completed == [1]
    assert queue.failed == []
    assert queue.delivery[0]["delivery_state"] == "published"
    assert context.sent[0][0] == "aiocqhttp:group:10001"
    assert context.sent[0][1].messages == ["可以聊点今天的新鲜事。"]


def test_worker_transcribes_voice_job_then_generates_reply():
    queue = FakeQueue(
        FakeJob(
            job_type="voice_group_message",
            payload_ref=(
                "astrbot://voice?umo=aiocqhttp%3Agroup%3A10001"
                "&audio_url=http%3A%2F%2Fexample.com%2Fa.wav"
            ),
            public_summary="[语音消息]",
        )
    )
    voice = FakeVoice(transcription="语音里说今天聊什么")
    llm = FakeLLM("可以聊语音输入。")
    context = FakeContext()
    worker = AmbientWorker(
        queue=queue,
        llm=llm,
        messenger=AstrBotMessenger(context, message_chain_cls=SimpleMessageChain),
        voice=voice,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert voice.transcriptions == [
        {
            "unified_msg_origin": "aiocqhttp:group:10001",
            "audio_url": "http://example.com/a.wav",
        }
    ]
    assert llm.calls[0]["message_text"] == "语音里说今天聊什么"
    assert context.sent[0][1].messages == ["可以聊语音输入。"]


def test_worker_fails_voice_job_when_stt_provider_is_unavailable():
    queue = FakeQueue(
        FakeJob(
            job_type="voice_group_message",
            payload_ref=(
                "astrbot://voice?umo=aiocqhttp%3Agroup%3A10001"
                "&audio_url=http%3A%2F%2Fexample.com%2Fa.wav"
            ),
            public_summary="[语音消息]",
        )
    )
    llm = FakeLLM("不应该调用")
    worker = AmbientWorker(
        queue=queue,
        llm=llm,
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        voice=FakeVoice(transcription=RuntimeError("stt_provider_unavailable")),
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert llm.calls == []
    assert queue.failed == [
        {
            "job_id": 1,
            "failure_code": "stt_provider_unavailable",
            "public_detail": "stt_provider_unavailable",
        }
    ]


def test_worker_fails_voice_job_when_stt_returns_empty_text():
    queue = FakeQueue(
        FakeJob(
            job_type="voice_group_message",
            payload_ref=(
                "astrbot://voice?umo=aiocqhttp%3Agroup%3A10001"
                "&audio_url=http%3A%2F%2Fexample.com%2Fa.wav"
            ),
            public_summary="[语音消息]",
        )
    )
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("不应该调用"),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        voice=FakeVoice(transcription="  "),
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert queue.failed == [
        {
            "job_id": 1,
            "failure_code": "empty_stt_response",
            "public_detail": "empty_stt_response",
        }
    ]


def test_worker_fails_voice_job_when_payload_ref_is_invalid():
    queue = FakeQueue(
        FakeJob(
            job_type="voice_group_message",
            payload_ref="astrbot://voice?umo=aiocqhttp%3Agroup%3A10001",
            public_summary="[语音消息]",
        )
    )
    voice = FakeVoice(transcription="不应该调用")
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("不应该调用"),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        voice=voice,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert voice.transcriptions == []
    assert queue.failed == [
        {
            "job_id": 1,
            "failure_code": "invalid_voice_payload",
            "public_detail": "invalid_voice_payload",
        }
    ]


def test_worker_skips_llm_when_rate_limiter_blocks_conversation():
    queue = FakeQueue(FakeJob())
    llm = FakeLLM("不应该调用")
    limiter = FakeRateLimiter(allowed=False, failure_code="cooldown_active")
    worker = AmbientWorker(
        queue=queue,
        llm=llm,
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        rate_limiter=limiter,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert limiter.checked == ["group:10001"]
    assert limiter.recorded == []
    assert llm.calls == []
    assert queue.completed == []
    assert queue.failed == [
        {
            "job_id": 1,
            "failure_code": "cooldown_active",
            "public_detail": "cooldown_active",
        }
    ]


def test_worker_records_rate_limiter_after_successful_delivery():
    queue = FakeQueue(FakeJob())
    limiter = FakeRateLimiter(allowed=True)
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        rate_limiter=limiter,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert limiter.checked == ["group:10001"]
    assert limiter.recorded == ["group:10001"]


def test_worker_sends_voice_when_voice_output_is_enabled():
    queue = FakeQueue(FakeJob())
    voice = FakeVoice("/tmp/voice.wav")
    context = FakeContext()
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(context, message_chain_cls=SimpleMessageChain),
        voice=voice,
        voice_output_enabled=True,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert voice.calls == [
        {
            "unified_msg_origin": "aiocqhttp:group:10001",
            "text": "回复文本",
        }
    ]
    assert context.sent[0][1].messages == [{"record": "/tmp/voice.wav"}]
    assert queue.delivery[0]["delivery_state"] == "published"


def test_worker_falls_back_to_text_when_tts_fails():
    queue = FakeQueue(FakeJob())
    context = FakeContext()
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(context, message_chain_cls=SimpleMessageChain),
        voice=FakeVoice(RuntimeError("tts down")),
        voice_output_enabled=True,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert context.sent[0][1].messages == ["回复文本"]
    assert queue.delivery[0]["delivery_state"] == "fallback_sent"


def test_worker_does_not_synthesize_when_voice_output_is_disabled():
    queue = FakeQueue(FakeJob())
    voice = FakeVoice("/tmp/voice.wav")
    context = FakeContext()
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(context, message_chain_cls=SimpleMessageChain),
        voice=voice,
        voice_output_enabled=False,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert voice.calls == []
    assert context.sent[0][1].messages == ["回复文本"]


def test_worker_returns_false_when_queue_has_no_job():
    queue = FakeQueue(None)
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("不会被调用"),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is False


def test_worker_fails_job_when_llm_provider_is_unavailable():
    queue = FakeQueue(FakeJob())
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM(LLMUnavailableError("llm_provider_unavailable")),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert queue.completed == []
    assert queue.failed == [
        {
            "job_id": 1,
            "failure_code": "llm_provider_unavailable",
            "public_detail": "llm_provider_unavailable",
        }
    ]


def test_worker_records_delivery_failure_without_failing_generation():
    queue = FakeQueue(FakeJob())
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(BrokenContext(), message_chain_cls=SimpleMessageChain),
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert queue.completed == [1]
    assert queue.failed == []
    assert queue.delivery[0]["delivery_state"] == "delivery_failed"
    assert queue.delivery[0]["failure_code"] == "delivery_failed"


def test_worker_does_not_record_rate_limiter_when_llm_fails():
    queue = FakeQueue(FakeJob())
    limiter = FakeRateLimiter(allowed=True)
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM(LLMUnavailableError("llm_provider_unavailable")),
        messenger=AstrBotMessenger(FakeContext(), message_chain_cls=SimpleMessageChain),
        rate_limiter=limiter,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert limiter.checked == ["group:10001"]
    assert limiter.recorded == []


def test_worker_does_not_record_rate_limiter_when_delivery_fails():
    queue = FakeQueue(FakeJob())
    limiter = FakeRateLimiter(allowed=True)
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(BrokenContext(), message_chain_cls=SimpleMessageChain),
        rate_limiter=limiter,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert limiter.checked == ["group:10001"]
    assert limiter.recorded == []


def test_worker_does_not_record_rate_limiter_when_voice_and_text_delivery_fail():
    queue = FakeQueue(FakeJob())
    limiter = FakeRateLimiter(allowed=True)
    worker = AmbientWorker(
        queue=queue,
        llm=FakeLLM("回复文本"),
        messenger=AstrBotMessenger(BrokenContext(), message_chain_cls=SimpleMessageChain),
        voice=FakeVoice(RuntimeError("tts down")),
        voice_output_enabled=True,
        rate_limiter=limiter,
    )

    assert asyncio.run(worker.process_once(worker_id="worker-1")) is True
    assert queue.delivery[0]["delivery_state"] == "delivery_failed"
    assert limiter.recorded == []


class FakeProvider:
    def __init__(self, response: object | None = None) -> None:
        self.response = response or type(
            "LLMResponse",
            (),
            {"role": "assistant", "completion_text": "收到，我看看。"},
        )()
        self.calls: list[dict[str, object]] = []

    async def text_chat(
        self,
        *,
        prompt: str,
        session_id: object,
        contexts: list[object],
        image_urls: list[str],
        system_prompt: str,
    ) -> object:
        self.calls.append(
            {
                "prompt": prompt,
                "session_id": session_id,
                "contexts": contexts,
                "image_urls": image_urls,
                "system_prompt": system_prompt,
            }
        )
        return self.response


class FakeProviderContext:
    def __init__(self, provider: object | None) -> None:
        self.provider = provider

    def get_using_provider(self) -> object | None:
        return self.provider


def test_llm_adapter_uses_current_astrbot_provider_text_chat():
    provider = FakeProvider()
    adapter = AstrBotLLMAdapter(FakeProviderContext(provider))

    reply = asyncio.run(
        adapter.generate_ambient_reply(
            unified_msg_origin="aiocqhttp:group:10001",
            message_text="今天聊什么？",
        )
    )

    assert reply == "收到，我看看。"
    assert "今天聊什么？" in str(provider.calls[0]["prompt"])
    assert provider.calls[0]["session_id"] is None
    assert provider.calls[0]["contexts"] == []
    assert provider.calls[0]["image_urls"] == []


def test_llm_adapter_raises_public_error_when_provider_missing():
    adapter = AstrBotLLMAdapter(FakeProviderContext(None))

    with pytest.raises(LLMUnavailableError, match="llm_provider_unavailable"):
        asyncio.run(
            adapter.generate_ambient_reply(
                unified_msg_origin="aiocqhttp:group:10001",
                message_text="今天聊什么？",
            )
        )
