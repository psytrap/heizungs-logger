import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
HARDWARE_MODULES = ("serial", "board", "adafruit_character_lcd")


def test_package_import_is_hardware_free():
    code = (
        "import sys, heizungslogger; "
        f"print(sorted(m for m in {HARDWARE_MODULES!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout


def test_public_api_is_exposed():
    import heizungslogger

    assert callable(heizungslogger.parse_frame)
    assert callable(heizungslogger.Runner)
    assert heizungslogger.__version__
