from __future__ import annotations

from typing import Any

from .async_utils import maybe_await


class LLMUnavailableError(RuntimeError):
    """Raised when AstrBot has no usable LLM provider for the session."""


class EmptyLLMResponseError(RuntimeError):
    """Raised when the provider returns no sendable text."""


class AstrBotLLMAdapter:
    def __init__(self, context: object) -> None:
        self.context = context

    async def generate_ambient_reply(self, *, unified_msg_origin: str, message_text: str) -> str:
        provider = _get_provider(self.context.get_using_provider, unified_msg_origin)
        if provider is None:
            raise LLMUnavailableError("llm_provider_unavailable")

        response = await maybe_await(
            provider.text_chat(
                prompt=_build_ambient_prompt(message_text),
                session_id=None,
                contexts=[],
                image_urls=[],
                system_prompt="",
            )
        )
        reply = _extract_text(response)
        if not reply:
            raise EmptyLLMResponseError("empty_llm_response")
        return reply


def _get_provider(provider_getter: object, unified_msg_origin: str) -> object | None:
    try:
        return provider_getter()
    except TypeError:
        return provider_getter(umo=unified_msg_origin)


def _build_ambient_prompt(message_text: str) -> str:
    return (
        "你是群聊里的 AI 角色。请根据下面这条群消息，生成一句自然、简短、不过度打扰的回复。\n"
        f"群消息：{message_text}"
    )


def _extract_text(response: Any) -> str:
    for attr in ("completion_text", "text", "content", "result"):
        value = getattr(response, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(response, str):
        return response.strip()
    return ""
