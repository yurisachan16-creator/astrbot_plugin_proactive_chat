from __future__ import annotations

import json
from pathlib import Path

from main import ProactiveChatPlugin
from proactive_chat.config import ProactiveChatConfig


ROOT = Path(__file__).resolve().parents[1]


class SmokeContext:
    async def send_message(self, unified_msg_origin: str, chain: object) -> None:
        raise AssertionError("smoke check must not send messages")


def main() -> int:
    required_files = [
        "metadata.yaml",
        "_conf_schema.json",
        "requirements.txt",
        "main.py",
    ]
    for relative_path in required_files:
        assert (ROOT / relative_path).is_file(), relative_path

    schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
    assert schema["proactive_enabled"]["default"] is False
    assert schema["ambient_enabled"]["default"] is False
    assert schema["voice_input_enabled"]["default"] is False
    assert schema["voice_output_enabled"]["default"] is False

    config = ProactiveChatConfig.from_mapping({})
    assert config.enabled_groups == ()
    assert config.can_proactively_speak("10001") is False
    assert config.can_observe_ambient_message("10001") is False
    assert config.can_use_voice_input("10001") is False
    assert config.can_use_voice_output() is False

    plugin = ProactiveChatPlugin(SmokeContext(), {}, queue_factory=lambda _config: None)
    assert plugin.queue is None
    assert plugin.worker is None

    print("plugin smoke ok")
    print("safe defaults ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
