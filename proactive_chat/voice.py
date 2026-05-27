from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .async_utils import maybe_await


class ProviderUnavailableError(RuntimeError):
    """Raised when AstrBot has no usable STT/TTS provider for the session."""


class VoiceProviderState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass(frozen=True)
class VoiceProviderProbe:
    state: VoiceProviderState
    failure_code: str = ""
    public_detail: str = ""


@dataclass(frozen=True)
class VoiceProviderStatus:
    stt: VoiceProviderProbe
    tts: VoiceProviderProbe


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

    def provider_status(
        self,
        *,
        unified_msg_origin: str,
        voice_input_enabled: bool,
        voice_output_enabled: bool,
    ) -> VoiceProviderStatus:
        return VoiceProviderStatus(
            stt=_probe_provider(
                getattr(self.context, "get_using_stt_provider", None),
                unified_msg_origin,
                enabled=voice_input_enabled,
                missing_code="stt_provider_unavailable",
                failed_code="stt_probe_failed",
            ),
            tts=_probe_provider(
                getattr(self.context, "get_using_tts_provider", None),
                unified_msg_origin,
                enabled=voice_output_enabled,
                missing_code="tts_provider_unavailable",
                failed_code="tts_probe_failed",
            ),
        )


def _get_provider(provider_getter: object, unified_msg_origin: str) -> object | None:
    try:
        return provider_getter()
    except TypeError:
        return provider_getter(umo=unified_msg_origin)


def _probe_provider(
    provider_getter: object,
    unified_msg_origin: str,
    *,
    enabled: bool,
    missing_code: str,
    failed_code: str,
) -> VoiceProviderProbe:
    if not enabled:
        return VoiceProviderProbe(VoiceProviderState.DISABLED)
    if provider_getter is None:
        return VoiceProviderProbe(VoiceProviderState.MISSING, failure_code=missing_code)
    try:
        provider = _get_provider(provider_getter, unified_msg_origin)
    except Exception as exc:
        return VoiceProviderProbe(
            VoiceProviderState.FAILED,
            failure_code=failed_code,
            public_detail=_redact_public_detail(str(exc)),
        )
    if provider is None:
        return VoiceProviderProbe(VoiceProviderState.MISSING, failure_code=missing_code)
    return VoiceProviderProbe(VoiceProviderState.AVAILABLE)


def _redact_public_detail(detail: str) -> str:
    lowered = detail.lower()
    sensitive_markers = (
        "authorization",
        "bearer",
        "cookie",
        "token",
        "secret",
        "password",
        "api key",
        "apikey",
        "base64",
        "http://",
        "https://",
        "/users/",
        "/tmp/",
    )
    if any(marker in lowered for marker in sensitive_markers):
        return "redacted"
    return detail
