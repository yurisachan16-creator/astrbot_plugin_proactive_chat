from __future__ import annotations

import asyncio

import pytest

from proactive_chat.voice import AstrBotVoiceAdapter, ProviderUnavailableError, VoiceProviderState


class FakeSTTProvider:
    def __init__(self) -> None:
        self.audio_urls: list[str] = []

    async def get_text(self, audio_url: str) -> str:
        self.audio_urls.append(audio_url)
        return "你好"


class FakeTTSProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def get_audio(self, text: str) -> str:
        self.texts.append(text)
        return "/tmp/voice.wav"


class FakeContext:
    def __init__(self, stt: object | None = None, tts: object | None = None) -> None:
        self.stt = stt
        self.tts = tts
        self.requested_stt_count = 0
        self.requested_tts_count = 0

    def get_using_stt_provider(self) -> object | None:
        self.requested_stt_count += 1
        return self.stt

    def get_using_tts_provider(self) -> object | None:
        self.requested_tts_count += 1
        return self.tts


def test_transcribe_uses_astrbot_current_stt_provider_for_session():
    stt = FakeSTTProvider()
    context = FakeContext(stt=stt)

    text = asyncio.run(AstrBotVoiceAdapter(context).transcribe("aiocqhttp:group:10001", "http://a/b.wav"))

    assert text == "你好"
    assert context.requested_stt_count == 1
    assert stt.audio_urls == ["http://a/b.wav"]


def test_synthesize_uses_astrbot_current_tts_provider_for_session():
    tts = FakeTTSProvider()
    context = FakeContext(tts=tts)

    audio_path = asyncio.run(AstrBotVoiceAdapter(context).synthesize("aiocqhttp:group:10001", "早上好"))

    assert audio_path == "/tmp/voice.wav"
    assert context.requested_tts_count == 1
    assert tts.texts == ["早上好"]


def test_voice_adapter_raises_public_error_when_provider_missing():
    adapter = AstrBotVoiceAdapter(FakeContext())

    with pytest.raises(ProviderUnavailableError, match="stt_provider_unavailable"):
        asyncio.run(adapter.transcribe("aiocqhttp:group:10001", "http://a/b.wav"))

    with pytest.raises(ProviderUnavailableError, match="tts_provider_unavailable"):
        asyncio.run(adapter.synthesize("aiocqhttp:group:10001", "早上好"))


def test_voice_adapter_reports_available_provider_status_without_calling_provider():
    adapter = AstrBotVoiceAdapter(FakeContext(stt=FakeSTTProvider(), tts=FakeTTSProvider()))

    status = adapter.provider_status(
        unified_msg_origin="aiocqhttp:group:10001",
        voice_input_enabled=True,
        voice_output_enabled=True,
    )

    assert status.stt.state == VoiceProviderState.AVAILABLE
    assert status.stt.failure_code == ""
    assert status.tts.state == VoiceProviderState.AVAILABLE
    assert status.tts.failure_code == ""


def test_voice_adapter_reports_disabled_and_missing_provider_status():
    adapter = AstrBotVoiceAdapter(FakeContext())

    disabled = adapter.provider_status(
        unified_msg_origin="aiocqhttp:group:10001",
        voice_input_enabled=False,
        voice_output_enabled=False,
    )
    missing = adapter.provider_status(
        unified_msg_origin="aiocqhttp:group:10001",
        voice_input_enabled=True,
        voice_output_enabled=True,
    )

    assert disabled.stt.state == VoiceProviderState.DISABLED
    assert disabled.tts.state == VoiceProviderState.DISABLED
    assert missing.stt.state == VoiceProviderState.MISSING
    assert missing.stt.failure_code == "stt_provider_unavailable"
    assert missing.tts.state == VoiceProviderState.MISSING
    assert missing.tts.failure_code == "tts_provider_unavailable"


def test_voice_adapter_reports_failed_provider_status_with_redacted_detail():
    class BrokenContext(FakeContext):
        def get_using_stt_provider(self) -> object | None:
            raise RuntimeError("Authorization: Bearer secret-token http://signed.example/audio.wav")

        def get_using_tts_provider(self) -> object | None:
            raise RuntimeError("cookie=session-secret /Users/aitwo/private.wav")

    status = AstrBotVoiceAdapter(BrokenContext()).provider_status(
        unified_msg_origin="aiocqhttp:group:10001",
        voice_input_enabled=True,
        voice_output_enabled=True,
    )

    assert status.stt.state == VoiceProviderState.FAILED
    assert status.stt.failure_code == "stt_probe_failed"
    assert "secret-token" not in status.stt.public_detail
    assert "signed.example" not in status.stt.public_detail
    assert status.tts.state == VoiceProviderState.FAILED
    assert status.tts.failure_code == "tts_probe_failed"
    assert "session-secret" not in status.tts.public_detail
    assert "/Users/aitwo" not in status.tts.public_detail
