from __future__ import annotations

from .async_utils import maybe_await


class ProviderUnavailableError(RuntimeError):
    """Raised when AstrBot has no usable STT/TTS provider for the session."""


class AstrBotVoiceAdapter:
    def __init__(self, context: object) -> None:
        self.context = context

    async def transcribe(self, unified_msg_origin: str, audio_url: str) -> str:
        provider = _get_provider(self.context.get_using_stt_provider, unified_msg_origin)
        if provider is None:
            raise ProviderUnavailableError("stt_provider_unavailable")
        return await maybe_await(provider.get_text(audio_url))

    async def synthesize(self, unified_msg_origin: str, text: str) -> str:
        provider = _get_provider(self.context.get_using_tts_provider, unified_msg_origin)
        if provider is None:
            raise ProviderUnavailableError("tts_provider_unavailable")
        return await maybe_await(provider.get_audio(text))


def _get_provider(provider_getter: object, unified_msg_origin: str) -> object | None:
    try:
        return provider_getter()
    except TypeError:
        return provider_getter(umo=unified_msg_origin)
