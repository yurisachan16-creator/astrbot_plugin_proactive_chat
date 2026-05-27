from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .voice import VoiceProviderProbe, VoiceProviderState, VoiceProviderStatus


@dataclass(frozen=True)
class VoiceProviderSnapshot:
    state: VoiceProviderState
    failure_code: str = ""
    public_detail: str = ""


@dataclass(frozen=True)
class VoiceSnapshot:
    input_enabled: bool = False
    output_enabled: bool = False
    stt: VoiceProviderSnapshot = VoiceProviderSnapshot(VoiceProviderState.DISABLED)
    tts: VoiceProviderSnapshot = VoiceProviderSnapshot(VoiceProviderState.DISABLED)


@dataclass(frozen=True)
class QueueSnapshot:
    queue_available: bool
    worker_available: bool
    background_running: bool
    voice: VoiceSnapshot = VoiceSnapshot()
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    delivery_failed: int = 0


def snapshot_queue(
    queue: object | None,
    *,
    worker_available: bool,
    background_running: bool,
    voice: VoiceSnapshot | None = None,
) -> QueueSnapshot:
    if queue is None:
        return QueueSnapshot(
            queue_available=False,
            worker_available=worker_available,
            background_running=background_running,
            voice=voice or VoiceSnapshot(),
        )

    counts = _queue_counts(queue)
    return QueueSnapshot(
        queue_available=True,
        worker_available=worker_available,
        background_running=background_running,
        voice=voice or VoiceSnapshot(),
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        delivery_failed=counts.get("delivery_failed", 0),
    )


def format_status(snapshot: QueueSnapshot) -> str:
    queue_state = "可用" if snapshot.queue_available else "未启用"
    worker_state = "可用" if snapshot.worker_available else "未启用"
    background_state = "运行中" if snapshot.background_running else "未运行"
    return "\n".join(
        [
        f"队列: {queue_state}\n"
        f"任务: queued={snapshot.queued}, running={snapshot.running}, completed={snapshot.completed}, "
        f"failed={snapshot.failed}, delivery_failed={snapshot.delivery_failed}\n"
        f"worker: {worker_state}\n"
        f"后台 worker: {background_state}",
        *_format_voice_lines(snapshot.voice),
        ]
    )


def _queue_counts(queue: object) -> dict[str, int]:
    if hasattr(queue, "status_counts"):
        return _normalize_counts(queue.status_counts())
    return {}


def _normalize_counts(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): int(value) for key, value in raw.items()}


def voice_snapshot_from_status(
    *,
    input_enabled: bool,
    output_enabled: bool,
    status: VoiceProviderStatus,
) -> VoiceSnapshot:
    return VoiceSnapshot(
        input_enabled=input_enabled,
        output_enabled=output_enabled,
        stt=_voice_provider_snapshot(status.stt),
        tts=_voice_provider_snapshot(status.tts),
    )


def _voice_provider_snapshot(probe: VoiceProviderProbe) -> VoiceProviderSnapshot:
    return VoiceProviderSnapshot(
        state=probe.state,
        failure_code=probe.failure_code,
        public_detail=probe.public_detail,
    )


def _format_voice_lines(snapshot: VoiceSnapshot) -> list[str]:
    return [
        "voice:",
        f"- input: {_enabled(snapshot.input_enabled)}",
        f"- output: {_enabled(snapshot.output_enabled)}",
        f"- stt_provider: {_format_provider(snapshot.stt)}",
        f"- tts_provider: {_format_provider(snapshot.tts)}",
    ]


def _format_provider(snapshot: VoiceProviderSnapshot) -> str:
    parts = [snapshot.state.value]
    if snapshot.failure_code:
        parts.append(snapshot.failure_code)
    detail = _redact_status_detail(snapshot.public_detail)
    if detail:
        parts.append(detail)
    return " ".join(parts)


def _enabled(value: bool) -> str:
    return "enabled" if value else "disabled"


def _redact_status_detail(detail: str) -> str:
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
