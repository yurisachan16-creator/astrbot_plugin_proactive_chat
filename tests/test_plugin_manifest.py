from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_metadata_declares_astrbot_plugin_identity():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")

    assert 'name: "astrbot_plugin_proactive_chat"' in metadata
    assert 'version: "v0.1.4"' in metadata
    assert "AstrBot" in metadata
    assert "shared queue" in metadata
    assert "memory" not in metadata
    assert "support_platforms:" in metadata
    assert "aiocqhttp" in metadata


def test_config_schema_defaults_to_safe_inactive_mode():
    schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))

    assert schema["enabled_groups"]["default"] == []
    assert schema["proactive_enabled"]["default"] is False
    assert schema["background_worker_enabled"]["default"] is False
    assert schema["worker_interval_seconds"]["default"] == 5
    assert schema["voice_output_enabled"]["default"] is False
    assert schema["voice_input_enabled"]["default"] is False
    assert schema["quiet_hours_enabled"]["default"] is True
    assert schema["cooldown_seconds"]["default"] == 120
    assert schema["daily_reply_limit"]["default"] == 24
    assert schema["queue_database_path"]["default"] == "data/proactive_chat.sqlite3"
    assert schema["kill_switch"]["default"] is False
    assert schema["stt_provider"]["_special"] == "select_provider_stt"
    assert schema["tts_provider"]["_special"] == "select_provider_tts"


def test_requirements_pin_compatible_core_version():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "astrbot-proactive-core>=0.1.0,<0.2.0" in requirements
