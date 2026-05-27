from __future__ import annotations

from proactive_chat.config import ProactiveChatConfig


def test_config_defaults_are_safe_when_missing():
    config = ProactiveChatConfig.from_mapping({})

    assert config.enabled_groups == ()
    assert config.kill_switch is False
    assert config.proactive_enabled is False
    assert config.background_worker_enabled is False
    assert config.worker_interval_seconds == 5
    assert config.voice_output_enabled is False
    assert config.voice_input_enabled is False
    assert config.cooldown_seconds == 120
    assert config.daily_reply_limit == 24
    assert config.queue_database_path == "data/proactive_chat.sqlite3"
    assert config.can_proactively_speak("10001") is False
    assert config.can_use_voice_output() is False


def test_config_normalizes_group_ids_and_boolean_gates():
    config = ProactiveChatConfig.from_mapping(
        {
            "enabled_groups": [10001, " 10002 ", ""],
            "proactive_enabled": True,
            "ambient_enabled": True,
            "background_worker_enabled": True,
            "worker_interval_seconds": 2,
            "cooldown_seconds": "9",
            "daily_reply_limit": "3",
            "voice_output_enabled": True,
            "voice_input_enabled": True,
            "queue_database_path": "custom/queue.sqlite3",
        }
    )

    assert config.enabled_groups == ("10001", "10002")
    assert config.background_worker_enabled is True
    assert config.worker_interval_seconds == 2
    assert config.cooldown_seconds == 9
    assert config.daily_reply_limit == 3
    assert config.queue_database_path == "custom/queue.sqlite3"
    assert config.can_proactively_speak(10001) is True
    assert config.can_proactively_speak("10003") is False
    assert config.can_observe_ambient_message("10002") is True
    assert config.can_observe_ambient_message("10003") is False
    assert config.can_use_voice_output() is True
    assert config.can_use_voice_input("10001") is True


def test_kill_switch_disables_all_active_surfaces():
    config = ProactiveChatConfig.from_mapping(
        {
            "enabled_groups": ["10001"],
            "proactive_enabled": True,
            "ambient_enabled": True,
            "voice_output_enabled": True,
            "voice_input_enabled": True,
            "kill_switch": True,
        }
    )

    assert config.can_proactively_speak("10001") is False
    assert config.can_observe_ambient_message("10001") is False
    assert config.can_use_voice_output() is False
    assert config.can_use_voice_input("10001") is False
