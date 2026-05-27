from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_smoke_script_passes_without_astrbot_runtime():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "smoke_check.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "plugin smoke ok" in result.stdout
    assert "safe defaults ok" in result.stdout


def test_readme_mentions_smoke_script():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "scripts/smoke_check.py" in readme
