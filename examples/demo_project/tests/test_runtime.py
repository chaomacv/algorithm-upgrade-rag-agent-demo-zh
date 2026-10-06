from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_runtime_completes():
    """Verify the toy pipeline runs without exceptions."""
    # A positive image value is enough for this synthetic runtime check.
    assert run()["image"] > 0
