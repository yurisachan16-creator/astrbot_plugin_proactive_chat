from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlsplit

from proactive_chat.llm import EmptyLLMResponseError, LLMUnavailableError


class AmbientWorker:
    def __init__(
        self,
        *,
        queue: object,
        llm: object,
        messenger: object,
        rate_limiter: object | None = None,
        voice: object | None = None,
        voice_output_enabled: bool = False,
    ) -> None:
        self.queue = queue
        self.llm = llm
        self.messenger = messenger
        self.rate_limiter = rate_limiter
        self.voice = voice
        self.voice_output_enabled = voice_output_enabled

    async def process_once(self, *, worker_id: str) -> bool:
        job = self.queue.claim_next_job(worker_id=worker_id)
        if job is None:
            return False
        job_type = getattr(job, "job_type", "")
        if job_type not in {"ambient_group_message", "voice_group_message"}:
            self.queue.fail_job(
                job.id,
                failure_code="unsupported_job_type",
                public_detail=str(job_type),
            )
            return True

        if self.rate_limiter is not None:
            decision = self.rate_limiter.check(job.conversation_key)
            if not decision.allowed:
                self.queue.fail_job(
                    job.id,
                    failure_code=decision.failure_code,
                    public_detail=decision.failure_code,
                )
                return True

        if job_type == "voice_group_message":
            voice_payload = _decode_voice_payload_ref(job.payload_ref)
            if voice_payload is None:
                self.queue.fail_job(
                    job.id,
                    failure_code="invalid_voice_payload",
                    public_detail="invalid_voice_payload",
                )
                return True
            unified_msg_origin, audio_url = voice_payload
            if self.voice is None:
                self.queue.fail_job(
                    job.id,
                    failure_code="stt_provider_unavailable",
                    public_detail="stt_provider_unavailable",
                )
                return True
            try:
                message_text = (await self.voice.transcribe(unified_msg_origin, audio_url)).strip()
            except Exception as exc:
                self.queue.fail_job(job.id, failure_code=str(exc), public_detail=str(exc))
                return True
            if not message_text:
                self.queue.fail_job(
                    job.id,
                    failure_code="empty_stt_response",
                    public_detail="empty_stt_response",
                )
                return True
        else:
            unified_msg_origin = _unified_msg_origin_from_payload_ref(job.payload_ref)
            message_text = job.public_summary

        try:
            reply = await self.llm.generate_ambient_reply(
                unified_msg_origin=unified_msg_origin,
                message_text=message_text,
            )
        except (LLMUnavailableError, EmptyLLMResponseError) as exc:
            self.queue.fail_job(job.id, failure_code=str(exc), public_detail=str(exc))
            return True

        self.queue.complete_job(job.id)
        if self.voice_output_enabled and self.voice is not None:
            try:
                audio_path = await self.voice.synthesize(unified_msg_origin, reply)
                await self.messenger.send_record(unified_msg_origin, audio_path)
            except Exception:
                try:
                    await self.messenger.send_text(unified_msg_origin, reply)
                except Exception as exc:
                    self.queue.record_delivery(
                        job.id,
                        _delivery_state("DELIVERY_FAILED", "delivery_failed"),
                        failure_code="delivery_failed",
                        public_detail=str(exc),
                    )
                    return True
                self.queue.record_delivery(job.id, _delivery_state("FALLBACK_SENT", "fallback_sent"))
                if self.rate_limiter is not None:
                    self.rate_limiter.record(job.conversation_key)
                return True

            self.queue.record_delivery(job.id, _delivery_state("PUBLISHED", "published"))
            if self.rate_limiter is not None:
                self.rate_limiter.record(job.conversation_key)
            return True

        try:
            await self.messenger.send_text(unified_msg_origin, reply)
        except Exception as exc:
            self.queue.record_delivery(
                job.id,
                _delivery_state("DELIVERY_FAILED", "delivery_failed"),
                failure_code="delivery_failed",
                public_detail=str(exc),
            )
            return True

        self.queue.record_delivery(job.id, _delivery_state("PUBLISHED", "published"))
        if self.rate_limiter is not None:
            self.rate_limiter.record(job.conversation_key)
        return True


def _unified_msg_origin_from_payload_ref(payload_ref: str) -> str:
    return payload_ref.removeprefix("astrbot://")


def _decode_voice_payload_ref(payload_ref: str) -> tuple[str, str] | None:
    parsed = urlsplit(payload_ref)
    if parsed.scheme != "astrbot" or parsed.netloc != "voice":
        return None
    query = parse_qs(parsed.query)
    unified_msg_origin = (query.get("umo") or [""])[0].strip()
    audio_url = (query.get("audio_url") or [""])[0].strip()
    if not unified_msg_origin or not audio_url:
        return None
    return unified_msg_origin, audio_url


def _delivery_state(member_name: str, fallback: str) -> Any:
    try:
        from astrbot_proactive_core import DeliveryState
    except ImportError:
        return fallback
    return getattr(DeliveryState, member_name)
