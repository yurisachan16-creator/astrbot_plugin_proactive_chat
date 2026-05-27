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


def test_readme_documents_installation_and_smoke_test_commands():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "安装" in readme
    assert "astrbot_proactive_core" in readme
    assert "uv run --extra dev pytest -q" in readme
    assert "/proactive_status" in readme


def test_pyproject_has_publish_metadata():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["authors"][0]["name"] == "aitwo"
    assert "AstrBot" in project["keywords"]
    assert project["urls"]["Repository"].startswith("https://github.com/")
