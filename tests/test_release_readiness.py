from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_files_exist():
    assert (ROOT / "LICENSE").is_file()
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "metadata.yaml").is_file()
    assert (ROOT / "_conf_schema.json").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "docs" / "INSTALL_ASTRBOT.md").is_file()
    assert (ROOT / "docs" / "COMMUNITY_LISTING.md").is_file()
    assert (ROOT / "docs" / "MAINTENANCE_0.1.md").is_file()
    assert (ROOT / "docs" / "ROADMAP_0.2.md").is_file()
    assert (ROOT / "docs" / "TASKS.md").is_file()


def test_readme_documents_installation_and_smoke_test_commands():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "安装" in readme
    assert "astrbot-proactive-core>=0.1.0,<0.2.0" in readme
    assert "astrbot-plugin-proactive-chat==0.1.5" in readme
    assert "docs/INSTALL_ASTRBOT.md" in readme
    assert "uv run --extra dev pytest -q" in readme
    assert "/proactive_status" in readme


def test_pyproject_has_publish_metadata():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["authors"][0]["name"] == "aitwo"
    assert "AstrBot" in project["keywords"]
    assert project["urls"]["Repository"].startswith("https://github.com/")


def test_pyproject_publishes_core_runtime_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert "astrbot-proactive-core>=0.1.0,<0.2.0" in dependencies


def test_pyproject_wheel_includes_astrbot_plugin_entry_files():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert force_include["main.py"] == "main.py"
    assert force_include["metadata.yaml"] == "metadata.yaml"
    assert force_include["_conf_schema.json"] == "_conf_schema.json"
    assert force_include["requirements.txt"] == "requirements.txt"
