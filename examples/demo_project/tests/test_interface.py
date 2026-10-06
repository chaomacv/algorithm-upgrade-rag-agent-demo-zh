from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_interface_contains_required_fields():
    """Verify the pipeline output keeps the required public fields."""
    # Missing residual_map is the expected failure for a direct replacement.
    result = run()
    assert "image" in result
    assert "residual_map" in result
    assert "metadata" in result
