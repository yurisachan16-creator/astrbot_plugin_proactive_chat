from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode


@dataclass(frozen=True)
class IncomingGroupMessage:
    group_id: str
    sender_id: str
    text: str
    unified_msg_origin: str


@dataclass(frozen=True)
class IncomingVoiceGroupMessage:
    group_id: str
    sender_id: str
    audio_url: str
    unified_msg_origin: str


def extract_group_message(event: object) -> IncomingGroupMessage | None:
    message_obj = getattr(event, "message_obj", None)
    group_id = getattr(message_obj, "group_id", None)
    text = str(getattr(event, "message_str", "") or "").strip()
    if group_id is None or not text:
        return None
    if text.startswith("/"):
        return None

    sender = getattr(message_obj, "sender", None)
    sender_id = getattr(sender, "user_id", "")
    unified_msg_origin = str(getattr(event, "unified_msg_origin", "") or "")

    return IncomingGroupMessage(
        group_id=str(group_id).strip(),
        sender_id=str(sender_id).strip(),
        text=text,
        unified_msg_origin=unified_msg_origin,
    )


def extract_voice_group_message(event: object) -> IncomingVoiceGroupMessage | None:
    message_obj = getattr(event, "message_obj", None)
    group_id = getattr(message_obj, "group_id", None)
    if group_id is None:
        return None

    audio_url = _first_record_url(getattr(message_obj, "message", []) or [])
    if not audio_url:
        return None

    sender = getattr(message_obj, "sender", None)
    sender_id = getattr(sender, "user_id", "")
    unified_msg_origin = str(getattr(event, "unified_msg_origin", "") or "")

    return IncomingVoiceGroupMessage(
        group_id=str(group_id).strip(),
        sender_id=str(sender_id).strip(),
        audio_url=audio_url,
        unified_msg_origin=unified_msg_origin,
    )


def enqueue_ambient_group_message(queue: Any, message: IncomingGroupMessage) -> object:
    return queue.enqueue_job(
        conversation_key=f"group:{message.group_id}",
        job_type="ambient_group_message",
        payload_ref=f"astrbot://{message.unified_msg_origin}",
        public_summary=message.text,
    )


def enqueue_voice_group_message(queue: Any, message: IncomingVoiceGroupMessage) -> object:
    return queue.enqueue_job(
        conversation_key=f"group:{message.group_id}",
        job_type="voice_group_message",
        payload_ref=_encode_voice_payload_ref(message.unified_msg_origin, message.audio_url),
        public_summary="[语音消息]",
    )


def _first_record_url(components: list[object]) -> str:
    for component in components:
        name = type(component).__name__.lower()
        if "record" not in name and str(getattr(component, "type", "")).lower() != "record":
            continue
        for attr in ("url", "file", "path"):
            value = str(getattr(component, attr, "") or "").strip()
            if value:
                return value
    return ""


def _encode_voice_payload_ref(unified_msg_origin: str, audio_url: str) -> str:
    return "astrbot://voice?" + urlencode(
        {
            "umo": unified_msg_origin,
            "audio_url": audio_url,
        }
    )
