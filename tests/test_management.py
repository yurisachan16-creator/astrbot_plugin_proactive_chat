from __future__ import annotations

import asyncio

from proactive_chat.management import QueueSnapshot, VoiceProviderSnapshot, VoiceSnapshot, format_status
from proactive_chat.voice import VoiceProviderState


def test_format_status_handles_missing_queue_and_worker():
    status = format_status(
        QueueSnapshot(queue_available=False, worker_available=False, background_running=False)
    )

    assert "队列: 未启用" in status
    assert "后台 worker: 未运行" in status


def test_format_status_includes_queue_counts_when_available():
    status = format_status(
        QueueSnapshot(
            queue_available=True,
            worker_available=True,
            background_running=True,
            queued=2,
            running=1,
            completed=5,
            failed=1,
            delivery_failed=1,
        )
    )

    assert "队列: 可用" in status
    assert "queued=2" in status
    assert "running=1" in status
    assert "completed=5" in status
    assert "failed=1" in status
    assert "delivery_failed=1" in status
    assert "后台 worker: 运行中" in status


def test_format_status_includes_voice_provider_status_and_redacts_details():
    status = format_status(
        QueueSnapshot(
            queue_available=True,
            worker_available=True,
            background_running=False,
            voice=VoiceSnapshot(
                input_enabled=True,
                output_enabled=True,
                stt=VoiceProviderSnapshot(
                    state=VoiceProviderState.FAILED,
                    failure_code="stt_probe_failed",
                    public_detail="Authorization: Bearer secret-token http://signed.example/audio.wav",
                ),
                tts=VoiceProviderSnapshot(
                    state=VoiceProviderState.MISSING,
                    failure_code="tts_provider_unavailable",
                    public_detail="cookie=session-secret /Users/aitwo/private.wav data:audio/wav;base64,abc",
                ),
            ),
        )
    )

    assert "voice:" in status
    assert "- input: enabled" in status
    assert "- output: enabled" in status
    assert "- stt_provider: failed stt_probe_failed" in status
    assert "- tts_provider: missing tts_provider_unavailable" in status
    assert "secret-token" not in status
    assert "session-secret" not in status
    assert "signed.example" not in status
    assert "/Users/aitwo" not in status
    assert "base64" not in status


class FakeContext:
    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        raise AssertionError("management tests should not send active messages")


class FakeQueue:
    def status_counts(self) -> dict[str, int]:
        return {
            "queued": 3,
            "running": 1,
            "completed": 8,
            "failed": 2,
            "delivery_failed": 1,
        }


class FakeWorker:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.worker_ids: list[str] = []

    async def process_once(self, *, worker_id: str) -> bool:
        self.worker_ids.append(worker_id)
        return self.result


def test_plugin_management_status_uses_queue_counts():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(FakeContext(), queue=FakeQueue(), worker=FakeWorker())

    status = plugin.management_status()

    assert "queued=3" in status
    assert "delivery_failed=1" in status


class FakeSTTProvider:
    pass


class FakeTTSProvider:
    pass


class FakeVoiceContext(FakeContext):
    def __init__(self, *, stt: object | None = None, tts: object | None = None) -> None:
        self.stt = stt
        self.tts = tts

    def get_using_stt_provider(self) -> object | None:
        return self.stt

    def get_using_tts_provider(self) -> object | None:
        return self.tts


def test_plugin_management_status_includes_voice_provider_status_from_config():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(
        FakeVoiceContext(stt=FakeSTTProvider(), tts=None),
        {
            "enabled_groups": ["10001"],
            "voice_input_enabled": True,
            "voice_output_enabled": True,
        },
        queue=FakeQueue(),
        worker=FakeWorker(),
    )

    status = plugin.management_status()

    assert "- input: enabled" in status
    assert "- output: enabled" in status
    assert "- stt_provider: available" in status
    assert "- tts_provider: missing tts_provider_unavailable" in status


def test_plugin_pause_resume_and_manual_process():
    from main import ProactiveChatPlugin

    worker = FakeWorker(result=True)
    plugin = ProactiveChatPlugin(FakeContext(), queue=FakeQueue(), worker=worker)

    async def scenario() -> str:
        assert plugin.pause_background_worker() == "后台 worker 已暂停"
        assert plugin.resume_background_worker() == "后台 worker 已启动"
        plugin.pause_background_worker()
        return await plugin.process_one_job_command()

    result = asyncio.run(scenario())

    assert result == "已处理 1 个队列任务"
    assert worker.worker_ids == ["manual-admin"]


class FakeCommandEvent:
    def plain_result(self, text: str) -> str:
        return text


async def _collect_async_generator(generator: object) -> list[object]:
    return [item async for item in generator]


def test_plugin_management_command_methods_yield_plain_results():
    from main import ProactiveChatPlugin

    plugin = ProactiveChatPlugin(FakeContext(), queue=FakeQueue(), worker=FakeWorker(result=False))

    async def scenario() -> tuple[list[object], list[object], list[object]]:
        status = await _collect_async_generator(plugin.proactive_status(FakeCommandEvent()))
        pause = await _collect_async_generator(plugin.proactive_pause(FakeCommandEvent()))
        once = await _collect_async_generator(plugin.proactive_once(FakeCommandEvent()))
        return status, pause, once

    status, pause, once = asyncio.run(scenario())

    assert "队列: 可用" in status[0]
    assert pause == ["后台 worker 已暂停"]
    assert once == ["没有可处理的队列任务"]
