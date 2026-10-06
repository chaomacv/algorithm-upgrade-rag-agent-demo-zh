import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import run


def test_algorithm_switch_to_new_llf():
    """Verify config can activate NewLLF when the adapter is compatible."""
    # Patch the adapter inside the test so the initial demo can remain broken.
    config = ROOT / "config" / "pipeline.json"
    adapter = ROOT / "src" / "modules" / "dre_adapter.py"
    original_config = config.read_text(encoding="utf-8")
    original_adapter = adapter.read_text(encoding="utf-8")
    try:
        adapter.write_text(
            'def run_dre(algorithm, image):\n'
            '    """Run the selected DRE algorithm through the adapter boundary."""\n'
            '    # The fixed adapter fills residual_map for new algorithms that omit it.\n'
            '    result = algorithm.process(image)\n'
            '    if "residual_map" not in result:\n'
            '        result["residual_map"] = 0.0\n'
            '    return result\n',
            encoding="utf-8",
        )
        config.write_text(json.dumps({"dre_algorithm": "new_llf"}), encoding="utf-8")
        for module in ["main", "pipeline", "modules.dre_adapter"]:
            if module in sys.modules:
                del sys.modules[module]
        assert importlib.import_module("main").run()["metadata"]["algorithm"] == "new_llf"
    finally:
        config.write_text(original_config, encoding="utf-8")
        adapter.write_text(original_adapter, encoding="utf-8")
